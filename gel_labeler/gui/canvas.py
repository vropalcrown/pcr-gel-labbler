from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QBrush

from gel_labeler.core.project import GelProject
from gel_labeler.gui.label_item import LabelItem
from gel_labeler.config import DEFAULT_COLOR, DEFAULT_FONT_SIZE


class GelCanvas(QGraphicsView):
    """Custom interactive viewport for viewing gel images and placing labels."""
    
    def __init__(self, project: GelProject, parent=None):
        super().__init__(parent)
        self.project = project
        
        # Configure Graphics Scene
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # UI state variables
        self.bg_pixmap_item = None
        self.label_items = {}  # Map label_id -> LabelItem
        
        # Configure View performance & behaviors
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Signals/Callbacks to notify MainWindow
        self.on_project_modified = None
        self.on_status_message = None
        
        # Span placement state variables
        self.span_mode = False
        self.span_config = {}
        self.span_first_point = None
        self.temp_marker = None
        
        # 2-click alignment state variables
        self.align_mode = False
        self.align_first_point = None


    def load_project_image(self) -> bool:
        """Loads the image from the project into the canvas and sets boundaries."""
        if not self.project.image_path:
            return False
            
        self.clear_canvas()
        
        # Load image via QPixmap
        pixmap = QPixmap(self.project.image_path)
        if pixmap.isNull():
            if self.on_status_message:
                self.on_status_message("Error: Failed to load image file.")
            return False
            
        # Set scene size to match original image dimensions
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        
        # Add background image
        self.bg_pixmap_item = QGraphicsPixmapItem(pixmap)
        self.bg_pixmap_item.setZValue(-10)  # Make sure it stays in the background
        self.scene.addItem(self.bg_pixmap_item)
        
        # Populate any existing labels (e.g. if project loaded from JSON)
        self.populate_labels()
        
        # Fit image to view
        self.fit_image_in_view()
        return True

    def reload_labels(self):
        """Reloads only the label items without clearing the pixmap or resetting view zoom/pan."""
        for item in list(self.label_items.values()):
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self.label_items.clear()
        self.populate_labels()
        if self.on_project_modified:
            self.on_project_modified()

    def deferred_reload(self):
        """Reloads labels without resetting view zoom/pan if the image is already loaded."""
        if self.bg_pixmap_item is not None and not self.bg_pixmap_item.pixmap().isNull():
            self.reload_labels()
        else:
            self.load_project_image()
            if self.on_project_modified:
                self.on_project_modified()


    def populate_labels(self):
        """Builds LabelItems for all labels currently in the project."""
        for label in self.project.get_labels_list():
            self.create_label_item(label)

    def clear_canvas(self):
        """Clears all graphical items from the scene safely."""
        self.scene.clearSelection()
        if self.scene.focusItem():
            self.scene.focusItem().clearFocus()
        if self.temp_marker:
            try:
                self.scene.removeItem(self.temp_marker)
            except Exception:
                pass
            self.temp_marker = None
        self.span_mode = False
        self.align_mode = False
        self.align_first_point = None
        self.span_first_point = None
        self.scene.clear()
        self.bg_pixmap_item = None
        self.label_items.clear()


    def fit_image_in_view(self):
        """Scales the view to fit the loaded gel image while keeping aspect ratio."""
        if self.bg_pixmap_item:
            self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        """Keeps image centered/scaled on window resize if not zoomed in."""
        super().resizeEvent(event)
        # We only auto-fit if the scrollbars aren't active (meaning user hasn't zoomed in)
        if (self.horizontalScrollBar().maximum() == 0 and 
                self.verticalScrollBar().maximum() == 0):
            self.fit_image_in_view()

    # --- Mouse Interactions for Zoom and Pan ---
    
    def wheelEvent(self, event):
        """Handles zooming with Ctrl + Mouse Wheel."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            zoom_in_factor = 1.25
            zoom_out_factor = 0.8
            
            # Save the scene position of the mouse cursor
            old_pos = self.mapToScene(event.position().toPoint())
            
            # Perform zoom
            if event.angleDelta().y() > 0:
                self.scale(zoom_in_factor, zoom_in_factor)
            else:
                self.scale(zoom_out_factor, zoom_out_factor)
                
            # Pan the view to keep mouse cursor in the same relative position
            new_pos = self.mapToScene(event.position().toPoint())
            delta = new_pos - old_pos
            self.translate(delta.x(), delta.y())
            
            if self.on_status_message:
                scale_x = self.transform().m11()
                self.on_status_message(f"Zoom Level: {scale_x:.0%}")
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        """Initiates label placement, panning, cropping, or aligning based on active modes."""

        # Handle 2-Click Alignment Mode first
        if self.align_mode:
            if event.button() == Qt.MouseButton.LeftButton:
                pos = event.position().toPoint()
                scene_pos = self.mapToScene(pos)
                
                if self.align_first_point is None:
                    self.align_first_point = scene_pos
                    pen = QPen(QColor("#00FFCC"), 2)
                    brush = QBrush(QColor(0, 255, 204, 120))
                    self.temp_marker = self.scene.addEllipse(
                        scene_pos.x() - 6, scene_pos.y() - 6, 12, 12, pen, brush
                    )
                    if self.on_status_message:
                        self.on_status_message("Align Mode: Click the second point along the reference line (e.g. rightmost well).")
                else:
                    pt1 = self.align_first_point
                    pt2 = scene_pos
                    
                    if self.temp_marker:
                        self.scene.removeItem(self.temp_marker)
                        self.temp_marker = None
                        
                    dx = pt2.x() - pt1.x()
                    dy = pt2.y() - pt1.y()
                    
                    # Calculate angle
                    import math
                    angle_rad = math.atan2(dy, dx)
                    angle_deg = math.degrees(angle_rad)
                    
                    # Rotate image by -angle_deg to deskew/align
                    self.project.rotate_image(-angle_deg)
                    
                    self.align_mode = False
                    self.align_first_point = None
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                    QTimer.singleShot(0, self.deferred_reload)
                    
                    if self.on_status_message:
                        self.on_status_message(f"Successfully aligned image (rotated by {-angle_deg:.2f}°)")
            elif event.button() == Qt.MouseButton.RightButton:
                self.cancel_align_mode()
            return

        # Handle Span Placement Mode first
        if self.span_mode:
            if event.button() == Qt.MouseButton.LeftButton:
                pos = event.position().toPoint()
                scene_pos = self.mapToScene(pos)
                
                if self.span_first_point is None:
                    # Capture First Point
                    self.span_first_point = scene_pos
                    from PyQt6.QtGui import QPen, QBrush, QColor
                    pen = QPen(QColor("#FF0055"), 2)
                    brush = QBrush(QColor(255, 0, 85, 120))
                    self.temp_marker = self.scene.addEllipse(
                        scene_pos.x() - 6, scene_pos.y() - 6, 12, 12, pen, brush
                    )
                    
                    if self.on_status_message:
                        self.on_status_message(
                            f"Span Mode: Click the rightmost well for {self.span_config.get('name')}"
                        )
                else:
                    # Capture Second Point and Generate
                    pt1 = self.span_first_point
                    pt2 = scene_pos
                    
                    # Remove temp marker
                    if self.temp_marker:
                        self.scene.removeItem(self.temp_marker)
                        self.temp_marker = None
                        
                    # Generate labels in project model
                    self.project.generate_span_labels(
                        labels=self.span_config.get("labels", []),
                        x1=pt1.x(), y1=pt1.y(),
                        x2=pt2.x(), y2=pt2.y(),
                        color=self.span_config.get("color", DEFAULT_COLOR),
                        font_size=self.span_config.get("font_size", DEFAULT_FONT_SIZE),
                        rotation=self.span_config.get("rotation", 0.0),
                        font_family=self.span_config.get("font_family", "Arial")
                    )
                    
                    self.span_mode = False
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                    QTimer.singleShot(0, self.deferred_reload)
                    
                    if self.on_status_message:
                        self.on_status_message("Successfully generated span-based lane labels!")
            elif event.button() == Qt.MouseButton.RightButton:
                self.cancel_span_mode()
            return


        if event.button() == Qt.MouseButton.MiddleButton:
            # Middle button click = Hand panning
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            # Create a fake left click event for scroll hand drag to start immediately
            fake_event = event
            super().mousePressEvent(fake_event)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Restores default modes when mouse button is released."""
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

    def mouseDoubleClickEvent(self, event):
        """Double clicking on an empty area of the canvas prompts to create a new label at that position."""
        if event.button() == Qt.MouseButton.LeftButton and self.bg_pixmap_item:
            item_under_cursor = self.itemAt(event.position().toPoint())
            # If the click was not on an existing label (it was on the background or empty scene)
            if item_under_cursor is None or item_under_cursor == self.bg_pixmap_item:
                scene_pos = self.mapToScene(event.position().toPoint())
                self.prompt_add_label_at(scene_pos.x(), scene_pos.y())
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        """Shows canvas context menu when right-clicking on empty background."""
        item_under_cursor = self.itemAt(event.pos())
        if item_under_cursor is None or item_under_cursor == self.bg_pixmap_item:
            scene_pos = self.mapToScene(event.pos())
            from PyQt6.QtWidgets import QMenu
            menu = QMenu(self)
            
            add_act = menu.addAction("➕ Add Label Here...")
            menu.addSeparator()
            span_act = menu.addAction("📏 Mark Well Boundaries...")
            align_act = menu.addAction("🔄 Align Image (2-Click)...")
            fit_act = menu.addAction("⛶ Fit Gel to Window")
            menu.addSeparator()
            
            main_win = self.window()
            has_clipboard = hasattr(main_win, 'clipboard_labels') and bool(main_win.clipboard_labels)
            paste_act = menu.addAction("📋 Paste Labels")
            paste_act.setEnabled(has_clipboard)
            
            clear_act = menu.addAction("🗑 Clear All Labels")
            clear_act.setEnabled(bool(self.project.labels))
            
            action = menu.exec(event.globalPos())
            if action == add_act:
                self.prompt_add_label_at(scene_pos.x(), scene_pos.y())
            elif action == span_act:
                if hasattr(main_win, 'start_span_marking_dialog'):
                    main_win.start_span_marking_dialog()
            elif action == align_act:
                self.enter_align_mode()
            elif action == fit_act:
                self.fit_image_in_view()
            elif action == paste_act:
                if hasattr(main_win, 'paste_labels'):
                    main_win.paste_labels()
            elif action == clear_act:
                if hasattr(main_win, 'clear_labels_confirm'):
                    main_win.clear_labels_confirm()
            return
            
        super().contextMenuEvent(event)

    def prompt_add_label_at(self, x: float, y: float):
        """Opens SettingsDialog to add a label at the specified coordinates."""
        if not self.bg_pixmap_item:
            return
            
        from gel_labeler.gui.settings_dialog import SettingsDialog
        
        main_win = self.window()
        color = getattr(main_win, 'default_label_color', DEFAULT_COLOR)
        size = getattr(main_win, 'default_label_size', DEFAULT_FONT_SIZE)
        font_family = getattr(main_win, 'default_label_font_family', "Arial")
        
        # Suggest next number if existing labels are numeric
        default_text = "Lane 1"
        all_labels = self.project.get_labels_list()
        numeric_labels = []
        for l in all_labels:
            if l.text.isdigit():
                numeric_labels.append(int(l.text))
        if numeric_labels:
            default_text = str(max(numeric_labels) + 1)
            
        dialog = SettingsDialog(parent=self, initial_text=default_text, initial_color=color, initial_font_size=size)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            text, col, sz, rot = dialog.get_values()
            if text:
                new_label = self.project.add_label(
                    text=text,
                    x=x,
                    y=y,
                    color=col,
                    font_size=sz,
                    font_family=font_family,
                    rotation=rot
                )
                self.create_label_item(new_label)
                if self.on_project_modified:
                    self.on_project_modified()
                if self.on_status_message:
                    self.on_status_message(f"Added label '{text}' at ({int(x)}, {int(y)})")



    # --- Label CRUD Operations ---

    def create_label_item(self, label):
        """Helper to create and add a LabelItem to the graphics scene."""
        item = LabelItem(
            label_data=label,
            position_changed_callback=self.handle_label_dragged,
            delete_callback=self.handle_label_deleted,
            update_callback=self.handle_label_updated
        )
        self.scene.addItem(item)
        self.label_items[label.id] = item

    def handle_label_dragged(self, label_id: str, new_x: float, new_y: float):
        """Callback from LabelItem when it has finished being dragged."""
        if self.on_project_modified:
            self.on_project_modified()
        if self.on_status_message:
            self.on_status_message(f"Moved label to ({int(new_x)}, {int(new_y)})")

    def handle_label_deleted(self, label_id: str):
        """Callback from LabelItem to remove itself from the project and scene."""
        # Defer deletion to prevent PyQt C++ event handling crashes if triggered from within item event handlers
        QTimer.singleShot(0, lambda: self._do_delete_label(label_id))

    def _do_delete_label(self, label_id: str):
        if label_id in self.label_items:
            item = self.label_items[label_id]
            self.scene.removeItem(item)
            del self.label_items[label_id]
            
        label_text = ""
        if label_id in self.project.labels:
            label_text = self.project.labels[label_id].text
            self.project.remove_label(label_id)
            
        if self.on_project_modified:
            self.on_project_modified()
            
        if self.on_status_message:
            self.on_status_message(f"Deleted label '{label_text}'")

    def handle_label_updated(self, label_id: str):
        """Callback from LabelItem when text/styling has been modified."""
        if self.on_project_modified:
            self.on_project_modified()
        if self.on_status_message:
            label = self.project.labels.get(label_id)
            if label:
                self.on_status_message(f"Updated label '{label.text}'")

    def clear_all_labels(self):
        """Clears all labels from both the UI scene and project model."""
        if not self.bg_pixmap_item:
            return
            
        for item in self.label_items.values():
            self.scene.removeItem(item)
        self.label_items.clear()
        self.project.clear_labels()
        
        if self.on_project_modified:
            self.on_project_modified()
        if self.on_status_message:
            self.on_status_message("Cleared all labels.")

    def align_selected_labels(self, alignment_type: str):
        """Aligns or distributes selected labels similar to PowerPoint shapes."""
        selected_items = self.scene.selectedItems()
        # Filter to only LabelItems
        selected_items = [item for item in selected_items if hasattr(item, 'label_data')]
        
        n = len(selected_items)
        if n < 2:
            if self.on_status_message:
                self.on_status_message("Select at least 2 labels to align.")
            return
            
        if "Distribute" in alignment_type and n < 3:
            if self.on_status_message:
                self.on_status_message("Select at least 3 labels to distribute.")
            return

        self.project.save_undo_state()
        
        # Calculate bounding boxes
        rects = [item.sceneBoundingRect() for item in selected_items]
        
        if alignment_type == "Left":
            min_left = min(r.left() for r in rects)
            for item in selected_items:
                dx = min_left - item.sceneBoundingRect().left()
                new_pos = item.pos() + QPointF(dx, 0)
                item.setPos(new_pos)
                item.label_data.update_position(new_pos.x(), new_pos.y())
                
        elif alignment_type == "Right":
            max_right = max(r.right() for r in rects)
            for item in selected_items:
                dx = max_right - item.sceneBoundingRect().right()
                new_pos = item.pos() + QPointF(dx, 0)
                item.setPos(new_pos)
                item.label_data.update_position(new_pos.x(), new_pos.y())
                
        elif alignment_type == "Center":
            # Horizontal Center
            union_rect = QRectF()
            for r in rects:
                union_rect = union_rect.united(r)
            target_center_x = union_rect.center().x()
            for item in selected_items:
                dx = target_center_x - item.sceneBoundingRect().center().x()
                new_pos = item.pos() + QPointF(dx, 0)
                item.setPos(new_pos)
                item.label_data.update_position(new_pos.x(), new_pos.y())
                
        elif alignment_type == "Top":
            min_top = min(r.top() for r in rects)
            for item in selected_items:
                dy = min_top - item.sceneBoundingRect().top()
                new_pos = item.pos() + QPointF(0, dy)
                item.setPos(new_pos)
                item.label_data.update_position(new_pos.x(), new_pos.y())
                
        elif alignment_type == "Bottom":
            max_bottom = max(r.bottom() for r in rects)
            for item in selected_items:
                dy = max_bottom - item.sceneBoundingRect().bottom()
                new_pos = item.pos() + QPointF(0, dy)
                item.setPos(new_pos)
                item.label_data.update_position(new_pos.x(), new_pos.y())
                
        elif alignment_type == "Middle":
            # Vertical Middle
            union_rect = QRectF()
            for r in rects:
                union_rect = union_rect.united(r)
            target_middle_y = union_rect.center().y()
            for item in selected_items:
                dy = target_middle_y - item.sceneBoundingRect().center().y()
                new_pos = item.pos() + QPointF(0, dy)
                item.setPos(new_pos)
                item.label_data.update_position(new_pos.x(), new_pos.y())
                
        elif alignment_type == "DistributeHorizontally":
            # Sort items left-to-right by center X
            sorted_pairs = sorted(zip(selected_items, rects), key=lambda pair: pair[1].center().x())
            left_center = sorted_pairs[0][1].center().x()
            right_center = sorted_pairs[-1][1].center().x()
            span = right_center - left_center
            step = span / (n - 1)
            
            for idx, (item, r) in enumerate(sorted_pairs):
                target_center_x = left_center + idx * step
                dx = target_center_x - r.center().x()
                new_pos = item.pos() + QPointF(dx, 0)
                item.setPos(new_pos)
                item.label_data.update_position(new_pos.x(), new_pos.y())
                
        elif alignment_type == "DistributeVertically":
            # Sort items top-to-bottom by center Y
            sorted_pairs = sorted(zip(selected_items, rects), key=lambda pair: pair[1].center().y())
            top_center = sorted_pairs[0][1].center().y()
            bottom_center = sorted_pairs[-1][1].center().y()
            span = bottom_center - top_center
            step = span / (n - 1)
            
            for idx, (item, r) in enumerate(sorted_pairs):
                target_center_y = top_center + idx * step
                dy = target_center_y - r.center().y()
                new_pos = item.pos() + QPointF(0, dy)
                item.setPos(new_pos)
                item.label_data.update_position(new_pos.x(), new_pos.y())

        self.project.is_dirty = True
        if self.on_project_modified:
            self.on_project_modified()
        if self.on_status_message:
            self.on_status_message(f"Aligned selected labels: {alignment_type}")
        self.scene.update()

    def enter_span_mode(self, config: dict):
        """Enters interactive two-click lane span placement mode."""
        self.span_mode = True
        self.span_config = config
        self.span_first_point = None
        
        # Cancel align modes
        self.cancel_align_mode()
        
        # Remove any pre-existing temp markers
        if self.temp_marker:
            self.scene.removeItem(self.temp_marker)
            self.temp_marker = None
            
        self.setCursor(Qt.CursorShape.CrossCursor)
        if self.on_status_message:
            self.on_status_message(f"Span Mode: Click the leftmost well for {config.get('name')}")

    def cancel_span_mode(self):
        """Aborts interactive span placement."""
        self.span_mode = False
        self.span_first_point = None
        if self.temp_marker:
            self.scene.removeItem(self.temp_marker)
            self.temp_marker = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if self.on_status_message:
            self.on_status_message("Span placement cancelled.")

    def enter_align_mode(self):
        """Enters interactive 2-click alignment mode."""
        self.align_mode = True
        self.align_first_point = None
        if self.temp_marker:
            self.scene.removeItem(self.temp_marker)
            self.temp_marker = None
            
        # Cancel other modes
        self.cancel_span_mode()
        
        self.setCursor(Qt.CursorShape.CrossCursor)
        if self.on_status_message:
            self.on_status_message("Align Mode: Click the first point along the reference line (e.g. leftmost well).")

    def cancel_align_mode(self):
        """Aborts alignment mode."""
        self.align_mode = False
        self.align_first_point = None
        if self.temp_marker:
            self.scene.removeItem(self.temp_marker)
            self.temp_marker = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if self.on_status_message:
            self.on_status_message("Alignment cancelled.")


    def keyPressEvent(self, event):
        """Handles key press events (arrow keys to nudge selected labels)."""
        selected_items = self.scene.selectedItems()
        if not selected_items:
            super().keyPressEvent(event)
            return

        key = event.key()

        # Handle selection cycling on Enter/Return press
        if key == Qt.Key.Key_Enter or key == Qt.Key.Key_Return:
            all_labels = self.project.get_labels_list()
            if len(all_labels) > 1:
                # Sort primarily by Y decks (proximity of 50px) and secondarily by X
                sorted_labels = sorted(all_labels, key=lambda l: (round(l.y / 50) * 50, l.x))
                current_label = selected_items[0].label_data
                try:
                    idx = sorted_labels.index(current_label)
                    next_idx = (idx + 1) % len(sorted_labels)
                    next_label = sorted_labels[next_idx]
                    
                    self.scene.clearSelection()
                    if next_label.id in self.label_items:
                        self.label_items[next_label.id].setSelected(True)
                        if hasattr(self.window(), 'update_selection_status'):
                            self.window().update_selection_status()
                except ValueError:
                    pass
            event.accept()
            return

        # Handle deletion of selected items
        if key == Qt.Key.Key_Delete or key == Qt.Key.Key_Backspace:
            self.project.save_undo_state()
            self.project._in_batch_operation = True
            try:
                for item in list(selected_items):
                    if hasattr(item, 'label_data'):
                        self._do_delete_label(item.label_data.id)
            finally:
                self.project._in_batch_operation = False
            event.accept()
            return

        dx, dy = 0, 0

        # Move by 5px if Shift is pressed, otherwise 1px
        step = 5 if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 1

        if key == Qt.Key.Key_Left:
            dx = -step
        elif key == Qt.Key.Key_Right:
            dx = step
        elif key == Qt.Key.Key_Up:
            dy = -step
        elif key == Qt.Key.Key_Down:
            dy = step
        else:
            super().keyPressEvent(event)
            return

        # Move all selected items
        modified = False
        for item in selected_items:
            if hasattr(item, 'label_data'):
                if not modified:
                    self.project.save_undo_state()
                new_pos = item.pos() + QPointF(dx, dy)
                item.setPos(new_pos)
                
                # Get the actual clamped position
                actual_pos = item.pos()
                item.label_data.update_position(actual_pos.x(), actual_pos.y())
                modified = True

        if modified:
            self.project.is_dirty = True
            if self.on_project_modified:
                self.on_project_modified()
            # Update coordinate status readout in main window
            if hasattr(self.window(), 'update_selection_status'):
                self.window().update_selection_status()
            self.scene.update()

        event.accept()

