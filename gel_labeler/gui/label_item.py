from PyQt6.QtWidgets import QGraphicsTextItem, QGraphicsDropShadowEffect, QMenu
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QFont, QCursor
from gel_labeler.core.label import GelLabel
from gel_labeler.gui.settings_dialog import SettingsDialog

class LabelItem(QGraphicsTextItem):
    """Custom interactive text item representing a label on the QGraphicsScene.
    
    Manages selection, drag-and-drop boundary constraints, text styling, and syncing 
    positional updates back to the core data model.
    """
    
    def __init__(self, label_data: GelLabel, position_changed_callback=None, 
                 delete_callback=None, update_callback=None):
        super().__init__()
        self.label_data = label_data
        self.position_changed_callback = position_changed_callback
        self.delete_callback = delete_callback
        self.update_callback = update_callback
        
        # Enable item flags for selection and dragging
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        # Visual cues on hover
        self.setAcceptHoverEvents(True)
        
        # Apply shadow effect for readability on high-contrast/fluorescent gel bands
        self.apply_premium_shadow()
        
        # Refresh visual representation
        self.refresh()

    def apply_premium_shadow(self):
        """Applies a strong dark drop shadow/glow behind the text to ensure legibility."""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(5)
        shadow.setColor(QColor(0, 0, 0, 240))  # Solid dark shadow
        shadow.setOffset(1.5, 1.5)
        self.setGraphicsEffect(shadow)

    def refresh(self):
        """Updates text and styles from the underlying label data model."""
        self.setPlainText(self.label_data.text)
        
        font = QFont(self.label_data.font_family, self.label_data.font_size)
        font.setBold(True)
        self.setFont(font)
        
        self.setDefaultTextColor(QColor(self.label_data.color))
        self.setPos(self.label_data.x, self.label_data.y)
        
        # Center-origin rotation transform to rotate text in place
        self.setTransformOriginPoint(self.boundingRect().width() / 2, self.boundingRect().height() / 2)
        self.setRotation(self.label_data.rotation)

    def hoverEnterEvent(self, event):
        """Changes cursor to indicate drag capability on hover."""
        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Restores default cursor on leave."""
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        """Restricts drag motion so label stays within the scene boundaries."""
        if change == self.GraphicsItemChange.ItemPositionChange and self.scene():
            new_pos = value
            scene_rect = self.scene().sceneRect()
            item_rect = self.boundingRect()
            
            # Clamp X to scene bounds
            x = max(scene_rect.left(), min(new_pos.x(), scene_rect.right() - item_rect.width()))
            # Clamp Y to scene bounds
            y = max(scene_rect.top(), min(new_pos.y(), scene_rect.bottom() - item_rect.height()))
            
            clamped = QPointF(x, y)
            
            # Trigger real-time callback if item is dragged
            if hasattr(self, '_drag_start_pos') and self.scene().views():
                view = self.scene().views()[0]
                if hasattr(view.window(), 'on_selected_label_dragged'):
                    view.window().on_selected_label_dragged(self.label_data.id, x, y)
                    
            return clamped
            
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        """Records the starting position before drag starts."""
        self._drag_start_pos = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Syncs the final dragged position back to the core data model."""
        super().mouseReleaseEvent(event)
        new_pos = self.pos()
        
        # Save undo state only if position changed
        if hasattr(self, '_drag_start_pos') and self._drag_start_pos != new_pos:
            self.setPos(self._drag_start_pos)
            self.label_data.update_position(self._drag_start_pos.x(), self._drag_start_pos.y())
            
            if self.scene() and self.scene().views():
                view = self.scene().views()[0]
                view.project.save_undo_state()
                view.project.is_dirty = True
                if hasattr(view.window(), 'update_window_title'):
                    view.window().update_window_title()
                
            self.setPos(new_pos)
            self.label_data.update_position(new_pos.x(), new_pos.y())
            
        if self.position_changed_callback:
            self.position_changed_callback(self.label_data.id, new_pos.x(), new_pos.y())

    def contextMenuEvent(self, event):
        """Displays right-click context menu for editing styles or deleting."""
        menu = QMenu()
        edit_action = menu.addAction("Edit Label...")
        delete_action = menu.addAction("Delete")
        
        # Exec menu at the cursor's screen position
        action = menu.exec(event.screenPos())
        
        if action == edit_action:
            self.open_edit_dialog()
        elif action == delete_action:
            if self.delete_callback:
                self.delete_callback(self.label_data.id)

    def open_edit_dialog(self):
        """Opens the SettingsDialog to edit label text, color, size, and rotation."""
        parent_widget = None
        if self.scene() and self.scene().views():
            parent_widget = self.scene().views()[0]
            
        dialog = SettingsDialog(
            parent=parent_widget,
            initial_text=self.label_data.text,
            initial_color=self.label_data.color,
            initial_font_size=self.label_data.font_size,
            initial_rotation=self.label_data.rotation
        )
        
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            text, color, size, rotation = dialog.get_values()
            if text:
                if self.scene() and self.scene().views():
                    view = self.scene().views()[0]
                    view.project.save_undo_state()
                    view.project.is_dirty = True
                    if hasattr(view.window(), 'update_window_title'):
                        view.window().update_window_title()
                self.label_data.update_style(text=text, color=color, font_size=size, rotation=rotation)
                self.refresh()
                if self.update_callback:
                    self.update_callback(self.label_data.id)
            else:
                # If text was cleared, delete the label
                if self.delete_callback:
                    self.delete_callback(self.label_data.id)


    def mouseDoubleClickEvent(self, event):
        """Opens the SettingsDialog when double-clicked."""
        self.open_edit_dialog()
        event.accept()
