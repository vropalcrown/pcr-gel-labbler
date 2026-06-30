# Configuration and Styles for Gel Electrophoresis Image Labeler

# Default configuration parameters
DEFAULT_FONT_FAMILY = "Arial"
DEFAULT_FONT_SIZE = 16  # Font size in pixels/points in the original image coordinate space
DEFAULT_COLOR = "#e29c3d"  # Blender Orange (Default)

# Predefined colors for labeling (high-contrast on dark backgrounds)
COLOR_PALETTE = [
    {"name": "Blender Orange", "value": "#e29c3d"},
    {"name": "Neon Green", "value": "#00FF00"},
    {"name": "Bright Red", "value": "#FF0055"},
    {"name": "Bright Blue", "value": "#00E5FF"},
    {"name": "Electric Yellow", "value": "#FFEA00"},
    {"name": "Vivid Pink", "value": "#FF00FF"},
    {"name": "Pure White", "value": "#FFFFFF"},
    {"name": "Pure Black", "value": "#000000"}
]


# Blender-like Dark Mode QSS Stylesheet
DARK_THEME_QSS = """
QMainWindow {
    background-color: #282828;
}

QWidget {
    color: #cfcfcf;
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    font-size: 11px;
}

/* Splitter styles */
QSplitter::handle {
    background-color: #151515;
}
QSplitter::handle:horizontal {
    width: 4px;
}
QSplitter::handle:vertical {
    height: 4px;
}

QMenuBar {
    background-color: #1e1e1e;
    border-bottom: 1px solid #151515;
}

QMenuBar::item {
    background-color: transparent;
    padding: 4px 10px;
}

QMenuBar::item:selected {
    background-color: #3b3b3b;
    color: #ffffff;
}

QMenu {
    background-color: #1e1e1e;
    border: 1px solid #151515;
    padding: 3px;
}

QMenu::item {
    padding: 4px 20px;
    border-radius: 2px;
}

QMenu::item:selected {
    background-color: #e29c3d;
    color: #151515;
    font-weight: bold;
}

QMenu::separator {
    height: 1px;
    background-color: #2d2d2d;
    margin: 4px 0px;
}

QToolBar {
    background-color: #1e1e1e;
    border-bottom: 1px solid #151515;
    spacing: 5px;
    padding: 3px;
}

QToolButton {
    background-color: #545454;
    border: 1px solid #2b2b2b;
    border-radius: 3px;
    padding: 4px 8px;
    font-weight: bold;
    color: #cfcfcf;
}

QToolButton:hover {
    background-color: #616161;
    border-color: #e29c3d;
}

QToolButton:pressed {
    background-color: #e29c3d;
    color: #151515;
}

QToolButton:checked {
    background-color: #e29c3d;
    color: #151515;
}

QGraphicsView {
    background-color: #151515;
    border: 1px solid #1a1a1a;
    border-radius: 3px;
}

QStatusBar {
    background-color: #1d1d1d;
    border-top: 1px solid #151515;
    color: #8a8a8a;
    font-size: 10px;
}

QLabel {
    color: #cfcfcf;
}

QDialog {
    background-color: #2e2e2e;
    border: 1px solid #151515;
    border-radius: 4px;
}

QPushButton {
    background-color: #545454;
    border: 1px solid #2b2b2b;
    border-radius: 3px;
    padding: 5px 12px;
    font-weight: bold;
    color: #cfcfcf;
}

QPushButton:hover {
    background-color: #616161;
    border-color: #e29c3d;
}

QPushButton:pressed {
    background-color: #e29c3d;
    color: #151515;
}

QPushButton#primaryBtn {
    background-color: #e29c3d;
    color: #151515;
    border: 1px solid #b87c2b;
}

QPushButton#primaryBtn:hover {
    background-color: #f29e38;
}

QLineEdit {
    background-color: #151515;
    border: 1px solid #2d2d2d;
    border-radius: 3px;
    padding: 4px 6px;
    color: #ffffff;
}

QLineEdit:focus {
    border-color: #e29c3d;
}

QComboBox {
    background-color: #545454;
    border: 1px solid #2b2b2b;
    border-radius: 3px;
    padding: 3px 6px;
    color: #cfcfcf;
}

QComboBox:hover {
    background-color: #616161;
    border-color: #e29c3d;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 15px;
    border-left-width: 0px;
}

QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    border: 1px solid #151515;
    selection-background-color: #e29c3d;
    selection-color: #151515;
    color: #cfcfcf;
}

QSpinBox, QDoubleSpinBox {
    background-color: #151515;
    border: 1px solid #2d2d2d;
    border-radius: 3px;
    padding: 3px 20px 3px 6px; /* 20px right-padding to clear spin arrows */
    color: #ffffff;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #e29c3d;
}

QSlider::groove:horizontal {
    border: 1px solid #151515;
    height: 4px;
    background: #1e1e1e;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #e29c3d;
    border: 1px solid #b87c2b;
    width: 10px;
    height: 10px;
    margin-top: -3px;
    margin-bottom: -3px;
    border-radius: 5px;
}

QSlider::handle:horizontal:hover {
    background: #f29e38;
}

QTableWidget {
    background-color: #1e1e1e;
    gridline-color: #2b2b2b;
    border: 1px solid #151515;
    color: #cfcfcf;
    selection-background-color: #e29c3d;
    selection-color: #151515;
}

QHeaderView::section {
    background-color: #2d2d2d;
    color: #cfcfcf;
    padding: 4px;
    border: 1px solid #151515;
    font-weight: bold;
}
"""
