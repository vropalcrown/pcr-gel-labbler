from PyQt6.QtWidgets import QWidget, QVBoxLayout

from gel_labeler.core.project import GelProject
from gel_labeler.gui.canvas import GelCanvas
from gel_labeler.config import DEFAULT_COLOR

class GelTabWidget(QWidget):
    """Container widget representing a single Gel Project Tab workspace."""
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        
        # Unique instances for this tab
        self.project = GelProject()
        self.canvas = GelCanvas(self.project, self)
        
        # Connect canvas signals
        self.canvas.on_project_modified = main_window.handle_project_modified
        self.canvas.on_status_message = main_window.show_status_message
        
        # Tab-specific defaults
        self.default_label_color = DEFAULT_COLOR
        self.default_label_size = 14
        self.default_label_rotation = 0.0
        self.default_label_font_family = "Arial"
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
