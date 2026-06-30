import sys
import os

# Ensure the parent directory is in the python path to support modular imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PyQt6.QtWidgets import QApplication
from gel_labeler.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Set app-wide metadata
    app.setApplicationName("Gel Electrophoresis Image Labeler")
    app.setOrganizationName("Bioinformatics Tools")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()


