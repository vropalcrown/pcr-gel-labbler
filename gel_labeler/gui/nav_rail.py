"""
Sleek, modern Navigation Rail for switching between applications in the Molecular Biology Suite.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QButtonGroup
from PyQt6.QtCore import pyqtSignal, Qt


class NavButton(QPushButton):
    """Custom navigation rail button with icon and label."""

    def __init__(self, icon_str: str, label_str: str, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(76, 68)
        self.setText(f"{icon_str}\n{label_str}")
        self.setToolTip(label_str)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            NavButton {
                background-color: transparent;
                border: none;
                border-left: 3px solid transparent;
                color: #8e8e8e;
                font-size: 11px;
                font-weight: bold;
                text-align: center;
                padding: 6px 2px;
            }
            NavButton:hover {
                background-color: #262626;
                color: #ffffff;
            }
            NavButton:checked {
                background-color: #2b2824;
                border-left: 3px solid #e29c3d;
                color: #e29c3d;
            }
        """)


class SuiteNavRail(QWidget):
    """Left navigation rail sidebar for switching suite applications."""

    page_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(80)
        self.setStyleSheet("background-color: #171717; border-right: 1px solid #282828;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(8)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        # 1. Gel Labeler
        self.btn_gel = NavButton("🧬", "Gel Labeler")
        self.btn_group.addButton(self.btn_gel, 0)
        layout.addWidget(self.btn_gel)

        # 2. Master Mixer
        self.btn_mm = NavButton("🧪", "Master Mix")
        self.btn_group.addButton(self.btn_mm, 1)
        layout.addWidget(self.btn_mm)

        # 3. Protocols
        self.btn_proto = NavButton("📋", "Protocols")
        self.btn_group.addButton(self.btn_proto, 2)
        layout.addWidget(self.btn_proto)

        # 4. Colony Counter
        self.btn_colony = NavButton("🧫", "Colonies")
        self.btn_group.addButton(self.btn_colony, 3)
        layout.addWidget(self.btn_colony)

        # 5. Multiwell Plate Designer & Labeler
        self.btn_plate = NavButton("▦", "Plates")
        self.btn_group.addButton(self.btn_plate, 4)
        layout.addWidget(self.btn_plate)

        layout.addStretch()

        self.btn_group.idClicked.connect(self.page_changed.emit)
        self.btn_gel.setChecked(True)

    def set_active_page(self, page_index: int):
        btn = self.btn_group.button(page_index)
        if btn:
            btn.setChecked(True)
