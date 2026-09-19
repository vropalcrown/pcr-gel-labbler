import os
import csv
import cv2
import numpy as np
from typing import List, Optional

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSlider, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QFileDialog, 
    QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsEllipseItem, QGraphicsTextItem, QFormLayout, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QFont


from gel_labeler.core.colony_detector import ColonyDetector, ColonyObject


class ColonyCanvas(QGraphicsView):
    """Interactive viewport for viewing plate images and placing/deleting colony markers."""

    def __init__(self, parent_dialog=None):
        super().__init__(parent_dialog)
        self.parent_dialog = parent_dialog
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.bg_pixmap_item: Optional[QGraphicsPixmapItem] = None
        self.dish_ring_item: Optional[QGraphicsEllipseItem] = None
        self.marker_items: List[dict] = []  # List of {obj, ellipse_item, text_item}
        self.colonies: List[ColonyObject] = []
        self.marker_color = "#FF3366"
        self.marker_size = 10
        self.show_numbers = True

    def set_image(self, pixmap: QPixmap):
        self.scene.clear()
        self.marker_items.clear()
        self.dish_ring_item = None
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())

        self.bg_pixmap_item = QGraphicsPixmapItem(pixmap)
        self.bg_pixmap_item.setZValue(-10)
        self.scene.addItem(self.bg_pixmap_item)

        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def draw_dish_boundary(self, dish_circle: Optional[tuple]):
        if self.dish_ring_item:
            self.scene.removeItem(self.dish_ring_item)
            self.dish_ring_item = None

        if dish_circle:
            cx, cy, r = dish_circle
            pen = QPen(QColor(0, 255, 204, 180), 2, Qt.PenStyle.DashLine)
            self.dish_ring_item = self.scene.addEllipse(cx - r, cy - r, r * 2, r * 2, pen)
            self.dish_ring_item.setZValue(-2)

    def render_markers(self, colonies: List[ColonyObject], dish_circle: Optional[tuple] = None):
        self.colonies = colonies

        # Clear existing graphical marker items
        for item in self.marker_items:
            if item.get("ellipse"):
                self.scene.removeItem(item["ellipse"])
            if item.get("text"):
                self.scene.removeItem(item["text"])
        self.marker_items.clear()

        if dish_circle:
            self.draw_dish_boundary(dish_circle)

        qcolor = QColor(self.marker_color)
        pen = QPen(qcolor, 2)
        brush = QBrush(QColor(qcolor.red(), qcolor.green(), qcolor.blue(), 60))

        font = QFont("Arial", max(7, int(self.marker_size * 0.8)), QFont.Weight.Bold)

        for col in self.colonies:
            r = max(3.0, float(self.marker_size))
            el = self.scene.addEllipse(col.x - r, col.y - r, r * 2, r * 2, pen, brush)
            el.setZValue(5)

            txt_item = None
            if self.show_numbers:
                txt_item = QGraphicsTextItem(str(col.id))
                txt_item.setFont(font)
                txt_item.setDefaultTextColor(QColor("#FFFFFF"))
                txt_item.setPos(col.x + r - 2, col.y - r - 2)
                txt_item.setZValue(6)
                self.scene.addItem(txt_item)

            self.marker_items.append({
                "colony": col,
                "ellipse": el,
                "text": txt_item
            })

    def wheelEvent(self, event):
        """Zoom with Ctrl + Mouse Wheel."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.25 if event.angleDelta().y() > 0 else 0.8
            self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        """Left click = Add colony; Right click = Remove clicked colony."""
        if not self.bg_pixmap_item:
            super().mousePressEvent(event)
            return

        scene_pos = self.mapToScene(event.pos())
        x, y = scene_pos.x(), scene_pos.y()

        if event.button() == Qt.MouseButton.LeftButton:
            # Add manual colony marker
            next_id = (max([c.id for c in self.colonies], default=0) + 1)
            new_col = ColonyObject(
                obj_id=next_id,
                x=x,
                y=y,
                radius=float(self.marker_size),
                is_manual=True
            )
            self.colonies.append(new_col)
            self.render_markers(self.colonies)
            if self.parent_dialog:
                self.parent_dialog.update_statistics()

        elif event.button() == Qt.MouseButton.RightButton:
            # Delete closest marker within clicking threshold
            threshold = max(15.0, float(self.marker_size * 2))
            closest_idx = -1
            min_dist = float("inf")

            for i, col in enumerate(self.colonies):
                dist = np.hypot(col.x - x, col.y - y)
                if dist < threshold and dist < min_dist:
                    min_dist = dist
                    closest_idx = i

            if closest_idx != -1:
                del self.colonies[closest_idx]
                self.render_markers(self.colonies)
                if self.parent_dialog:
                    self.parent_dialog.update_statistics()

        super().mousePressEvent(event)


class ColonyCounterDialog(QDialog):
    """Modern standalone AI Vision Colony and Seed Counter modal window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🧫 AI Vision Colony & Seed Counter — Gel Labeler")
        self.resize(1150, 720)
        self.setMinimumSize(900, 600)

        self.image_path: Optional[str] = None
        self.raw_cv_image: Optional[np.ndarray] = None
        self.last_dish_circle: Optional[tuple] = None

        self._detect_timer = QTimer(self)
        self._detect_timer.setSingleShot(True)
        self._detect_timer.setInterval(80)
        self._detect_timer.timeout.connect(self._run_live_detection)

        self.init_ui()
        self.apply_dark_theme()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: 'Inter', Arial, sans-serif;
            }
            QGroupBox {
                background-color: #262626;
                border: 1px solid #333333;
                border-radius: 6px;
                margin-top: 14px;
                padding-top: 14px;
                font-weight: bold;
                font-size: 12px;
                color: #e29c3d;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 5px;
            }
            QLabel {
                color: #cfcfcf;
                font-size: 11px;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #484848;
                border-radius: 4px;
                padding: 6px 14px;
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #e29c3d;
            }
            QPushButton#accentBtn {
                background-color: #e29c3d;
                color: #121212;
                border: none;
            }
            QPushButton#accentBtn:hover {
                background-color: #f1b35c;
            }
            QPushButton#successBtn {
                background-color: #2a9d8f;
                color: #ffffff;
                border: none;
            }
            QPushButton#successBtn:hover {
                background-color: #3eb5a6;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #121212;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #e29c3d;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #141414;
                border: 1px solid #333333;
                border-radius: 3px;
                padding: 3px 6px;
                color: #ffffff;
                font-size: 11px;
            }
            QCheckBox {
                color: #ffffff;
                font-size: 11px;
                font-weight: 500;
            }
        """)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Left Control Sidebar (scrollable or fixed width)
        sidebar = QWidget()
        sidebar.setFixedWidth(330)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(10)

        # 1. Image Loader Group
        img_group = QGroupBox("Plate / Tray Image")
        img_layout = QVBoxLayout(img_group)
        self.load_btn = QPushButton("📁 Load Plate / Seed Image...")
        self.load_btn.setObjectName("accentBtn")
        self.load_btn.clicked.connect(self.open_image_dialog)
        img_layout.addWidget(self.load_btn)

        self.img_info_lbl = QLabel("No image loaded")
        self.img_info_lbl.setStyleSheet("color: #888888; font-style: italic;")
        img_layout.addWidget(self.img_info_lbl)
        sidebar_layout.addWidget(img_group)

        # 2. AI Vision Parameters Group
        ai_group = QGroupBox("AI Vision Parameters")
        ai_form = QFormLayout(ai_group)
        ai_form.setSpacing(8)

        # Sensitivity Slider
        self.sens_slider = QSlider(Qt.Orientation.Horizontal)
        self.sens_slider.setRange(1, 100)
        self.sens_slider.setValue(50)
        self.sens_lbl = QLabel("50")
        sens_row = QHBoxLayout()
        sens_row.addWidget(self.sens_slider)
        sens_row.addWidget(self.sens_lbl)
        self.sens_slider.valueChanged.connect(lambda v: (self.sens_lbl.setText(str(v)), self.trigger_live_detection()))
        ai_form.addRow("Sensitivity:", sens_row)

        # Min / Max Radius
        self.min_rad_spin = QSpinBox()
        self.min_rad_spin.setRange(1, 100)
        self.min_rad_spin.setValue(4)
        self.min_rad_spin.valueChanged.connect(self.trigger_live_detection)

        self.max_rad_spin = QSpinBox()
        self.max_rad_spin.setRange(5, 500)
        self.max_rad_spin.setValue(45)
        self.max_rad_spin.valueChanged.connect(self.trigger_live_detection)

        rad_row = QHBoxLayout()
        rad_row.addWidget(QLabel("Min:"))
        rad_row.addWidget(self.min_rad_spin)
        rad_row.addWidget(QLabel("Max:"))
        rad_row.addWidget(self.max_rad_spin)
        ai_form.addRow("Size (px):", rad_row)

        # Circularity Filter
        self.circ_slider = QSlider(Qt.Orientation.Horizontal)
        self.circ_slider.setRange(1, 99)
        self.circ_slider.setValue(40)
        self.circ_lbl = QLabel("0.40")
        circ_row = QHBoxLayout()
        circ_row.addWidget(self.circ_slider)
        circ_row.addWidget(self.circ_lbl)
        self.circ_slider.valueChanged.connect(lambda v: (self.circ_lbl.setText(f"{v/100:.2f}"), self.trigger_live_detection()))
        ai_form.addRow("Circularity:", circ_row)

        # Petri Dish Auto-Mask Checkbox
        self.mask_dish_chk = QCheckBox("Auto-Mask Dish Rim (Ignore Edges)")
        self.mask_dish_chk.setChecked(True)
        self.mask_dish_chk.stateChanged.connect(self.trigger_live_detection)
        ai_form.addRow(self.mask_dish_chk)

        # Invert Checkbox (Light on Dark vs Dark on Light)
        self.invert_chk = QCheckBox("Invert (Fluorescent / Light Colonies)")
        self.invert_chk.setChecked(False)
        self.invert_chk.stateChanged.connect(self.trigger_live_detection)
        ai_form.addRow(self.invert_chk)

        # Watershed Separation
        self.watershed_chk = QCheckBox("Watershed (Separate Touching)")
        self.watershed_chk.setChecked(True)
        self.watershed_chk.stateChanged.connect(self.trigger_live_detection)
        ai_form.addRow(self.watershed_chk)

        sidebar_layout.addWidget(ai_group)

        # 3. Markers & Styling Group
        style_group = QGroupBox("Marker Appearance")
        style_form = QFormLayout(style_group)
        style_form.setSpacing(8)

        self.marker_color_combo = QComboBox()
        self.marker_color_combo.addItems(["Neon Red", "Electric Cyan", "Neon Green", "Vibrant Yellow", "Pure White"])
        self.marker_color_combo.currentIndexChanged.connect(self.update_marker_style)
        style_form.addRow("Marker Color:", self.marker_color_combo)

        self.marker_size_spin = QSpinBox()
        self.marker_size_spin.setRange(3, 50)
        self.marker_size_spin.setValue(10)
        self.marker_size_spin.valueChanged.connect(self.update_marker_style)
        style_form.addRow("Marker Size:", self.marker_size_spin)

        self.show_numbers_chk = QCheckBox("Show Colony ID Numbers")
        self.show_numbers_chk.setChecked(True)
        self.show_numbers_chk.stateChanged.connect(self.update_marker_style)
        style_form.addRow(self.show_numbers_chk)

        sidebar_layout.addWidget(style_group)

        # 4. CFU & Density Calculator Group
        cfu_group = QGroupBox("CFU / Density Calculator")
        cfu_form = QFormLayout(cfu_group)
        cfu_form.setSpacing(6)

        self.volume_spin = QDoubleSpinBox()
        self.volume_spin.setRange(0.001, 1000.0)
        self.volume_spin.setValue(0.1)  # 0.1 mL = 100 uL
        self.volume_spin.setDecimals(3)
        self.volume_spin.valueChanged.connect(self.update_statistics)
        cfu_form.addRow("Plated Vol (mL):", self.volume_spin)

        self.dilution_combo = QComboBox()
        self.dilution_combo.addItems([
            "10⁰ (Undiluted - 1x)",
            "10⁻¹ (1:10)",
            "10⁻² (1:100)",
            "10⁻³ (1:1,000)",
            "10⁻⁴ (1:10,000)",
            "10⁻⁵ (1:100,000)",
            "10⁻⁶ (1:1,000,000)"
        ])
        self.dilution_combo.setCurrentIndex(0)
        self.dilution_combo.currentIndexChanged.connect(self.update_statistics)
        cfu_form.addRow("Dilution Factor:", self.dilution_combo)

        # Summary Display
        self.stat_count_lbl = QLabel("<b>Count:</b> 0")
        self.stat_count_lbl.setStyleSheet("color: #e29c3d; font-size: 14px; font-weight: bold;")
        cfu_form.addRow(self.stat_count_lbl)

        self.stat_cfu_lbl = QLabel("<b>CFU/mL:</b> 0.00")
        self.stat_cfu_lbl.setStyleSheet("color: #00ffcc; font-size: 13px; font-weight: bold;")
        cfu_form.addRow(self.stat_cfu_lbl)

        sidebar_layout.addWidget(cfu_group)

        # 5. Export Actions
        export_group = QGroupBox("Export Results")
        export_layout = QVBoxLayout(export_group)
        export_layout.setSpacing(6)

        self.export_img_btn = QPushButton("🖼️ Export Annotated Image...")
        self.export_img_btn.clicked.connect(self.export_image)
        export_layout.addWidget(self.export_img_btn)

        self.export_csv_btn = QPushButton("📊 Export CSV Table...")
        self.export_csv_btn.clicked.connect(self.export_csv)
        export_layout.addWidget(self.export_csv_btn)

        sidebar_layout.addWidget(export_group)
        sidebar_layout.addStretch()

        main_layout.addWidget(sidebar)

        # Right Interactive Canvas Area
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # Instructions Bar
        hint_lbl = QLabel("💡 <b>Instructions:</b> Left-Click to add missed colonies/seeds. Right-Click a marker to delete false positives. Ctrl + Wheel to Zoom.")
        hint_lbl.setStyleSheet("background-color: #242424; padding: 6px 10px; border-radius: 4px; color: #aaaaaa;")
        right_layout.addWidget(hint_lbl)

        # Canvas Viewport
        self.canvas = ColonyCanvas(self)
        right_layout.addWidget(self.canvas)

        main_layout.addWidget(right_panel, stretch=1)

    def open_image_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Petri Dish / Seed Tray Image", "",
            "Image Files (*.png *.jpg *.jpeg *.tif *.tiff *.bmp)"
        )
        if not path:
            return

        self.image_path = path
        self.raw_cv_image = cv2.imread(path)
        if self.raw_cv_image is None:
            QMessageBox.critical(self, "Error", "Could not load image file.")
            return

        pixmap = QPixmap(path)
        self.canvas.set_image(pixmap)
        self.img_info_lbl.setText(f"{os.path.basename(path)} ({pixmap.width()}x{pixmap.height()})")

        self.trigger_live_detection()

    def get_color_hex_from_combo(self) -> str:
        idx = self.marker_color_combo.currentIndex()
        colors = ["#FF3366", "#00FFFF", "#00FF00", "#FFFF00", "#FFFFFF"]
        return colors[idx] if idx < len(colors) else "#FF3366"

    def update_marker_style(self):
        self.canvas.marker_color = self.get_color_hex_from_combo()
        self.canvas.marker_size = self.marker_size_spin.value()
        self.canvas.show_numbers = self.show_numbers_chk.isChecked()
        self.canvas.render_markers(self.canvas.colonies, self.last_dish_circle)

    def trigger_live_detection(self):
        """Triggers live detection with debouncing to keep the GUI responsive during slider movements."""
        if self.raw_cv_image is None:
            return
        self._detect_timer.start(80)

    def _run_live_detection(self):
        if self.raw_cv_image is None:
            return

        manual_colonies = [c for c in self.canvas.colonies if c.is_manual]

        colonies, dish_circle = ColonyDetector.detect_colonies(
            image=self.raw_cv_image,
            min_radius=self.min_rad_spin.value(),
            max_radius=self.max_rad_spin.value(),
            sensitivity=self.sens_slider.value(),
            circularity_min=self.circ_slider.value() / 100.0,
            invert_mode=self.invert_chk.isChecked(),
            mask_petri_dish=self.mask_dish_chk.isChecked(),
            use_watershed=self.watershed_chk.isChecked()
        )

        # Retain manual markers and renumber
        next_id = len(colonies) + 1
        for mc in manual_colonies:
            mc.id = next_id
            colonies.append(mc)
            next_id += 1

        self.last_dish_circle = dish_circle
        self.canvas.marker_color = self.get_color_hex_from_combo()
        self.canvas.marker_size = self.marker_size_spin.value()
        self.canvas.show_numbers = self.show_numbers_chk.isChecked()
        self.canvas.render_markers(colonies, dish_circle)
        self.update_statistics()


    def get_current_dilution_factor(self) -> float:
        idx = self.dilution_combo.currentIndex()
        # 10^0 to 10^6 dilution reciprocal
        return float(10 ** idx)

    def update_statistics(self):
        count = len(self.canvas.colonies)
        vol = self.volume_spin.value()
        dilution = self.get_current_dilution_factor()
        cfu = ColonyDetector.calculate_cfu(count, vol, dilution)

        self.stat_count_lbl.setText(f"<b>Total Count:</b> {count} {'colonies' if not self.invert_chk.isChecked() else 'objects'}")
        self.stat_cfu_lbl.setText(f"<b>CFU/mL:</b> {cfu:,.1f}")

    def export_image(self):
        if not self.raw_cv_image is not None or not self.canvas.colonies:
            QMessageBox.warning(self, "No Data", "Please load an image and detect colonies first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Annotated Plate Image", "colony_counted.png",
            "PNG Image (*.png);;JPEG Image (*.jpg)"
        )
        if not file_path:
            return

        # Render full scene to high-resolution pixmap
        rect = self.canvas.scene.sceneRect()
        pixmap = QPixmap(int(rect.width()), int(rect.height()))
        pixmap.fill(Qt.GlobalColor.black)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.canvas.scene.render(painter)
        painter.end()

        pixmap.save(file_path)
        QMessageBox.information(self, "Export Successful", f"Annotated image saved to:\n{file_path}")

    def export_csv(self):
        if not self.canvas.colonies:
            QMessageBox.warning(self, "No Data", "No colonies detected to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Colony Data Table", "colony_results.csv",
            "CSV Spreadsheet (*.csv)"
        )
        if not file_path:
            return

        vol = self.volume_spin.value()
        dilution = self.get_current_dilution_factor()
        cfu_total = ColonyDetector.calculate_cfu(len(self.canvas.colonies), vol, dilution)

        def sanitize_cell(val):
            if val is None:
                return ""
            s = str(val)
            if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
                return f"'{s}"
            return s

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["# Colony & Seed AI Vision Report"])
            writer.writerow(["Source Image", sanitize_cell(self.image_path or "Unknown")])
            writer.writerow(["Total Count", len(self.canvas.colonies)])
            writer.writerow(["Plated Volume (mL)", vol])
            writer.writerow(["Dilution Factor", dilution])
            writer.writerow(["Estimated CFU/mL", f"{cfu_total:.2f}"])
            writer.writerow([])
            writer.writerow(["Colony ID", "X (px)", "Y (px)", "Radius (px)", "Area (px^2)", "Type"])

            for c in self.canvas.colonies:
                writer.writerow([
                    sanitize_cell(c.id),
                    c.x,
                    c.y,
                    c.radius,
                    c.area,
                    sanitize_cell("Manual" if c.is_manual else "AI Detected")
                ])

        QMessageBox.information(self, "Export Successful", f"Colony data exported to:\n{file_path}")
