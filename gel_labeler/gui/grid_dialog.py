from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QSlider, QSpinBox, 
                               QCheckBox, QWidget, QGridLayout, QComboBox, QFormLayout)
from PyQt6.QtCore import Qt

class GridOverlayDialog(QDialog):
    """Modeless dialog to configure and toggle a real-time visual reference grid overlay on the gel image."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Grid Overlay Settings")
        self.setModal(False)  # Modeless floating window
        self.resize(360, 320)
        
        # Color mapping preset list (Name -> Hex)
        self.color_presets = [
            ("Blender Orange", "#E29C3D"),
            ("Neon Green", "#00FF00"),
            ("Bright Red", "#FF0000"),
            ("Electric Cyan", "#00FFFF"),
            ("Pure White", "#FFFFFF"),
            ("Muted Gray", "#555555")
        ]
        
        self.init_ui()
        self.update_for_active_canvas()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Style QDialog matching the Blender dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #282828;
                color: #cfcfcf;
            }
            QLabel {
                color: #cfcfcf;
                font-size: 11px;
            }
            QCheckBox {
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
            }
            QSpinBox {
                background-color: #151515;
                border: 1px solid #2d2d2d;
                border-radius: 3px;
                padding: 3px 20px 3px 6px;
                color: #ffffff;
            }
            QComboBox {
                background-color: #1e1e1e;
                border: 1px solid #151515;
                border-radius: 3px;
                padding: 4px;
                color: #cfcfcf;
            }
            QPushButton {
                background-color: #545454;
                border: 1px solid #2b2b2b;
                border-radius: 3px;
                padding: 6px 16px;
                color: #cfcfcf;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #616161;
                border-color: #e29c3d;
            }
        """)
        
        # Enable grid checkbox
        self.enable_checkbox = QCheckBox("Show Visual Grid Overlay")
        self.enable_checkbox.stateChanged.connect(self.apply_grid_settings)
        main_layout.addWidget(self.enable_checkbox)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # 1. Color preset selector
        self.color_combo = QComboBox()
        for name, _ in self.color_presets:
            self.color_combo.addItem(name)
        self.color_combo.currentTextChanged.connect(self.apply_grid_settings)
        form_layout.addRow("Grid Color:", self.color_combo)
        
        # Helper to create slider + spinbox layout
        def create_slider_spin_pair(min_val, max_val, default_val):
            container = QWidget()
            hbox = QHBoxLayout(container)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.setSpacing(8)
            
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(default_val)
            
            spin = QSpinBox()
            spin.setRange(min_val, max_val)
            spin.setValue(default_val)
            spin.setFixedWidth(70)
            
            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(slider.setValue)
            
            hbox.addWidget(slider)
            hbox.addWidget(spin)
            return container, slider, spin
        
        # 2. X Spacing
        x_spacing_widget, self.x_spacing_slider, self.x_spacing_spin = create_slider_spin_pair(5, 500, 40)
        self.x_spacing_spin.valueChanged.connect(self.apply_grid_settings)
        form_layout.addRow("H Spacing (X px):", x_spacing_widget)
        
        # 3. Y Spacing
        y_spacing_widget, self.y_spacing_slider, self.y_spacing_spin = create_slider_spin_pair(5, 500, 40)
        self.y_spacing_spin.valueChanged.connect(self.apply_grid_settings)
        form_layout.addRow("V Spacing (Y px):", y_spacing_widget)
        
        # 4. X Offset
        x_offset_widget, self.x_offset_slider, self.x_offset_spin = create_slider_spin_pair(-500, 500, 0)
        self.x_offset_spin.valueChanged.connect(self.apply_grid_settings)
        form_layout.addRow("X Offset (px):", x_offset_widget)
        
        # 5. Y Offset
        y_offset_widget, self.y_offset_slider, self.y_offset_spin = create_slider_spin_pair(-500, 500, 0)
        self.y_offset_spin.valueChanged.connect(self.apply_grid_settings)
        form_layout.addRow("Y Offset (px):", y_offset_widget)
        
        main_layout.addLayout(form_layout)
        
        # Bottom close button
        btn_hbox = QHBoxLayout()
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        btn_hbox.addStretch()
        btn_hbox.addWidget(self.close_btn)
        main_layout.addLayout(btn_hbox)

    def block_all_signals(self, block: bool):
        """Helper to block/unblock signals on all widgets to prevent feedback loops."""
        self.enable_checkbox.blockSignals(block)
        self.color_combo.blockSignals(block)
        self.x_spacing_spin.blockSignals(block)
        self.x_spacing_slider.blockSignals(block)
        self.y_spacing_spin.blockSignals(block)
        self.y_spacing_slider.blockSignals(block)
        self.x_offset_spin.blockSignals(block)
        self.x_offset_slider.blockSignals(block)
        self.y_offset_spin.blockSignals(block)
        self.y_offset_slider.blockSignals(block)

    def get_selected_color_hex(self) -> str:
        name = self.color_combo.currentText()
        for preset_name, hex_val in self.color_presets:
            if preset_name == name:
                return hex_val
        return "#E29C3D"

    def set_color_combo_to_hex(self, hex_val: str):
        for name, preset_hex in self.color_presets:
            if preset_hex.upper() == hex_val.upper():
                self.color_combo.setCurrentText(name)
                break

    def apply_grid_settings(self):
        """Applies the current widget settings to the active tab's canvas."""
        parent = self.parent()
        if not parent or not hasattr(parent, 'active_tab') or not parent.active_tab:
            return
            
        tab = parent.active_tab
        if tab and tab.canvas:
            canvas = tab.canvas
            canvas.grid_enabled = self.enable_checkbox.isChecked()
            canvas.grid_x_spacing = float(self.x_spacing_spin.value())
            canvas.grid_y_spacing = float(self.y_spacing_spin.value())
            canvas.grid_x_offset = float(self.x_offset_spin.value())
            canvas.grid_y_offset = float(self.y_offset_spin.value())
            canvas.grid_color = self.get_selected_color_hex()
            canvas.viewport().update()

    def update_for_active_canvas(self):
        """Updates the dialog's controls to reflect the active tab's canvas grid settings."""
        parent = self.parent()
        if not parent or not hasattr(parent, 'active_tab') or not parent.active_tab:
            return
            
        tab = parent.active_tab
        if not tab or not tab.canvas:
            return
            
        canvas = tab.canvas
        self.block_all_signals(True)
        
        self.enable_checkbox.setChecked(canvas.grid_enabled)
        self.x_spacing_spin.setValue(int(canvas.grid_x_spacing))
        self.x_spacing_slider.setValue(int(canvas.grid_x_spacing))
        self.y_spacing_spin.setValue(int(canvas.grid_y_spacing))
        self.y_spacing_slider.setValue(int(canvas.grid_y_spacing))
        self.x_offset_spin.setValue(int(canvas.grid_x_offset))
        self.x_offset_slider.setValue(int(canvas.grid_x_offset))
        self.y_offset_spin.setValue(int(canvas.grid_y_offset))
        self.y_offset_slider.setValue(int(canvas.grid_y_offset))
        self.set_color_combo_to_hex(canvas.grid_color)
        
        self.block_all_signals(False)
