import os
import csv
import numpy as np
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QLinearGradient, QPainterPath, QFont
from gel_labeler.core.project import GelProject
from gel_labeler.core.label import GelLabel

class ProfileGraphWidget(QWidget):
    """Custom widget to draw the vertical lane pixel intensity profile."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile_data = None
        self.image_height = 0
        self.active_label = None
        self.other_labels = []
        
        # Style variables
        self.bg_color = QColor("#151515")
        self.grid_color = QColor("#22222a")
        self.text_color = QColor("#9d9d9d")
        self.curve_color = QColor("#e29c3d")  # Blender Orange
        self.active_line_color = QColor("#ff5500")  # Blender active horizontal line
        self.sibling_line_color = QColor("#4c4c4c")  # Muted sibling guide lines
        
        self.setMinimumWidth(150)
        self.setMinimumHeight(300)

    def set_data(self, profile, img_height, active_label, other_labels):
        self.profile_data = profile
        self.image_height = img_height
        self.active_label = active_label
        self.other_labels = other_labels
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dimensions
        w = self.width()
        h = self.height()
        
        # Fill background
        painter.fillRect(0, 0, w, h, self.bg_color)
        
        # Margins
        margin_left = 35
        margin_right = 15
        margin_top = 15
        margin_bottom = 25
        
        plot_w = w - margin_left - margin_right
        plot_h = h - margin_top - margin_bottom
        
        if plot_w <= 0 or plot_h <= 0:
            return
            
        # Draw border
        painter.setPen(QPen(self.grid_color, 1))
        painter.drawRect(margin_left, margin_top, plot_w, plot_h)
        
        # Draw horizontal grid lines & labels (migration distance Y)
        painter.setFont(QFont("Arial", 8))
        num_y_grid = 5
        for i in range(num_y_grid + 1):
            grid_y = margin_top + int(i * plot_h / num_y_grid)
            painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))
            painter.drawLine(margin_left, grid_y, w - margin_right, grid_y)
            
            # Map grid Y back to gel image Y
            if self.image_height > 0:
                gel_y = int(i * self.image_height / num_y_grid)
                painter.setPen(self.text_color)
                painter.drawText(5, grid_y + 4, f"{gel_y}")
                
        # Draw vertical grid lines & labels (Intensity)
        num_x_grid = 4
        for i in range(num_x_grid + 1):
            val = int(i * 255 / num_x_grid)
            grid_x = margin_left + int(i * plot_w / num_x_grid)
            painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))
            painter.drawLine(grid_x, margin_top, grid_x, h - margin_bottom)
            
            painter.setPen(self.text_color)
            painter.drawText(grid_x - 10, h - 8, f"{val}")
            
        # Draw axis label
        painter.setPen(self.text_color)
        painter.drawText(margin_left + plot_w // 2 - 20, h - 22, "Intensity")
        
        if self.profile_data is None or len(self.profile_data) == 0:
            # Draw placeholder message
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            painter.setPen(self.text_color)
            painter.drawText(margin_left + 10, margin_top + plot_h // 2, "No lane data")
            return
            
        # Draw the curve
        n_points = len(self.profile_data)
        path = QPainterPath()
        
        # Helper to map (intensity, index) -> (widget_x, widget_y)
        def map_coords(intensity, idx):
            # Intensity goes 0..255 -> plot_w
            # Index goes 0..n_points-1 -> plot_h
            px = margin_left + (intensity / 255.0) * plot_w
            py = margin_top + (idx / float(n_points - 1)) * plot_h
            return px, py
            
        # Build path and gradient area
        x0, y0 = map_coords(self.profile_data[0], 0)
        path.moveTo(x0, y0)
        
        area_path = QPainterPath()
        area_path.moveTo(margin_left, y0)
        area_path.lineTo(x0, y0)
        
        for i in range(1, n_points):
            px, py = map_coords(self.profile_data[i], i)
            path.lineTo(px, py)
            area_path.lineTo(px, py)
            
        xn, yn = map_coords(self.profile_data[-1], n_points - 1)
        area_path.lineTo(margin_left, yn)
        area_path.closeSubpath()
        
        # Fill gradient
        grad = QLinearGradient(margin_left, 0, w - margin_right, 0)
        grad.setColorAt(0.0, QColor(226, 156, 61, 10))
        grad.setColorAt(1.0, QColor(226, 156, 61, 50))
        painter.fillPath(area_path, QBrush(grad))
        
        # Draw curve path
        painter.setPen(QPen(self.curve_color, 2, Qt.PenStyle.SolidLine))
        painter.drawPath(path)
        
        # Draw sibling/other labels on the same lane (grey lines)
        if self.image_height > 0:
            for sibling in self.other_labels:
                sibling_y = margin_top + int(sibling.y * plot_h / self.image_height)
                if margin_top <= sibling_y <= margin_top + plot_h:
                    painter.setPen(QPen(self.sibling_line_color, 1.5, Qt.PenStyle.DotLine))
                    painter.drawLine(margin_left, sibling_y, w - margin_right, sibling_y)
                    
                    # Label name tag
                    painter.setPen(self.sibling_line_color)
                    painter.setFont(QFont("Arial", 8))
                    painter.drawText(margin_left + 5, sibling_y - 4, sibling.text)
                    
            # Draw active label line (pink/red line)
            if self.active_label:
                active_y = margin_top + int(self.active_label.y * plot_h / self.image_height)
                if margin_top <= active_y <= margin_top + plot_h:
                    painter.setPen(QPen(self.active_line_color, 2, Qt.PenStyle.DashLine))
                    painter.drawLine(margin_left, active_y, w - margin_right, active_y)
                    
                    # Highlight active label text
                    painter.setPen(self.active_line_color)
                    painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
                    painter.drawText(margin_left + 5, active_y - 4, f"★ {self.active_label.text}")


class LaneProfilePanel(QWidget):
    """Sidebar panel representing the lane profile viewer."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.selected_label = None
        self.profile = None
        self.img_height = 0
        
        self.setStyleSheet("""
            QWidget {
                background-color: #2e2e2e;
                border-left: 1px solid #151515;
            }
            QLabel {
                color: #cfcfcf;
                font-family: 'Inter', Arial;
                border: none;
            }
            QPushButton {
                background-color: #545454;
                color: #cfcfcf;
                border: 1px solid #2b2b2b;
                border-radius: 3px;
                padding: 6px 10px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #616161;
                border-color: #e29c3d;
            }
            QPushButton:pressed {
                background-color: #e29c3d;
                color: #151515;
            }
        """)
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # Header Row
        header_layout = QHBoxLayout()
        header_title = QLabel("📊 Lane Profile Viewer")
        header_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #e29c3d;")
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #8E8EA8;
                font-size: 14px;
                padding: 0;
            }
            QPushButton:hover {
                color: #e29c3d;
            }
        """)
        self.close_btn.clicked.connect(self.hide_panel)
        
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)
        layout.addLayout(header_layout)
        
        # Selected Lane Info
        self.info_label = QLabel("No active lane selected.")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #8E8EA8; font-size: 11px; padding: 4px 0;")
        layout.addWidget(self.info_label)
        
        # Graph Widget
        self.graph = ProfileGraphWidget(self)
        layout.addWidget(self.graph, 1)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        self.csv_btn = QPushButton("📄 CSV")
        self.csv_btn.setToolTip("Export the intensity profile data to a CSV spreadsheet")
        self.csv_btn.clicked.connect(self.export_csv)
        self.csv_btn.setEnabled(False)
        
        self.graph_btn = QPushButton("🖼 Graph")
        self.graph_btn.setToolTip("Save the plotted graph as a PNG image")
        self.graph_btn.clicked.connect(self.export_graph)
        self.graph_btn.setEnabled(False)
        
        btn_layout.addWidget(self.csv_btn)
        btn_layout.addWidget(self.graph_btn)
        layout.addLayout(btn_layout)

    def set_project(self, project: GelProject):
        self.project = project
        self.selected_label = None
        self.profile = None
        self.graph.set_data(None, 0, None, [])
        self.info_label.setText("No active lane selected. Click a well/lane label to view profile.")
        self.csv_btn.setEnabled(False)
        self.graph_btn.setEnabled(False)

    def set_selected_label(self, label: GelLabel):
        self.selected_label = label
        if not self.project or not label or self.project.gray_data is None:
            self.profile = None
            self.graph.set_data(None, 0, None, [])
            self.info_label.setText("No active lane selected. Click a well/lane label to view profile.")
            self.csv_btn.setEnabled(False)
            self.graph_btn.setEnabled(False)
            return
            
        # Extract profile at label X coordinate
        gray = self.project.gray_data
        H, W = gray.shape
        self.img_height = H
        
        # Sample average across a small horizontal column slice centered at X
        col = max(0, min(W - 1, int(round(label.x))))
        lw = 9  # Linewidth
        col_min = max(0, col - lw // 2)
        col_max = min(W - 1, col + lw // 2)
        
        if col_max >= col_min:
            self.profile = np.mean(gray[:, col_min:col_max + 1], axis=1)
        else:
            self.profile = gray[:, col].astype(float)
            
        # Find sibling labels on the same lane (similar X coordinate)
        other_labels = []
        for l in self.project.labels.values():
            if l.id != label.id:
                # Group if horizontal coordinates are within 35 pixels of each other
                if abs(l.x - label.x) < 35:
                    other_labels.append(l)
                    
        self.graph.set_data(self.profile, H, label, other_labels)
        self.info_label.setText(f"Active: '{label.text}' at X={int(label.x)} px\nWidth: {lw} px column average")
        self.csv_btn.setEnabled(True)
        self.graph_btn.setEnabled(True)

    def update_drag_position(self, label_id: str, new_x: float, new_y: float):
        """Called in real-time when the selected label is dragged."""
        if self.selected_label and self.selected_label.id == label_id:
            # Create a temporary label state to recalculate profile
            temp_label = GelLabel(
                self.selected_label.text, 
                new_x, 
                new_y, 
                self.selected_label.color, 
                self.selected_label.font_size, 
                self.selected_label.font_family,
                self.selected_label.rotation
            )
            temp_label.id = label_id
            self.set_selected_label(temp_label)

    def hide_panel(self):
        """Hides the profile panel, expanding the main canvas view."""
        self.setVisible(False)
        # Notify MainWindow
        if hasattr(self.window(), 'sync_profile_button_state'):
            self.window().sync_profile_button_state()

    def export_csv(self):
        if self.profile is None or not self.selected_label:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Lane Profile (CSV)", 
            f"profile_{self.selected_label.text.replace(' ', '_')}.csv",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Y_pixel", "Intensity"])
                    for y_idx, val in enumerate(self.profile):
                        writer.writerow([y_idx, round(val, 2)])
                QMessageBox.information(self, "Export Success", f"Profile exported to {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save CSV file: {e}")

    def export_graph(self):
        if self.profile is None or not self.selected_label:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Profile Graph (PNG)", 
            f"profile_{self.selected_label.text.replace(' ', '_')}.png",
            "PNG Files (*.png);;All Files (*)"
        )
        
        if file_path:
            try:
                pixmap = self.graph.grab()
                if pixmap.save(file_path, "PNG"):
                    QMessageBox.information(self, "Export Success", f"Graph exported to {os.path.basename(file_path)}")
                else:
                    QMessageBox.critical(self, "Export Error", "Failed to render or save image file.")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export graph: {e}")
