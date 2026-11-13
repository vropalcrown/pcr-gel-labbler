"""
Interactive Multiwell Plate Designer & Labeler GUI Widget.
Supports 6-, 12-, 24-, 48-, 96-, 384-well plates and custom grid dimensions with
multi-selection, copy/paste, series numbering, color categorization, and CSV/image export.
"""
from typing import List, Set, Optional, Tuple

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QGroupBox, QTextEdit, QSpinBox, QColorDialog,
    QMessageBox, QFileDialog, QInputDialog, QDialog, QDialogButtonBox,
    QFormLayout, QToolTip, QMenu, QSplitter
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QKeySequence, QShortcut,
    QImage
)

from gel_labeler.core.plate import (
    PlateProject, WellData, STANDARD_PLATE_FORMATS, STANDARD_ROLE_COLORS,
    create_builtin_templates, load_user_plates, save_user_plates,
    export_plate_to_json, import_plate_from_json, make_well_id,
    row_index_to_letter
)


class CustomGridDialog(QDialog):
    """Dialog for defining custom row and column counts for non-standard multiwell plates."""

    def __init__(self, current_rows: int = 8, current_cols: int = 12, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Custom Plate Grid Dimensions")
        self.setFixedSize(300, 180)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #cfcfcf; }
            QLabel { color: #cfcfcf; font-size: 12px; }
            QSpinBox { background-color: #2b2b2b; color: #ffffff; border: 1px solid #444444; border-radius: 4px; padding: 4px; }
        """)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.row_spin = QSpinBox()
        self.row_spin.setRange(1, 26)
        self.row_spin.setValue(current_rows)
        form.addRow("Rows (1 – 26, A–Z):", self.row_spin)

        self.col_spin = QSpinBox()
        self.col_spin.setRange(1, 48)
        self.col_spin.setValue(current_cols)
        form.addRow("Columns (1 – 48):", self.col_spin)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_dimensions(self) -> Tuple[int, int]:
        return self.row_spin.value(), self.col_spin.value()


class PlateCanvas(QWidget):
    """High-performance custom-rendered multiwell plate canvas with rubberband selection."""

    selection_changed = pyqtSignal()

    def __init__(self, plate: PlateProject, parent=None):
        super().__init__(parent)
        self.plate = plate
        self.selected_well_ids: Set[str] = set()
        self.last_clicked_well: Optional[Tuple[int, int]] = None

        # Drag selection state
        self._is_dragging = False
        self._drag_start = QPointF()
        self._drag_end = QPointF()

        # Geometry caching
        self.left_margin = 40.0
        self.top_margin = 35.0
        self.cell_w = 50.0
        self.cell_h = 50.0

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(480, 360)

    def set_plate(self, plate: PlateProject):
        self.plate = plate
        self.selected_well_ids.clear()
        self.last_clicked_well = None
        self.selection_changed.emit()
        self.update()

    def select_all(self):
        self.selected_well_ids = set(self.plate.wells.keys())
        self.selection_changed.emit()
        self.update()

    def clear_selection(self):
        self.selected_well_ids.clear()
        self.selection_changed.emit()
        self.update()

    def select_row(self, row: int, toggle: bool = False):
        row_ids = {make_well_id(row, c) for c in range(self.plate.cols)}
        if toggle:
            if row_ids.issubset(self.selected_well_ids):
                self.selected_well_ids -= row_ids
            else:
                self.selected_well_ids |= row_ids
        else:
            self.selected_well_ids = row_ids
        self.selection_changed.emit()
        self.update()

    def select_col(self, col: int, toggle: bool = False):
        col_ids = {make_well_id(r, col) for r in range(self.plate.rows)}
        if toggle:
            if col_ids.issubset(self.selected_well_ids):
                self.selected_well_ids -= col_ids
            else:
                self.selected_well_ids |= col_ids
        else:
            self.selected_well_ids = col_ids
        self.selection_changed.emit()
        self.update()

    def _calc_layout(self):
        w = max(100.0, float(self.width()))
        h = max(100.0, float(self.height()))
        avail_w = w - self.left_margin - 15.0
        avail_h = h - self.top_margin - 15.0

        self.cell_w = max(18.0, avail_w / max(1, self.plate.cols))
        self.cell_h = max(18.0, avail_h / max(1, self.plate.rows))
        # Keep wells roughly square/circular
        cell_size = min(self.cell_w, self.cell_h)
        self.cell_w = cell_size
        self.cell_h = cell_size

    def _well_rect(self, r: int, c: int) -> QRectF:
        x = self.left_margin + c * self.cell_w
        y = self.top_margin + r * self.cell_h
        return QRectF(x, y, self.cell_w, self.cell_h)

    def _point_to_grid(self, pt: QPointF) -> Tuple[Optional[str], Optional[int]]:
        """Identifies if a point falls on row header ('row', r), col header ('col', c), all ('all', None), or well ('well', (r, c))."""
        x, y = pt.x(), pt.y()

        # Top-left all corner
        if x < self.left_margin and y < self.top_margin:
            return "all", None

        # Column headers across top
        if y < self.top_margin:
            c = int((x - self.left_margin) / self.cell_w)
            if 0 <= c < self.plate.cols:
                return "col", c
            return None, None

        # Row headers along left
        if x < self.left_margin:
            r = int((y - self.top_margin) / self.cell_h)
            if 0 <= r < self.plate.rows:
                return "row", r
            return None, None

        # Well area
        c = int((x - self.left_margin) / self.cell_w)
        r = int((y - self.top_margin) / self.cell_h)
        if 0 <= r < self.plate.rows and 0 <= c < self.plate.cols:
            return "well", (r, c)
        return None, None

    def paintEvent(self, event):
        self._calc_layout()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # 1. Background
        painter.fillRect(self.rect(), QColor("#141416"))

        # Plate container outline
        plate_rect = QRectF(
            self.left_margin - 4,
            self.top_margin - 4,
            self.plate.cols * self.cell_w + 8,
            self.plate.rows * self.cell_h + 8
        )
        painter.setPen(QPen(QColor("#2d3139"), 1.5))
        painter.setBrush(QColor("#1b1d22"))
        painter.drawRoundedRect(plate_rect, 8.0, 8.0)

        # 2. Top-Left Select All Corner
        corner_rect = QRectF(self.left_margin - 24, self.top_margin - 20, 20, 16)
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.setBrush(QColor("#222429"))
        painter.drawRoundedRect(corner_rect, 3.0, 3.0)
        painter.setPen(QColor("#888888"))
        f_corner = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(f_corner)
        painter.drawText(corner_rect, Qt.AlignmentFlag.AlignCenter, "⛶")

        # 3. Column Numbers (1, 2, 3...)
        header_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(header_font)
        for c in range(self.plate.cols):
            col_rect = QRectF(self.left_margin + c * self.cell_w, self.top_margin - 22, self.cell_w, 18)
            painter.setPen(QColor("#8e95a5"))
            painter.drawText(col_rect, Qt.AlignmentFlag.AlignCenter, str(c + 1))

        # 4. Row Letters (A, B, C...)
        for r in range(self.plate.rows):
            row_rect = QRectF(self.left_margin - 28, self.top_margin + r * self.cell_h, 24, self.cell_h)
            painter.setPen(QColor("#8e95a5"))
            painter.drawText(row_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, row_index_to_letter(r))

        # 5. Wells
        for r in range(self.plate.rows):
            for c in range(self.plate.cols):
                wid = make_well_id(r, c)
                w_rect = self._well_rect(r, c)
                is_selected = wid in self.selected_well_ids
                well_data = self.plate.get_well(r, c)

                self._draw_well(painter, w_rect, well_data, is_selected)

        # 6. Rubberband drag rectangle
        if self._is_dragging:
            drag_rect = QRectF(
                min(self._drag_start.x(), self._drag_end.x()),
                min(self._drag_start.y(), self._drag_end.y()),
                abs(self._drag_start.x() - self._drag_end.x()),
                abs(self._drag_start.y() - self._drag_end.y())
            )
            painter.setPen(QPen(QColor("#e29c3d"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(226, 156, 61, 40))
            painter.drawRect(drag_rect)

    def _draw_well(self, painter: QPainter, rect: QRectF, well: WellData, is_selected: bool):
        margin = max(2.0, rect.width() * 0.08)
        circle_rect = rect.adjusted(margin, margin, -margin, -margin)

        # Fill & Border
        has_data = not well.is_empty
        fill_color = QColor(well.color) if has_data else QColor("#22252a")

        if is_selected:
            # Golden amber glowing highlight
            painter.setPen(QPen(QColor("#e29c3d"), max(2.5, rect.width() * 0.08)))
        else:
            painter.setPen(QPen(QColor("#3a3e47"), 1.0))

        painter.setBrush(QBrush(fill_color))
        painter.drawEllipse(circle_rect)

        # Text inside well (if cell is big enough)
        d = circle_rect.width()
        if d >= 24.0:
            # 1. Subtle Well ID
            id_font_size = max(6, int(d * 0.20))
            painter.setFont(QFont("Segoe UI", id_font_size))
            id_rect = QRectF(circle_rect.x(), circle_rect.y() + d * 0.12, d, d * 0.3)
            painter.setPen(QColor(255, 255, 255, 140) if has_data else QColor(140, 140, 140, 90))
            painter.drawText(id_rect, Qt.AlignmentFlag.AlignCenter, well.well_id)

            # 2. Main Title
            if well.title:
                title_font_size = max(7, int(d * 0.23))
                painter.setFont(QFont("Segoe UI", title_font_size, QFont.Weight.Bold))
                title_rect = QRectF(circle_rect.x() + 2, circle_rect.y() + d * 0.42, d - 4, d * 0.45)
                painter.setPen(QColor("#ffffff"))
                # Truncate text if needed
                text = well.title
                if len(text) > 8 and d < 60:
                    text = text[:7] + "…"
                painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            target_type, target_val = self._point_to_grid(pos)

            ctrl_pressed = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            shift_pressed = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

            if target_type == "all":
                self.select_all()
                return
            elif target_type == "col":
                self.select_col(target_val, toggle=ctrl_pressed)
                return
            elif target_type == "row":
                self.select_row(target_val, toggle=ctrl_pressed)
                return
            elif target_type == "well":
                r, c = target_val
                wid = make_well_id(r, c)

                if shift_pressed and self.last_clicked_well:
                    # Bounding box range selection
                    r0, c0 = self.last_clicked_well
                    min_r, max_r = min(r0, r), max(r0, r)
                    min_c, max_c = min(c0, c), max(c0, c)
                    range_ids = {make_well_id(ri, ci) for ri in range(min_r, max_r + 1) for ci in range(min_c, max_c + 1)}
                    if ctrl_pressed:
                        self.selected_well_ids |= range_ids
                    else:
                        self.selected_well_ids = range_ids
                elif ctrl_pressed:
                    if wid in self.selected_well_ids:
                        self.selected_well_ids.remove(wid)
                    else:
                        self.selected_well_ids.add(wid)
                    self.last_clicked_well = (r, c)
                else:
                    self.selected_well_ids = {wid}
                    self.last_clicked_well = (r, c)

                self.selection_changed.emit()
                self.update()
                return

            # Clicked outside well/headers: start rubberband selection
            if not ctrl_pressed:
                self.selected_well_ids.clear()
                self.selection_changed.emit()
            self._is_dragging = True
            self._drag_start = pos
            self._drag_end = pos
            self.update()

        elif event.button() == Qt.MouseButton.RightButton:
            pos = event.position()
            target_type, target_val = self._point_to_grid(pos)
            if target_type == "well":
                r, c = target_val
                wid = make_well_id(r, c)
                if wid not in self.selected_well_ids:
                    self.selected_well_ids = {wid}
                    self.last_clicked_well = (r, c)
                    self.selection_changed.emit()
                    self.update()
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self._is_dragging:
            self._drag_end = pos
            self._update_rubberband_selection(bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier))
            self.update()
            return

        # Tooltip handling
        target_type, target_val = self._point_to_grid(pos)
        if target_type == "well":
            r, c = target_val
            well = self.plate.get_well(r, c)
            tip = f"<b>Well {well.well_id}</b>"
            if well.title:
                tip += f"<br/><b>Title:</b> {well.title}"
            if well.role and well.role != "Empty":
                tip += f"<br/><b>Role:</b> {well.role}"
            if well.concentration:
                tip += f"<br/><b>Conc:</b> {well.concentration}"
            if well.description:
                tip += f"<br/><b>Notes:</b> {well.description}"
            QToolTip.showText(event.globalPosition().toPoint(), tip, self)
        else:
            QToolTip.hideText()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False
            self.update()

    def _update_rubberband_selection(self, additive: bool):
        rect = QRectF(
            min(self._drag_start.x(), self._drag_end.x()),
            min(self._drag_start.y(), self._drag_end.y()),
            abs(self._drag_start.x() - self._drag_end.x()),
            abs(self._drag_start.y() - self._drag_end.y())
        )
        dragged_ids = set()
        for r in range(self.plate.rows):
            for c in range(self.plate.cols):
                w_rect = self._well_rect(r, c)
                if rect.intersects(w_rect):
                    dragged_ids.add(make_well_id(r, c))

        if additive:
            self.selected_well_ids |= dragged_ids
        else:
            self.selected_well_ids = dragged_ids
        self.selection_changed.emit()

    def _show_context_menu(self, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #202227; color: #cfcfcf; border: 1px solid #333333; padding: 4px; }
            QMenu::item:selected { background-color: #388bfd; color: #ffffff; }
        """)

        copy_act = menu.addAction("📋 Copy Selection")
        paste_act = menu.addAction("📋 Paste into Selection")
        menu.addSeparator()
        clear_act = menu.addAction("🗑️ Clear Selected Wells")
        menu.addSeparator()
        sel_all = menu.addAction("⛶ Select All")

        action = menu.exec(global_pos)
        parent_widget = self.parent()
        while parent_widget and not hasattr(parent_widget, "copy_selection"):
            parent_widget = parent_widget.parent()

        if parent_widget:
            if action == copy_act:
                parent_widget.copy_selection()
            elif action == paste_act:
                parent_widget.paste_selection()
            elif action == clear_act:
                parent_widget.clear_selected_wells()
            elif action == sel_all:
                self.select_all()


class WellInspectorPanel(QWidget):
    """Right-side inspector for viewing, styling, batch editing, and auto-numbering wells."""

    data_applied = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(310)
        self.selected_color = "#2563eb"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Header status
        self.status_lbl = QLabel("0 Wells Selected")
        self.status_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #e29c3d;")
        layout.addWidget(self.status_lbl)

        # Main Properties Box
        prop_group = QGroupBox("Well Attributes")
        form = QFormLayout(prop_group)
        form.setSpacing(10)

        # Title
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Sample Title (e.g. Sample A, Ctrl)")
        self.title_edit.setStyleSheet("background-color: #1a1c20; border: 1px solid #363a45; padding: 5px; color: #ffffff;")
        form.addRow("Title:", self.title_edit)

        # Role
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Sample", "Standard", "Control", "Blank", "Positive", "Negative", "Treated", "Empty"])
        self.role_combo.setStyleSheet("background-color: #1a1c20; border: 1px solid #363a45; padding: 4px; color: #ffffff;")
        self.role_combo.currentTextChanged.connect(self._on_role_changed)
        form.addRow("Role:", self.role_combo)

        # Concentration / Value
        self.conc_edit = QLineEdit()
        self.conc_edit.setPlaceholderText("e.g. 10 µM, 100 ng/µL, 1:50")
        self.conc_edit.setStyleSheet("background-color: #1a1c20; border: 1px solid #363a45; padding: 5px; color: #ffffff;")
        form.addRow("Conc / Value:", self.conc_edit)

        # Description / Notes
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Notes, cell line, treatment details...")
        self.desc_edit.setFixedHeight(65)
        self.desc_edit.setStyleSheet("background-color: #1a1c20; border: 1px solid #363a45; padding: 4px; color: #ffffff;")
        form.addRow("Notes:", self.desc_edit)

        # Color Palette Swatches
        color_vbox = QVBoxLayout()
        swatch_layout = QHBoxLayout()
        swatch_layout.setSpacing(6)

        self.swatch_buttons = []
        for role_name, hex_color in STANDARD_ROLE_COLORS.items():
            if role_name == "Empty":
                continue
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"{role_name} ({hex_color})")
            btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #555555; border-radius: 11px;")
            btn.clicked.connect(lambda checked, col=hex_color: self.set_color(col))
            swatch_layout.addWidget(btn)
            self.swatch_buttons.append(btn)

        self.custom_color_btn = QPushButton("🎨")
        self.custom_color_btn.setFixedSize(24, 22)
        self.custom_color_btn.setToolTip("Pick Custom Color...")
        self.custom_color_btn.clicked.connect(self.pick_custom_color)
        swatch_layout.addWidget(self.custom_color_btn)

        color_vbox.addLayout(swatch_layout)

        # Current color preview banner
        self.color_preview = QLabel("Active Color")
        self.color_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; color: #ffffff; font-size: 10px; font-weight: bold; border-radius: 3px; padding: 2px;")
        color_vbox.addWidget(self.color_preview)

        form.addRow("Color:", color_vbox)
        layout.addWidget(prop_group)

        # Apply Attributes Button
        self.apply_btn = QPushButton("✔️ Apply to Selected Wells")
        self.apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                font-weight: bold;
                border-radius: 4px;
                padding: 7px;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)
        self.apply_btn.clicked.connect(self.apply_attributes)
        layout.addWidget(self.apply_btn)

        # Auto-Series / Numbering Tool
        series_group = QGroupBox("Series / Auto-Numbering")
        series_layout = QVBoxLayout(series_group)
        series_layout.setSpacing(8)

        sf = QFormLayout()
        self.series_prefix = QLineEdit("Sample")
        self.series_prefix.setStyleSheet("background-color: #1a1c20; border: 1px solid #363a45; padding: 4px; color: #ffffff;")
        sf.addRow("Prefix:", self.series_prefix)

        self.series_start = QSpinBox()
        self.series_start.setRange(1, 9999)
        self.series_start.setValue(1)
        self.series_start.setStyleSheet("background-color: #1a1c20; border: 1px solid #363a45; padding: 4px; color: #ffffff;")
        sf.addRow("Start Num:", self.series_start)

        self.series_pad = QSpinBox()
        self.series_pad.setRange(0, 4)
        self.series_pad.setValue(0)
        self.series_pad.setToolTip("Zero pad width (e.g. 2 -> 01, 02)")
        self.series_pad.setStyleSheet("background-color: #1a1c20; border: 1px solid #363a45; padding: 4px; color: #ffffff;")
        sf.addRow("Zero Padding:", self.series_pad)

        series_layout.addLayout(sf)

        self.apply_series_btn = QPushButton("🔢 Number Selected Wells")
        self.apply_series_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_series_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        self.apply_series_btn.clicked.connect(self.apply_series)
        series_layout.addWidget(self.apply_series_btn)

        layout.addWidget(series_group)
        layout.addStretch()

    def set_color(self, hex_color: str):
        self.selected_color = hex_color
        self.color_preview.setStyleSheet(f"background-color: {hex_color}; color: #ffffff; font-size: 10px; font-weight: bold; border-radius: 3px; padding: 2px;")

    def pick_custom_color(self):
        col = QColorDialog.getColor(QColor(self.selected_color), self, "Select Well Color")
        if col.isValid():
            self.set_color(col.name())

    def _on_role_changed(self, role_name: str):
        if role_name in STANDARD_ROLE_COLORS:
            self.set_color(STANDARD_ROLE_COLORS[role_name])

    def update_from_selection(self, selected_wells: List[WellData]):
        n = len(selected_wells)
        if n == 0:
            self.status_lbl.setText("No Wells Selected")
            self.title_edit.clear()
            self.conc_edit.clear()
            self.desc_edit.clear()
            self.setEnabled(False)
        elif n == 1:
            w = selected_wells[0]
            self.status_lbl.setText(f"Well {w.well_id} Selected")
            self.title_edit.setText(w.title)
            self.role_combo.blockSignals(True)
            self.role_combo.setCurrentText(w.role if w.role in STANDARD_ROLE_COLORS else "Sample")
            self.role_combo.blockSignals(False)
            self.conc_edit.setText(w.concentration)
            self.desc_edit.setText(w.description)
            self.set_color(w.color if w.color else "#2563eb")
            self.setEnabled(True)
        else:
            self.status_lbl.setText(f"{n} Wells Selected")
            # If all titles are identical, show it, else clear
            titles = {w.title for w in selected_wells if w.title}
            self.title_edit.setText(titles.pop() if len(titles) == 1 else "")
            self.setEnabled(True)

    def apply_attributes(self):
        self.data_applied.emit()

    def apply_series(self):
        parent_widget = self.parent()
        while parent_widget and not hasattr(parent_widget, "apply_series_to_selection"):
            parent_widget = parent_widget.parent()
        if parent_widget:
            prefix = self.series_prefix.text().strip()
            start = self.series_start.value()
            pad = self.series_pad.value()
            parent_widget.apply_series_to_selection(prefix, start, pad, self.selected_color, self.role_combo.currentText())


