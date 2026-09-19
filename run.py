import sys
import os
import logging
import tempfile
import threading
import traceback

# Ensure the parent directory is in the python path to support modular imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PyQt6.QtCore import QStandardPaths
from PyQt6.QtWidgets import QApplication, QMessageBox
from gel_labeler.gui.main_window import MainWindow

logger = logging.getLogger("gel_labeler")


def get_app_data_dir() -> str:
    """Returns the writable AppData directory path for Gel Labeler."""
    app_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not app_dir:
        app_dir = os.path.join(tempfile.gettempdir(), "GelLabeler")
    try:
        os.makedirs(app_dir, exist_ok=True)
    except Exception:
        app_dir = tempfile.gettempdir()
    return app_dir


def setup_logging():
    """Sets up root and application logging to console and log file."""
    app_dir = get_app_data_dir()
    log_file = os.path.join(app_dir, "gel_labeler.log")
    
    logger.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(filename)s:%(lineno)d] %(message)s"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not initialize file logging to {log_file}: {e}")
        
    logger.info("Gel Labeler logger initialized.")


def setup_exception_hooks():
    """Installs sys.excepthook and threading.excepthook to log uncaught errors and prevent hard crashes."""
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.critical(f"Uncaught exception:\n{err_msg}")
        
        # Show message dialog if QApplication exists and is not exiting
        app = QApplication.instance()
        if app:
            try:
                log_dir = get_app_data_dir()
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("An Unexpected Error Occurred")
                msg_box.setText(f"Gel Labeler encountered an unexpected error:\n\n{exc_type.__name__}: {exc_value}")
                msg_box.setInformativeText(f"Logs have been saved to:\n{log_dir}\n\nYou can continue working or save your work and restart.")
                msg_box.setDetailedText(err_msg)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()
            except Exception as dialog_err:
                logger.error(f"Failed to display exception dialog: {dialog_err}")

    sys.excepthook = handle_exception
    
    def handle_thread_exception(args):
        handle_exception(args.exc_type, args.exc_value, args.exc_traceback)
        
    threading.excepthook = handle_thread_exception


def main():
    app = QApplication(sys.argv)
    
    # Set app-wide metadata
    app.setApplicationName("Gel Labeler")
    app.setOrganizationName("Bioinformatics Tools")
    
    setup_logging()
    setup_exception_hooks()
    
    window = MainWindow()
    window.show()
    window.raise_()
    window.activateWindow()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
