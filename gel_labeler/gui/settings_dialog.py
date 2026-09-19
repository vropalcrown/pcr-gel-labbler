from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QSlider, QSpinBox, 
                               QGridLayout, QWidget, QComboBox)
from PyQt6.QtCore import Qt
from gel_labeler.config import COLOR_PALETTE, DEFAULT_FONT_SIZE, DEFAULT_COLOR

class SettingsDialog(QDialog):
    """A dialog to input label text and configure its styling (color, font size)."""
    
    def __init__(self, parent=None, initial_text: str = "", 
                 initial_color: str = DEFAULT_COLOR, 
                 initial_font_size: int = DEFAULT_FONT_SIZE,
                 initial_rotation: float = 0.0):
        super().__init__(parent)
        self.setWindowTitle("Label Settings")
        self.setModal(True)
        self.resize(320, 340)  # Expanded height slightly to fit rotation input
        
        self.selected_color = initial_color
        try:
            sz = int(round(float(initial_font_size)))
        except (ValueError, TypeError):
            sz = DEFAULT_FONT_SIZE
        self.selected_font_size = max(8, min(72, sz))
        self.selected_rotation = initial_rotation
        self.color_buttons = []
        
        self.init_ui(initial_text)

    def init_ui(self, initial_text: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Label Text Input
        text_label = QLabel("Label Text:")
        text_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(text_label)
        
        self.text_input = QLineEdit()
        self.text_input.setText(initial_text)
        self.text_input.setPlaceholderText("e.g. Lane 1, Ladder, Control")
        layout.addWidget(self.text_input)
        
        # Color Selector Grid
        color_label = QLabel("🎨")
        color_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(color_label)
        
        color_widget = QWidget()
        color_grid = QGridLayout(color_widget)
        color_grid.setContentsMargins(0, 0, 0, 0)
        color_grid.setSpacing(8)
        
        # Create small square buttons for each color in the palette
        for i, col_data in enumerate(COLOR_PALETTE):
            btn = QPushButton()
            btn.setFixedSize(36, 36)
            color_hex = col_data["value"]
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color_hex};
                    border: 2px solid transparent;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border-color: #FFFFFF;
                }}
            """)
            btn.setToolTip(col_data["name"])
            
            # Highlight currently selected color button
            if color_hex.upper() == self.selected_color.upper():
                btn.setStyleSheet(btn.styleSheet() + "border-color: #FFFFFF; border-width: 3px;")
            
            # Connect using closure or default argument to capture current color_hex
            btn.clicked.connect(lambda checked, c=color_hex, b=btn: self.select_color(c, b))
            
            row, col = divmod(i, 3)
            color_grid.addWidget(btn, row, col)
            self.color_buttons.append((color_hex, btn))
            
        layout.addWidget(color_widget)
        
        # Font Size Controls
        font_label = QLabel("Font Size (px):")
        font_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(font_label)
        
        font_hbox = QHBoxLayout()
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(8, 72)
        self.size_slider.setValue(self.selected_font_size)
        
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 72)
        self.size_spin.setValue(self.selected_font_size)
        self.size_spin.setFixedWidth(55)
        
        # Sync slider and spinbox
        self.size_slider.valueChanged.connect(self.size_spin.setValue)
        self.size_spin.valueChanged.connect(self.size_slider.setValue)
        self.size_slider.valueChanged.connect(self.update_font_size)
        
        font_hbox.addWidget(self.size_slider)
        font_hbox.addWidget(self.size_spin)
        layout.addLayout(font_hbox)
        
        # Rotation Control
        rot_label = QLabel("Text Rotation:")
        rot_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(rot_label)
        
        self.rot_combo = QComboBox()
        self.rot_combo.addItems([
            "0° (Horizontal)",
            "90° (Vertical Down)",
            "270° (Vertical Up)",
            "45° (Slanted)"
        ])
        
        # Sync index with initial value
        if abs(self.selected_rotation - 90.0) < 1.0:
            self.rot_combo.setCurrentIndex(1)
        elif abs(self.selected_rotation - 270.0) < 1.0 or abs(self.selected_rotation + 90.0) < 1.0:
            self.rot_combo.setCurrentIndex(2)
        elif abs(self.selected_rotation - 45.0) < 1.0:
            self.rot_combo.setCurrentIndex(3)
        else:
            self.rot_combo.setCurrentIndex(0)
            
        layout.addWidget(self.rot_combo)
        
        # Dialog Action Buttons
        btn_hbox = QHBoxLayout()
        btn_hbox.setSpacing(12)
        
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("✔️ Apply")
        self.save_btn.setObjectName("primaryBtn")  # Styled with green accent in QSS
        self.save_btn.clicked.connect(self.accept)
        
        btn_hbox.addWidget(self.cancel_btn)
        btn_hbox.addWidget(self.save_btn)
        layout.addLayout(btn_hbox)
        
        # Focus on text input by default
        self.text_input.setFocus()
        self.text_input.selectAll()

    def select_color(self, color_hex: str, selected_btn: QPushButton):
        """Sets the selected color and highlights the active button."""
        self.selected_color = color_hex
        
        # Reset borders of all color buttons
        for hex_val, btn in self.color_buttons:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_val};
                    border: 2px solid transparent;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border-color: #FFFFFF;
                }}
            """)
            if hex_val.upper() == color_hex.upper():
                btn.setStyleSheet(btn.styleSheet() + "border-color: #FFFFFF; border-width: 3px;")

    def update_font_size(self, size: int):
        self.selected_font_size = size

    def get_selected_rotation(self) -> float:
        """Translates combo box selections into degrees rotation."""
        idx = self.rot_combo.currentIndex()
        if idx == 1:
            return 90.0
        elif idx == 2:
            return 270.0
        elif idx == 3:
            return 45.0
        return 0.0

    def get_values(self):
        """Returns the configured text, color, font size, and rotation."""
        return (
            self.text_input.text().strip(), 
            self.selected_color, 
            self.size_spin.value(), 
            self.get_selected_rotation()
        )