class PlateWidget(QWidget):
    """Complete Multiwell Plate Designer application module."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plate = PlateProject(name="96-Well Plate Layout", rows=8, cols=12)
        self.user_plates = load_user_plates()
        self.builtin_templates = create_builtin_templates()
        self.clipboard_wells: List[WellData] = []

        self.init_ui()
        self._setup_shortcuts()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(12)

        # 1. Header Toolbar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        title_lbl = QLabel("▦ Multiwell Plate Designer & Labeler")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #e29c3d;")
        header_layout.addWidget(title_lbl)

        header_layout.addStretch()

        # Plate Format Dropdown
        fmt_lbl = QLabel("Format:")
        fmt_lbl.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        header_layout.addWidget(fmt_lbl)

        self.format_combo = QComboBox()
        self.format_combo.addItems(list(STANDARD_PLATE_FORMATS.keys()) + ["Custom..."])
        self.format_combo.setCurrentText("96-Well (8 × 12)")
        self.format_combo.setStyleSheet("background-color: #22252a; border: 1px solid #363a45; padding: 4px; color: #ffffff;")
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        header_layout.addWidget(self.format_combo)

        # Templates Dropdown
        tmpl_lbl = QLabel("Templates:")
        tmpl_lbl.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        header_layout.addWidget(tmpl_lbl)

        self.template_combo = QComboBox()
        self.template_combo.addItem("Load Built-in Template...")
        for name in self.builtin_templates.keys():
            self.template_combo.addItem(f"⭐ {name}")
        self.template_combo.setStyleSheet("background-color: #22252a; border: 1px solid #363a45; padding: 4px; color: #ffffff;")
        self.template_combo.currentIndexChanged.connect(self.on_template_selected)
        header_layout.addWidget(self.template_combo)

        # Save / User Presets
        self.save_btn = QPushButton("💾 Save Plate")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #233446;
                color: #58a6ff;
                border: 1px solid #388bfd;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #388bfd; color: #ffffff; }
        """)
        self.save_btn.clicked.connect(self.save_current_plate)
        header_layout.addWidget(self.save_btn)

        self.saved_plates_combo = QComboBox()
        self.saved_plates_combo.setFixedWidth(170)
        self.saved_plates_combo.setStyleSheet("background-color: #22252a; border: 1px solid #363a45; padding: 4px; color: #ffffff;")
        self.saved_plates_combo.currentIndexChanged.connect(self.on_saved_plate_selected)
        self.populate_saved_plates_combo()
        header_layout.addWidget(self.saved_plates_combo)

        self.del_plate_btn = QPushButton("🗑️")
        self.del_plate_btn.setToolTip("Delete selected custom plate")
        self.del_plate_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b2225;
                color: #f85149;
                border: 1px solid #da3633;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #da3633; color: #ffffff; }
        """)
        self.del_plate_btn.clicked.connect(self.delete_current_saved_plate)
        header_layout.addWidget(self.del_plate_btn)

        main_layout.addLayout(header_layout)

        # 2. Plate Name & Quick Actions Bar
        sub_bar = QHBoxLayout()
        name_lbl = QLabel("Plate Name:")
        name_lbl.setStyleSheet("color: #888888; font-weight: bold;")
        sub_bar.addWidget(name_lbl)

        self.plate_name_edit = QLineEdit(self.plate.name)
        self.plate_name_edit.setPlaceholderText("Plate Title (e.g. ELISA Plate 1)")
        self.plate_name_edit.setStyleSheet("background-color: #1a1c20; border: 1px solid #363a45; padding: 4px; color: #ffffff;")
        self.plate_name_edit.textChanged.connect(self._on_plate_name_changed)
        sub_bar.addWidget(self.plate_name_edit)

        sub_bar.addSpacing(10)

        # Clear All
        self.clear_all_btn = QPushButton("🗑️ Clear All")
        self.clear_all_btn.clicked.connect(self.clear_all_wells)
        sub_bar.addWidget(self.clear_all_btn)

        # Copy / Paste Buttons
        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.clicked.connect(self.copy_selection)
        sub_bar.addWidget(self.copy_btn)

        self.paste_btn = QPushButton("📋 Paste")
        self.paste_btn.clicked.connect(self.paste_selection)
        sub_bar.addWidget(self.paste_btn)

        # Import / Export JSON
        self.import_btn = QPushButton("📥 Import...")
        self.import_btn.clicked.connect(self.import_json)
        sub_bar.addWidget(self.import_btn)

        self.export_json_btn = QPushButton("📤 Export JSON...")
        self.export_json_btn.clicked.connect(self.export_json)
        sub_bar.addWidget(self.export_json_btn)

        # CSV Export
        self.export_csv_btn = QPushButton("📊 Export CSV...")
        self.export_csv_btn.clicked.connect(self.export_csv)
        sub_bar.addWidget(self.export_csv_btn)

        # Image Export
        self.export_img_btn = QPushButton("🖼️ Export Image...")
        self.export_img_btn.clicked.connect(self.export_image)
        sub_bar.addWidget(self.export_img_btn)

        main_layout.addLayout(sub_bar)

        # 3. Central Splitter: Canvas + Inspector
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #272a31; }")

        # Canvas inside scrollable or direct widget
        self.canvas = PlateCanvas(self.plate, self)
        self.canvas.selection_changed.connect(self.on_canvas_selection_changed)
        splitter.addWidget(self.canvas)

        # Inspector Panel
        self.inspector = WellInspectorPanel(self)
        self.inspector.data_applied.connect(self.apply_inspector_to_selection)
        splitter.addWidget(self.inspector)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter, stretch=1)

        # 4. Bottom Legend & Status Bar
        self.bottom_bar = QLabel("")
        self.bottom_bar.setStyleSheet("font-size: 11px; color: #8e95a5; padding-top: 4px;")
        main_layout.addWidget(self.bottom_bar)

        self.update_stats()
        self.inspector.update_from_selection([])

    def _setup_shortcuts(self):
        QShortcut(QKeySequence.StandardKey.Copy, self, self.copy_selection)
        QShortcut(QKeySequence.StandardKey.Paste, self, self.paste_selection)
        QShortcut(QKeySequence.StandardKey.SelectAll, self, self.canvas.select_all)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self, self.clear_selected_wells)
        QShortcut(QKeySequence(Qt.Key.Key_Backspace), self, self.clear_selected_wells)

    def _on_plate_name_changed(self, text: str):
        self.plate.name = text.strip() or "Untitled Plate"

    def on_format_changed(self, fmt_text: str):
        if fmt_text == "Custom...":
            dlg = CustomGridDialog(self.plate.rows, self.plate.cols, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                r, c = dlg.get_dimensions()
                self.plate.resize(r, c)
                self.canvas.set_plate(self.plate)
                self.update_stats()
            else:
                # Revert combo
                for name, dims in STANDARD_PLATE_FORMATS.items():
                    if dims == (self.plate.rows, self.plate.cols):
                        self.format_combo.blockSignals(True)
                        self.format_combo.setCurrentText(name)
                        self.format_combo.blockSignals(False)
                        break
        elif fmt_text in STANDARD_PLATE_FORMATS:
            r, c = STANDARD_PLATE_FORMATS[fmt_text]
            self.plate.resize(r, c)
            self.canvas.set_plate(self.plate)
            self.update_stats()

    def on_template_selected(self, index: int):
        if index <= 0:
            return
        text = self.template_combo.currentText().replace("⭐ ", "").strip()
        if text in self.builtin_templates:
            tmpl = self.builtin_templates[text]
            # Deep clone template
            self.plate = PlateProject.from_dict(tmpl.to_dict())
            self.plate_name_edit.setText(self.plate.name)
            self.canvas.set_plate(self.plate)

            # Match format combo
            self.format_combo.blockSignals(True)
            for name, dims in STANDARD_PLATE_FORMATS.items():
                if dims == (self.plate.rows, self.plate.cols):
                    self.format_combo.setCurrentText(name)
                    break
            self.format_combo.blockSignals(False)

            self.update_stats()
        self.template_combo.blockSignals(True)
        self.template_combo.setCurrentIndex(0)
        self.template_combo.blockSignals(False)

    def populate_saved_plates_combo(self):
        self.saved_plates_combo.blockSignals(True)
        self.saved_plates_combo.clear()
        self.saved_plates_combo.addItem("Saved Plates...")
        for name in sorted(self.user_plates.keys()):
            self.saved_plates_combo.addItem(f"👤 {name}")
        self.saved_plates_combo.blockSignals(False)

    def save_current_plate(self):
        default_name = self.plate.name or "My Plate Layout"
        name, ok = QInputDialog.getText(self, "Save Plate Layout", "Layout Name:", text=default_name)
        if not ok or not name.strip():
            return
        name = name.strip()
        self.plate.name = name
        self.plate_name_edit.setText(name)

        self.user_plates[name] = PlateProject.from_dict(self.plate.to_dict())
        if save_user_plates(self.user_plates):
            self.populate_saved_plates_combo()
            self.saved_plates_combo.setCurrentText(f"👤 {name}")
            QMessageBox.information(self, "Saved", f"Plate layout '{name}' saved to your AppData library!")
        else:
            QMessageBox.critical(self, "Error", "Failed to save plate layout.")

    def on_saved_plate_selected(self, index: int):
        if index <= 0:
            return
        text = self.saved_plates_combo.currentText().replace("👤 ", "").strip()
        if text in self.user_plates:
            self.plate = PlateProject.from_dict(self.user_plates[text].to_dict())
            self.plate_name_edit.setText(self.plate.name)
            self.canvas.set_plate(self.plate)

            # Update format combo
            self.format_combo.blockSignals(True)
            for name, dims in STANDARD_PLATE_FORMATS.items():
                if dims == (self.plate.rows, self.plate.cols):
                    self.format_combo.setCurrentText(name)
                    break
            self.format_combo.blockSignals(False)
            self.update_stats()

    def delete_current_saved_plate(self):
        text = self.saved_plates_combo.currentText()
        if not text.startswith("👤 "):
            QMessageBox.information(self, "Delete", "Please select a custom user plate to delete.")
            return
        name = text.replace("👤 ", "").strip()
        res = QMessageBox.question(self, "Delete Plate", f"Delete saved plate '{name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res == QMessageBox.StandardButton.Yes:
            if name in self.user_plates:
                del self.user_plates[name]
                save_user_plates(self.user_plates)
                self.populate_saved_plates_combo()

    def on_canvas_selection_changed(self):
        selected_wells = [self.plate.wells[wid] for wid in self.canvas.selected_well_ids if wid in self.plate.wells]
        # Sort in reading order (row, col)
        selected_wells.sort(key=lambda w: (w.row, w.col))
        self.inspector.update_from_selection(selected_wells)
        self.update_stats()

    def apply_inspector_to_selection(self):
        if not self.canvas.selected_well_ids:
            return
        title = self.inspector.title_edit.text().strip()
        role = self.inspector.role_combo.currentText()
        conc = self.inspector.conc_edit.text().strip()
        desc = self.inspector.desc_edit.toPlainText().strip()
        color = self.inspector.selected_color

        self.plate.apply_batch(
            list(self.canvas.selected_well_ids),
            title=title,
            description=desc,
            color=color,
            role=role,
            concentration=conc
        )
        self.canvas.update()
        self.update_stats()

    def apply_series_to_selection(self, prefix: str, start: int, pad: int, color: str, role: str):
        if not self.canvas.selected_well_ids:
            return
        sorted_ids = sorted(list(self.canvas.selected_well_ids), key=lambda wid: (self.plate.wells[wid].row, self.plate.wells[wid].col))
        self.plate.apply_series(sorted_ids, prefix=prefix, start_num=start, pad=pad, color=color, role=role)
        self.canvas.update()
        self.on_canvas_selection_changed()
        self.update_stats()

    def copy_selection(self):
        if not self.canvas.selected_well_ids:
            return
        sorted_ids = sorted(list(self.canvas.selected_well_ids), key=lambda wid: (self.plate.wells[wid].row, self.plate.wells[wid].col))
        self.clipboard_wells = [WellData.from_dict(self.plate.wells[wid].to_dict()) for wid in sorted_ids]

    def paste_selection(self):
        if not self.clipboard_wells or not self.canvas.selected_well_ids:
            return
        target_ids = sorted(list(self.canvas.selected_well_ids), key=lambda wid: (self.plate.wells[wid].row, self.plate.wells[wid].col))
        # Tile or repeat clipboard onto targets
        n_clip = len(self.clipboard_wells)
        for i, tid in enumerate(target_ids):
            src = self.clipboard_wells[i % n_clip]
            w = self.plate.wells[tid]
            w.title = src.title
            w.description = src.description
            w.color = src.color
            w.role = src.role
            w.concentration = src.concentration
        self.canvas.update()
        self.on_canvas_selection_changed()
        self.update_stats()

    def clear_selected_wells(self):
        if not self.canvas.selected_well_ids:
            return
        self.plate.clear_wells(list(self.canvas.selected_well_ids))
        self.canvas.update()
        self.on_canvas_selection_changed()
        self.update_stats()

    def clear_all_wells(self):
        res = QMessageBox.question(self, "Clear Plate", "Are you sure you want to clear all wells on this plate?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res == QMessageBox.StandardButton.Yes:
            self.plate.clear_all()
            self.canvas.update()
            self.on_canvas_selection_changed()
            self.update_stats()

    def update_stats(self):
        stats = self.plate.get_stats()
        total = stats.get("total", 0)
        filled = stats.get("filled", 0)
        sel = len(self.canvas.selected_well_ids)

        role_items = []
        for role, count in sorted(stats.items()):
            if role not in ("total", "filled", "empty") and count > 0:
                color = STANDARD_ROLE_COLORS.get(role, "#388bfd")
                role_items.append(f"<span style='color:{color}; font-weight:bold;'>● {role}: {count}</span>")

        legend_text = " &nbsp;|&nbsp; ".join(role_items)
        if legend_text:
            legend_text = " &nbsp;&nbsp;[ " + legend_text + " ]"

        self.bottom_bar.setText(
            f"<b>Dimensions:</b> {self.plate.rows} × {self.plate.cols} ({total} Wells) &nbsp;|&nbsp; "
            f"<b>Filled:</b> {filled}/{total} ({int(filled/max(1, total)*100)}%) &nbsp;|&nbsp; "
            f"<b>Selected:</b> {sel}{legend_text}"
        )

    def import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Plate Layout JSON", "", "JSON Files (*.json)")
        if not path:
            return
        loaded = import_plate_from_json(path)
        if loaded:
            self.plate = loaded
            self.plate_name_edit.setText(self.plate.name)
            self.canvas.set_plate(self.plate)
            self.format_combo.blockSignals(True)
            for name, dims in STANDARD_PLATE_FORMATS.items():
                if dims == (self.plate.rows, self.plate.cols):
                    self.format_combo.setCurrentText(name)
                    break
            self.format_combo.blockSignals(False)
            self.update_stats()
            QMessageBox.information(self, "Import Successful", f"Loaded plate layout '{self.plate.name}'!")
        else:
            QMessageBox.critical(self, "Import Error", "Failed to parse plate layout file.")

    def export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Plate Layout JSON", f"{self.plate.name}.plate.json", "JSON Files (*.json)")
        if not path:
            return
        if export_plate_to_json(self.plate, path):
            QMessageBox.information(self, "Export Successful", f"Exported plate layout to:\n{path}")
        else:
            QMessageBox.critical(self, "Export Error", "Failed to export plate layout to JSON.")

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Plate Layout to CSV", f"{self.plate.name}.csv", "CSV Files (*.csv)")
        if not path:
            return
        # Ask format preference
        msg = QMessageBox(self)
        msg.setWindowTitle("Choose CSV Format")
        msg.setText("Which CSV export format would you like?")
        btn_matrix = msg.addButton("Plate Grid Matrix", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Tabular Sample List", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() == btn_cancel:
            return

        try:
            if msg.clickedButton() == btn_matrix:
                csv_data = self.plate.export_matrix_csv()
            else:
                csv_data = self.plate.export_table_csv()
            with open(path, "w", encoding="utf-8") as f:
                f.write(csv_data)
            QMessageBox.information(self, "Export Complete", f"Plate layout exported to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV: {e}")

    def export_image(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export High-Res Plate Diagram", f"{self.plate.name}.png", "PNG Images (*.png)")
        if not path:
            return
        try:
            # Render high-resolution image
            scale = 2.0
            img_w = int(max(800, self.canvas.width()) * scale)
            img_h = int(max(600, self.canvas.height() + 80) * scale)
            image = QImage(img_w, img_h, QImage.Format.Format_ARGB32)
            image.fill(QColor("#141416"))

            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

            # Draw title banner
            painter.setPen(QColor("#e29c3d"))
            painter.setFont(QFont("Segoe UI", int(14 * scale), QFont.Weight.Bold))
            painter.drawText(QRectF(20 * scale, 12 * scale, img_w - 40 * scale, 30 * scale), Qt.AlignmentFlag.AlignLeft, self.plate.name)

            # Subtitle
            painter.setPen(QColor("#8e95a5"))
            painter.setFont(QFont("Segoe UI", int(9 * scale)))
            painter.drawText(QRectF(20 * scale, 38 * scale, img_w - 40 * scale, 20 * scale), Qt.AlignmentFlag.AlignLeft, f"Format: {self.plate.rows} × {self.plate.cols} ({self.plate.rows * self.plate.cols} Wells)")

            # Save canvas selection and clear temporarily for clean render
            orig_sel = set(self.canvas.selected_well_ids)
            self.canvas.selected_well_ids.clear()

            # Render canvas
            painter.save()
            painter.translate(0, 50 * scale)
            painter.scale(scale, scale)
            self.canvas.render(painter)
            painter.restore()

            self.canvas.selected_well_ids = orig_sel
            painter.end()

            image.save(path, "PNG")
            QMessageBox.information(self, "Export Complete", f"High-resolution plate image saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export image: {e}")
