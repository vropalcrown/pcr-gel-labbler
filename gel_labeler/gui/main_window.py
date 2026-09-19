import os
import json
import logging
import tempfile
from typing import Optional
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                             QFileDialog, QMessageBox, QLabel,
                             QTabWidget, QDialog, QListWidget, QListWidgetItem,
                             QPushButton, QCheckBox, QLineEdit)
from PyQt6.QtCore import Qt, QTimer, QSize, QStandardPaths
from PyQt6.QtGui import QAction, QImage, QPainter, QIcon

logger = logging.getLogger("gel_labeler")

from gel_labeler.config import DARK_THEME_QSS, DEFAULT_COLOR
from gel_labeler.core.project import GelProject
from gel_labeler.gui.canvas import GelCanvas
from gel_labeler.gui.grid_dialog import GridOverlayDialog
from gel_labeler.gui.tab_widget import GelTabWidget

class PptxTabItemWidget(QWidget):
    """Custom widget for a tab item in the PowerPoint export dialog containing a checkbox, tab name, and custom title input."""
    
    def __init__(self, tab_name: str, details: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        
        self.name_label = QLabel(f"{tab_name}{details}")
        self.name_label.setStyleSheet("color: #cfcfcf; font-size: 12px;")
        
        layout.addWidget(self.checkbox)
        layout.addWidget(self.name_label)
        layout.addStretch()
        
        title_label = QLabel("Title:")
        title_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(title_label)
        
        self.title_edit = QLineEdit(tab_name)
        self.title_edit.setPlaceholderText("Slide Title...")
        self.title_edit.setFixedWidth(160)
        self.title_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 3px;
                color: #cfcfcf;
                padding: 2px 6px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #e29c3d;
            }
            QLineEdit:disabled {
                background-color: #121212;
                color: #555555;
            }
        """)
        self.checkbox.toggled.connect(self.title_edit.setEnabled)
        
        layout.addWidget(self.title_edit)


class PptxExportDialog(QDialog):
    """Dialog to custom select which gel tabs to export to a single PowerPoint file, including custom slide titles."""
    
    def __init__(self, tab_widget: QTabWidget, parent=None):
        super().__init__(parent)
        self.tab_widget = tab_widget
        self.setWindowTitle("Export PowerPoint Slide Deck")
        self.resize(520, 480)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        info = QLabel("Select the Gel Tabs to compile and customize their slide headers:")
        info.setWordWrap(True)
        info.setStyleSheet("color: #cfcfcf; font-size: 12px; font-weight: bold;")
        layout.addWidget(info)
        
        # List widget with checkable items
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #151515;
                border: 1px solid #2b2b2b;
                border-radius: 4px;
                color: #cfcfcf;
                padding: 4px;
            }
            QListWidget::item {
                padding: 2px;
                border-bottom: 1px solid #1e1e1e;
            }
            QListWidget::item:hover {
                background-color: #282828;
            }
        """)
        
        # Populate list widget
        for idx in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(idx)
            tab_name = self.tab_widget.tabText(idx).replace("📁 ", "")
            
            # Show image size or "(Empty Tab)"
            if tab.project.image_path:
                details = f" ({tab.project.image_width}x{tab.project.image_height} px)"
            else:
                details = " (Empty)"
                
            item = QListWidgetItem()
            item.setSizeHint(QSize(450, 36))
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.list_widget.addItem(item)
            
            widget = PptxTabItemWidget(tab_name, details, self)
            self.list_widget.setItemWidget(item, widget)
            
        layout.addWidget(self.list_widget)
        
        # Selection helper buttons
        sel_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all)
        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        
        sel_layout.addWidget(self.select_all_btn)
        sel_layout.addWidget(self.deselect_all_btn)
        sel_layout.addStretch()
        layout.addLayout(sel_layout)
        
        # Append to existing PowerPoint options group
        self.append_checkbox = QCheckBox("Append to existing PowerPoint presentation")
        self.append_checkbox.setStyleSheet("""
            QCheckBox {
                color: #cfcfcf;
                font-size: 12px;
                font-weight: bold;
                margin-top: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #151515;
                border: 1px solid #2b2b2b;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #e29c3d;
                border: 1px solid #e29c3d;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #e29c3d;
            }
        """)
        self.append_checkbox.toggled.connect(self.toggle_append_mode)
        layout.addWidget(self.append_checkbox)

        # Append path layout
        self.append_path_layout = QHBoxLayout()
        self.append_path_edit = QLineEdit()
        self.append_path_edit.setPlaceholderText("Select existing PowerPoint file...")
        self.append_path_edit.setReadOnly(True)
        self.append_path_edit.setEnabled(False)
        self.append_path_edit.setStyleSheet("""
            QLineEdit {
                background-color: #151515;
                border: 1px solid #2b2b2b;
                border-radius: 4px;
                color: #cfcfcf;
                padding: 4px;
            }
            QLineEdit:disabled {
                background-color: #1e1e1e;
                color: #777777;
            }
        """)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setEnabled(False)
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                color: #cfcfcf;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #383838;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                border: 1px solid #222222;
                color: #777777;
            }
        """)
        self.browse_btn.clicked.connect(self.browse_existing_pptx)
        
        self.append_path_layout.addWidget(self.append_path_edit)
        self.append_path_layout.addWidget(self.browse_btn)
        layout.addLayout(self.append_path_layout)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.export_btn = QPushButton("⚡ Export")
        self.export_btn.setObjectName("primaryBtn")
        self.export_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)
        
    def select_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                widget.checkbox.setChecked(True)
            
    def deselect_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                widget.checkbox.setChecked(False)
            
    def get_selected_tab_indices_and_titles(self) -> list:
        results = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget and widget.checkbox.isChecked():
                idx = item.data(Qt.ItemDataRole.UserRole)
                title = widget.title_edit.text().strip()
                results.append((idx, title))
        return results

    def toggle_append_mode(self, checked: bool):
        self.append_path_edit.setEnabled(checked)
        self.browse_btn.setEnabled(checked)

    def browse_existing_pptx(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Existing PowerPoint Presentation",
            "",
            "PowerPoint Files (*.pptx)"
        )
        if file_path:
            self.append_path_edit.setText(file_path)

    def get_existing_pptx_path(self) -> Optional[str]:
        if self.append_checkbox.isChecked():
            path = self.append_path_edit.text().strip()
            return path if path else None
        return None

    def accept(self):
        if self.append_checkbox.isChecked() and not self.append_path_edit.text().strip():
            QMessageBox.warning(self, "Missing File Path", "Please select an existing PowerPoint file to append to, or uncheck the append option.")
            return
        if self.append_checkbox.isChecked() and not os.path.exists(self.append_path_edit.text().strip()):
            QMessageBox.warning(self, "File Not Found", "The specified PowerPoint file does not exist. Please select a valid file.")
            return
        super().accept()


class MainWindow(QMainWindow):
    """Main application window for the Gel Electrophoresis Image Labeler."""
    
    @property
    def active_tab(self) -> Optional[GelTabWidget]:
        if hasattr(self, 'tab_widget'):
            return self.tab_widget.currentWidget()
        return None

    @property
    def project(self) -> Optional[GelProject]:
        tab = self.active_tab
        return tab.project if tab else None

    @property
    def canvas(self) -> Optional[GelCanvas]:
        tab = self.active_tab
        return tab.canvas if tab else None

    @property
    def profile_panel(self) -> Optional[QWidget]:
        tab = self.active_tab
        return tab.profile_panel if tab else None
        
    @property
    def default_label_color(self) -> str:
        tab = self.active_tab
        return tab.default_label_color if tab else self._default_label_color
        
    @default_label_color.setter
    def default_label_color(self, val: str):
        self._default_label_color = val
        tab = self.active_tab
        if tab:
            tab.default_label_color = val
            
    @property
    def default_label_size(self) -> int:
        tab = self.active_tab
        return tab.default_label_size if tab else self._default_label_size
        
    @default_label_size.setter
    def default_label_size(self, val: int):
        self._default_label_size = val
        tab = self.active_tab
        if tab:
            tab.default_label_size = val
            
    @property
    def default_label_rotation(self) -> float:
        tab = self.active_tab
        return tab.default_label_rotation if tab else self._default_label_rotation
        
    @default_label_rotation.setter
    def default_label_rotation(self, val: float):
        self._default_label_rotation = val
        tab = self.active_tab
        if tab:
            tab.default_label_rotation = val

    @property
    def default_label_font_family(self) -> str:
        tab = self.active_tab
        return tab.default_label_font_family if tab else self._default_label_font_family
        
    @default_label_font_family.setter
    def default_label_font_family(self, val: str):
        self._default_label_font_family = val
        tab = self.active_tab
        if tab:
            tab.default_label_font_family = val

    def __init__(self):
        super().__init__()
        
        # Default fallback styling variables
        self._default_label_color = DEFAULT_COLOR
        self._default_label_size = 14
        self._default_label_rotation = 0.0
        self._default_label_font_family = "Arial"
        
        # Clipboard for copying and pasting labels across tabs
        self.clipboard_labels = []
        
        self.setWindowTitle("Gel Labeler")
        self.resize(1024, 768)
        
        # Set window icon
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
            
        # Apply premium dark theme
        self.setStyleSheet(DARK_THEME_QSS)
        
        # Initialize the QTabWidget first
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.handle_tab_changed)
        self.tab_widget.tabBarDoubleClicked.connect(self.rename_tab_dialog)
        
        # Setup background auto-save timer running every 2 minutes (120,000 ms)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(2 * 60 * 1000)
        self.autosave_timer.timeout.connect(self.trigger_autosave)
        self.autosave_timer.start()
        
        # Check and recover session after window is initialized
        QTimer.singleShot(100, self.check_and_recover_session)
        
        # Style QTabWidget with Blender QSS
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #151515;
                background-color: #282828;
            }
            QTabBar::tab {
                background-color: #1e1e1e;
                color: #cfcfcf;
                border: 1px solid #151515;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                min-width: 85px;
            }
            QTabBar::tab:selected {
                background-color: #282828;
                border-color: #151515;
                color: #e29c3d; /* Blender Orange */
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #333333;
                color: #ffffff;
            }
        """)
        
        # Create core UI parts
        self.init_ui()
        self.create_menus()
        self.create_toolbars()
        
        # Add the first default empty tab
        self.add_new_tab("Gel 1")
        
        self.update_window_title()

    def init_ui(self):
        """Initializes the central widget and layout."""
        self.setCentralWidget(self.tab_widget)
        
        # Set up Status Bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready. Load an image to start labeling.")
        
        # Coordinate display in status bar
        self.coord_label = QLabel("")
        self.status_bar.addPermanentWidget(self.coord_label)

    def create_menus(self):
        """Creates the menu bar items."""
        menubar = self.menuBar()
        
        # --- File Menu ---
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Gel Image...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_image_dialog)
        file_menu.addAction(open_action)
        
        open_folder_action = QAction("Open Folder of Gel Images...", self)
        open_folder_action.setShortcut("Ctrl+Shift+O")
        open_folder_action.triggered.connect(self.open_folder_dialog)
        file_menu.addAction(open_folder_action)
        
        new_tab_action = QAction("New Tab", self)
        new_tab_action.setShortcut("Ctrl+T")
        new_tab_action.triggered.connect(lambda: self.add_new_tab())
        file_menu.addAction(new_tab_action)
        
        save_img_action = QAction("Export Labeled Image...", self)
        save_img_action.setShortcut("Ctrl+E")
        save_img_action.triggered.connect(self.export_image_dialog)
        file_menu.addAction(save_img_action)
        
        file_menu.addSeparator()
        
        save_json_action = QAction("Save Label Data (JSON)...", self)
        save_json_action.setShortcut("Ctrl+S")
        save_json_action.triggered.connect(self.save_json_dialog)
        file_menu.addAction(save_json_action)
        
        load_json_action = QAction("Load Label Data (JSON)...", self)
        load_json_action.setShortcut("Ctrl+L")
        load_json_action.triggered.connect(self.load_json_dialog)
        file_menu.addAction(load_json_action)
        
        export_csv_action = QAction("Export Label Data (CSV)...", self)
        export_csv_action.triggered.connect(self.export_csv_dialog)
        file_menu.addAction(export_csv_action)
        
        export_pptx_action = QAction("Export to PowerPoint (PPTX)...", self)
        export_pptx_action.triggered.connect(self.export_pptx_dialog)
        file_menu.addAction(export_pptx_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # --- Edit Menu ---
        edit_menu = menubar.addMenu("Edit")
        
        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo_action_trigger)
        edit_menu.addAction(undo_action)
        
        
        align_action = QAction("Align Image (2-Click)...", self)
        align_action.triggered.connect(self.trigger_align_mode)
        edit_menu.addAction(align_action)
        
        rotate_action = QAction("Rotate Image (Manual)...", self)
        rotate_action.triggered.connect(self.open_manual_rotate_dialog)
        edit_menu.addAction(rotate_action)
        
        edit_menu.addSeparator()
        
        copy_action = QAction("Copy Labels", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy_labels)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("Paste Labels", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.paste_labels)
        edit_menu.addAction(paste_action)
        
        edit_menu.addSeparator()
        
        # Align Labels Submenu
        align_labels_menu = edit_menu.addMenu("Align Labels")
        
        self.align_left_act = QAction("Align Left", self)
        self.align_left_act.triggered.connect(lambda: self.canvas.align_selected_labels("Left"))
        align_labels_menu.addAction(self.align_left_act)
        
        self.align_center_act = QAction("Align Center (Horizontal)", self)
        self.align_center_act.triggered.connect(lambda: self.canvas.align_selected_labels("Center"))
        align_labels_menu.addAction(self.align_center_act)
        
        self.align_right_act = QAction("Align Right", self)
        self.align_right_act.triggered.connect(lambda: self.canvas.align_selected_labels("Right"))
        align_labels_menu.addAction(self.align_right_act)
        
        align_labels_menu.addSeparator()
        
        self.align_top_act = QAction("Align Top", self)
        self.align_top_act.triggered.connect(lambda: self.canvas.align_selected_labels("Top"))
        align_labels_menu.addAction(self.align_top_act)
        
        self.align_middle_act = QAction("Align Middle (Vertical)", self)
        self.align_middle_act.triggered.connect(lambda: self.canvas.align_selected_labels("Middle"))
        align_labels_menu.addAction(self.align_middle_act)
        
        self.align_bottom_act = QAction("Align Bottom", self)
        self.align_bottom_act.triggered.connect(lambda: self.canvas.align_selected_labels("Bottom"))
        align_labels_menu.addAction(self.align_bottom_act)
        
        align_labels_menu.addSeparator()
        
        self.dist_horiz_act = QAction("Distribute Horizontally", self)
        self.dist_horiz_act.triggered.connect(lambda: self.canvas.align_selected_labels("DistributeHorizontally"))
        align_labels_menu.addAction(self.dist_horiz_act)
        
        self.dist_vert_act = QAction("Distribute Vertically", self)
        self.dist_vert_act.triggered.connect(lambda: self.canvas.align_selected_labels("DistributeVertically"))
        align_labels_menu.addAction(self.dist_vert_act)


        
        # --- View Menu ---
        view_menu = menubar.addMenu("View")
        
        fit_action = QAction("Fit Gel to Window", self)
        fit_action.setShortcut("Ctrl+0")
        fit_action.triggered.connect(lambda: self.canvas.fit_image_in_view() if self.canvas else None)
        view_menu.addAction(fit_action)
        
        grid_action = QAction("Grid Overlay Settings...", self)
        grid_action.setShortcut("Ctrl+G")
        grid_action.triggered.connect(self.open_grid_dialog)
        view_menu.addAction(grid_action)
        
        span_action = QAction("Mark Well Boundaries...", self)
        span_action.setShortcut("Ctrl+B")
        span_action.triggered.connect(self.start_span_marking_dialog)
        view_menu.addAction(span_action)
        
        ladder_action = QAction("Label Ladder Bands...", self)
        ladder_action.setShortcut("Ctrl+Shift+L")
        ladder_action.triggered.connect(self.start_ladder_marking_dialog)
        view_menu.addAction(ladder_action)
        
        align_action = QAction("Align Everything", self)
        align_action.setShortcut("Ctrl+Shift+A")
        align_action.triggered.connect(self.align_everything)
        view_menu.addAction(align_action)
        
        select_all_action = QAction("Select All Labels", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.select_all_labels)
        view_menu.addAction(select_all_action)
        
        clear_action = QAction("Clear All Labels", self)
        clear_action.triggered.connect(self.clear_labels_confirm)
        view_menu.addAction(clear_action)
        
        view_menu.addSeparator()
        self.profile_toggle_act = QAction("Show Lane Profile Panel", self)
        self.profile_toggle_act.setCheckable(True)
        self.profile_toggle_act.setChecked(True)
        self.profile_toggle_act.setShortcut("Ctrl+P")
        self.profile_toggle_act.triggered.connect(self.toggle_profile_panel)
        view_menu.addAction(self.profile_toggle_act)
        
        # --- Tools / Modules Menu ---
        tools_menu = menubar.addMenu("Tools")
        colony_action = QAction("🧫 AI Colony & Seed Counter...", self)
        colony_action.setShortcut("Ctrl+Shift+C")
        colony_action.triggered.connect(self.open_colony_counter_dialog)
        tools_menu.addAction(colony_action)
        
        # --- Help Menu ---
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About Gel Labeler", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def create_toolbars(self):
        """Creates the toolbars: Operations and Formatting & Export."""
        # --- Row 1: Operations Toolbar ---
        toolbar = self.addToolBar("Operations")
        toolbar.setMovable(False)
        
        # Open Image Button
        open_btn = QAction("📂", self)
        open_btn.setToolTip("Open Gel Image (Ctrl+O)")
        open_btn.triggered.connect(self.open_image_dialog)
        toolbar.addAction(open_btn)
        
        # New Tab Button
        new_tab_btn = QAction("➕", self)
        new_tab_btn.setToolTip("Create a New Gel Workspace Tab (Ctrl+T)")
        new_tab_btn.triggered.connect(lambda: self.add_new_tab())
        toolbar.addAction(new_tab_btn)
        
        toolbar.addSeparator()
        
        # Colony Counter Tool Button
        colony_btn = QAction("🧫", self)
        colony_btn.setToolTip("AI Colony & Seed Counter (Ctrl+Shift+C)")
        colony_btn.triggered.connect(self.open_colony_counter_dialog)
        toolbar.addAction(colony_btn)
        
        # Fit View Button
        fit_btn = QAction("⛶", self)
        fit_btn.setToolTip("Zoom to Fit (Ctrl+0)")
        fit_btn.triggered.connect(lambda: self.canvas.fit_image_in_view() if self.canvas else None)
        toolbar.addAction(fit_btn)
        
        # Generate Grid Button
        grid_btn = QAction("▦", self)
        grid_btn.setToolTip("Grid Overlay Settings (Ctrl+G)")
        grid_btn.triggered.connect(self.open_grid_dialog)
        toolbar.addAction(grid_btn)
        
        # Mark Span Button
        span_btn = QAction("📏", self)
        span_btn.setToolTip("Mark Well Boundaries (Ctrl+B)")
        span_btn.triggered.connect(self.start_span_marking_dialog)
        toolbar.addAction(span_btn)
        
        # Label Ladder Button
        ladder_btn = QAction("🪜", self)
        ladder_btn.setToolTip("Label Ladder Bands (Ctrl+Shift+L)")
        ladder_btn.triggered.connect(self.start_ladder_marking_dialog)
        toolbar.addAction(ladder_btn)
        
        # Select All Button
        select_all_btn = QAction("☑", self)
        select_all_btn.setToolTip("Select all active labels (Ctrl+A)")
        select_all_btn.triggered.connect(self.select_all_labels)
        toolbar.addAction(select_all_btn)
        
        # Align Everything Button
        align_btn = QAction("🎯", self)
        align_btn.setToolTip("Align all horizontal tiers and vertical ladders between their endpoints (Ctrl+Shift+A)")
        align_btn.triggered.connect(self.align_everything)
        toolbar.addAction(align_btn)
        
        # Align Labels Dropdown Button on Toolbar
        from PyQt6.QtWidgets import QToolButton, QMenu
        align_labels_btn = QToolButton()
        align_labels_btn.setText("⧉")
        align_labels_btn.setToolTip("PowerPoint-style alignment & distribution of selected labels")
        align_labels_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        align_labels_btn.setStyleSheet("""
            QToolButton {
                background-color: #545454;
                border: 1px solid #2b2b2b;
                border-radius: 3px;
                padding: 6px 12px;
                font-weight: bold;
                min-height: 18px;
                color: #cfcfcf;
            }
            QToolButton:hover {
                background-color: #616161;
                border-color: #e29c3d;
            }
        """)
        
        align_lbl_menu = QMenu(align_labels_btn)
        align_lbl_menu.addAction(self.align_left_act)
        align_lbl_menu.addAction(self.align_center_act)
        align_lbl_menu.addAction(self.align_right_act)
        align_lbl_menu.addSeparator()
        align_lbl_menu.addAction(self.align_top_act)
        align_lbl_menu.addAction(self.align_middle_act)
        align_lbl_menu.addAction(self.align_bottom_act)
        align_lbl_menu.addSeparator()
        align_lbl_menu.addAction(self.dist_horiz_act)
        align_lbl_menu.addAction(self.dist_vert_act)
        
        align_labels_btn.setMenu(align_lbl_menu)
        toolbar.addWidget(align_labels_btn)
        
        # Clear Button
        clear_btn = QAction("🗑", self)
        clear_btn.setToolTip("Delete all active labels")
        clear_btn.triggered.connect(self.clear_labels_confirm)
        toolbar.addAction(clear_btn)
        
        # Align Image Button
        align_toolbar_btn = QAction("🔄", self)
        align_toolbar_btn.setToolTip("Rotate/deskew image using a 2-click horizontal reference line")
        align_toolbar_btn.triggered.connect(self.trigger_align_mode)
        toolbar.addAction(align_toolbar_btn)
        
        # Profile Toggle Button
        self.profile_toolbar_btn = QAction("📊", self)
        self.profile_toolbar_btn.setCheckable(True)
        visible = self.profile_panel.isVisible() if self.profile_panel else True
        self.profile_toolbar_btn.setChecked(visible)
        self.profile_toolbar_btn.setToolTip("Toggle Lane Profile Viewer (Ctrl+P)")
        self.profile_toolbar_btn.triggered.connect(self.toggle_profile_panel)
        toolbar.addAction(self.profile_toolbar_btn)
        
        # Add a toolbar break to start a new row
        self.addToolBarBreak()
        
        # --- Row 2: Styling & Export Toolbar ---
        style_toolbar = self.addToolBar("Style & Export")
        style_toolbar.setMovable(False)
        
        # Click Mode Selection
        from PyQt6.QtWidgets import QComboBox, QLineEdit
        
        mode_lbl = QLabel(" 🖱 ")
        mode_lbl.setStyleSheet("color: #cfcfcf; font-weight: bold; font-size: 14px;")
        mode_lbl.setToolTip("Click Placement Mode")
        style_toolbar.addWidget(mode_lbl)
        
        self.click_mode_combo = QComboBox()
        self.click_mode_combo.addItems(["🚫 Disabled", "🔢 Auto-Numbering", "✍️ Quick Manual"])
        self.click_mode_combo.setToolTip(
            "Auto-Numbering: Place incrementing labels immediately on click\n"
            "Quick Manual: Show small text box on click\n"
            "Disabled: Disable click-to-place labels entirely"
        )
        style_toolbar.addWidget(self.click_mode_combo)
        self.click_mode_combo.currentTextChanged.connect(self.handle_click_mode_changed)
        self.handle_click_mode_changed(self.click_mode_combo.currentText())
        
        next_lbl = QLabel(" ✍ ")
        next_lbl.setStyleSheet("color: #cfcfcf; font-weight: bold; font-size: 14px;")
        next_lbl.setToolTip("Next placed label text/number (increments automatically)")
        style_toolbar.addWidget(next_lbl)
        
        self.next_edit = QLineEdit()
        self.next_edit.setText("1")
        self.next_edit.setFixedWidth(60)
        self.next_edit.setToolTip("The text/number that will be placed next (auto-increments on click)")
        self.next_edit.textChanged.connect(self.handle_next_edit_changed)
        style_toolbar.addWidget(self.next_edit)
        
        style_toolbar.addSeparator()
        
        # Font family combo
        from PyQt6.QtWidgets import QFontComboBox, QSpinBox
        from PyQt6.QtGui import QFont
        
        font_lbl = QLabel(" 🔤 ")
        font_lbl.setStyleSheet("color: #cfcfcf; font-weight: bold; font-size: 14px;")
        font_lbl.setToolTip("Font Family")
        style_toolbar.addWidget(font_lbl)
        
        self.font_combo = QFontComboBox()
        self.font_combo.setFixedWidth(120)
        self.font_combo.setCurrentFont(QFont("Arial"))
        self.font_combo.currentFontChanged.connect(self.change_selected_labels_font_family)
        style_toolbar.addWidget(self.font_combo)
        
        # Font size spin
        size_lbl = QLabel(" ↕ ")
        size_lbl.setStyleSheet("color: #cfcfcf; font-weight: bold; font-size: 14px;")
        size_lbl.setToolTip("Font Size (px)")
        style_toolbar.addWidget(size_lbl)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 72)
        self.font_size_spin.setValue(self.default_label_size)
        self.font_size_spin.setFixedWidth(70)
        self.font_size_spin.valueChanged.connect(self.change_selected_labels_font_size)
        style_toolbar.addWidget(self.font_size_spin)
        
        style_toolbar.addSeparator()
        
        # Color Selector Label
        color_lbl = QLabel(" 🎨 ")
        color_lbl.setStyleSheet("color: #cfcfcf; font-weight: bold; font-size: 14px;")
        color_lbl.setToolTip("Label Text Color Swatches")
        style_toolbar.addWidget(color_lbl)
        
        # Color Palette Buttons Container
        from gel_labeler.config import COLOR_PALETTE
        from PyQt6.QtWidgets import QPushButton, QHBoxLayout, QWidget
        
        color_container = QWidget()
        color_hbox = QHBoxLayout(color_container)
        color_hbox.setContentsMargins(0, 0, 0, 0)
        color_hbox.setSpacing(4)
        
        self.toolbar_color_buttons = []
        for col_data in COLOR_PALETTE:
            color_hex = col_data["value"]
            btn = QPushButton()
            btn.setFixedSize(18, 18)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color_hex};
                    border: 1px solid #2b2b2b;
                    border-radius: 9px;  /* Circle */
                }}
                QPushButton:hover {{
                    border-color: #FFFFFF;
                    border-width: 1.5px;
                }}
            """)
            btn.setToolTip(f"Set style/selected color to {col_data['name']}")
            btn.clicked.connect(lambda checked, c=color_hex: self.change_selected_labels_color(c))
            color_hbox.addWidget(btn)
            self.toolbar_color_buttons.append((color_hex, btn))
            
        style_toolbar.addWidget(color_container)
        self.update_toolbar_color_highlight(self.default_label_color)
        
        style_toolbar.addSeparator()
        
        # Export Image Button
        export_img_btn = QAction("🖼", self)
        export_img_btn.setToolTip("Export labeled gel image (PNG/JPG)")
        export_img_btn.triggered.connect(self.export_image_dialog)
        style_toolbar.addAction(export_img_btn)
        
        # Export Data Button
        export_data_btn = QAction("📄", self)
        export_data_btn.setToolTip("Export label database coordinates and metadata to CSV")
        export_data_btn.triggered.connect(self.export_csv_dialog)
        style_toolbar.addAction(export_data_btn)
        
        # Export PPTX Button
        export_pptx_btn = QAction("💻", self)
        export_pptx_btn.setToolTip("Export to PowerPoint slide deck (PPTX) with editable text labels")
        export_pptx_btn.triggered.connect(self.export_pptx_dialog)
        style_toolbar.addAction(export_pptx_btn)

    # --- UI Event Handlers ---
    
    def add_new_tab(self, name: str = None) -> GelTabWidget:
        if name is None:
            count = self.tab_widget.count() + 1
            name = f"Gel {count}"
            
        tab = GelTabWidget(self)
        
        # Connect signals for status display and cursor tracking
        tab.canvas.scene.selectionChanged.connect(self.update_selection_status)
        tab.canvas.setMouseTracking(True)
        
        # Sync initial click mode and drag settings from main toolbar if available
        if hasattr(self, 'click_mode_combo'):
            tab.click_mode = self.click_mode_combo.currentText()
            from PyQt6.QtWidgets import QGraphicsView
            if "Disabled" in tab.click_mode:
                tab.canvas.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            else:
                tab.canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
                
        if hasattr(self, 'next_edit'):
            tab.next_label_text = self.next_edit.text()
            
        self.tab_widget.addTab(tab, f"📁 {name}")
        self.tab_widget.setCurrentWidget(tab)
        return tab

    def rename_tab_dialog(self, index: int):
        """Opens a QInputDialog to allow inline renaming of the double-clicked tab."""
        if index < 0 or index >= self.tab_widget.count():
            return
            
        current_text = self.tab_widget.tabText(index)
        clean_text = current_text.replace("📁 ", "")
        
        from PyQt6.QtWidgets import QInputDialog
        new_text, ok = QInputDialog.getText(
            self, "Rename Tab",
            "Enter new tab name:",
            text=clean_text
        )
        
        if ok and new_text.strip():
            self.tab_widget.setTabText(index, f"📁 {new_text.strip()}")
            self.show_status_message(f"Tab renamed to: {new_text.strip()}")

    def autosave_path(self) -> str:
        """Returns the path of the hidden session recovery file in user AppData."""
        app_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        if not app_dir:
            app_dir = os.path.join(tempfile.gettempdir(), "GelLabeler")
        try:
            os.makedirs(app_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create app data directory {app_dir}: {e}")
            app_dir = tempfile.gettempdir()
        return os.path.join(app_dir, ".autosave_session.json")

    def serialize_session(self) -> Optional[dict]:
        """Serializes all open tabs, images, dimensions, and labels into a dictionary."""
        count = self.tab_widget.count()
        if count == 0:
            return None
            
        tabs_list = []
        for idx in range(count):
            tab = self.tab_widget.widget(idx)
            project = tab.project
            tabs_list.append({
                "name": self.tab_widget.tabText(idx),
                "image_path": project.image_path,
                "image_width": project.image_width,
                "image_height": project.image_height,
                "labels": [lbl.to_dict() for lbl in project.labels.values()]
            })
            
        return {
            "active_tab_index": self.tab_widget.currentIndex(),
            "tabs": tabs_list
        }

    def trigger_autosave(self):
        """Saves the active session atomically to disk."""
        temp_path = None
        try:
            session_data = self.serialize_session()
            if not session_data:
                return
                
            path = self.autosave_path()
            temp_path = f"{path}.tmp"
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=4)
                
            os.replace(temp_path, path)
            logger.debug(f"Autosave completed successfully to {path}")
        except Exception as e:
            logger.error(f"Error during auto-save: {e}", exc_info=True)
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def check_and_recover_session(self):
        """Checks for an auto-save file and prompts the user to restore the session."""
        path = self.autosave_path()
        # Fallback to legacy scratch path or working directory if not found in AppData
        if not os.path.exists(path):
            legacy_path = os.path.join(os.getcwd(), ".autosave_session.json")
            if os.path.exists(legacy_path):
                path = legacy_path
            else:
                return
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read autosave session file: {e}")
            return
            
        if not session_data or "tabs" not in session_data or not session_data["tabs"]:
            return
            
        reply = QMessageBox.question(
            self, "Auto-Save Recovery",
            "The application detected an unsaved session from your last run. Would you like to restore it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.No:
            # Delete file if user declines so they are not prompted again
            try:
                os.remove(path)
            except Exception as e:
                logger.warning(f"Could not remove discarded autosave file: {e}")
            return
            
        self.tab_widget.clear()
        
        from gel_labeler.core.label import GelLabel
        
        for tab_data in session_data["tabs"]:
            raw_name = tab_data.get("name", "Gel")
            
            tab = GelTabWidget(self)
            
            # Connect signals
            tab.canvas.scene.selectionChanged.connect(self.update_selection_status)
            tab.canvas.setMouseTracking(True)
            if hasattr(self, 'click_mode_combo'):
                tab.click_mode = self.click_mode_combo.currentText()
                from PyQt6.QtWidgets import QGraphicsView
                if "Disabled" in tab.click_mode:
                    tab.canvas.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
                else:
                    tab.canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
                    
            if hasattr(self, 'next_edit'):
                tab.next_label_text = self.next_edit.text()
                
            # Restore project details
            img_path = tab_data.get("image_path", None)
            if img_path and os.path.exists(img_path):
                reader = QImage(img_path)
                if not reader.isNull():
                    tab.project.load_image(img_path, reader.width(), reader.height())
                    
            # Load labels
            for label_data in tab_data.get("labels", []):
                lbl = GelLabel.from_dict(label_data)
                tab.project.labels[lbl.id] = lbl
                
            tab.profile_panel.set_project(tab.project)
            tab.canvas.load_project_image()
            
            self.tab_widget.addTab(tab, raw_name)
            
        # Restore active tab
        active_idx = session_data.get("active_tab_index", 0)
        if 0 <= active_idx < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(active_idx)
            
        self.show_status_message("Session recovered successfully.")
        self.update_window_title()

    def closeEvent(self, event):
        """Clean shutdown handler checking for unsaved changes and removing recovery file only when clean."""
        all_clean = True
        for idx in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(idx)
            if tab and tab.project.is_dirty:
                all_clean = False
                break
                
        if not all_clean:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes in one or more tabs. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            # Preserve unsaved session by capturing a snapshot before exit
            self.trigger_autosave()
        else:
            # Clean close: delete autosave backup
            try:
                path = self.autosave_path()
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.warning(f"Could not remove autosave file on clean exit: {e}")
        event.accept()

    def close_tab(self, index: int):
        tab = self.tab_widget.widget(index)
        if tab and tab.project.is_dirty:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"Tab '{self.tab_widget.tabText(index)}' has unsaved label edits. Do you want to close it and discard changes?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
                
        self.tab_widget.removeTab(index)
        
        if self.tab_widget.count() == 0:
            self.add_new_tab()

    def handle_tab_changed(self, index: int):
        tab = self.tab_widget.widget(index)
        if not tab:
            return
            
        # Block signals to prevent triggering updates while setting widget values
        if hasattr(self, 'click_mode_combo'):
            self.click_mode_combo.blockSignals(True)
            self.click_mode_combo.setCurrentText(tab.click_mode)
            self.click_mode_combo.blockSignals(False)
            
        if hasattr(self, 'next_edit'):
            self.next_edit.blockSignals(True)
            self.next_edit.setText(tab.next_label_text)
            self.next_edit.blockSignals(False)
            
        if hasattr(self, 'font_combo'):
            self.font_combo.blockSignals(True)
            from PyQt6.QtGui import QFont
            self.font_combo.setCurrentFont(QFont(tab.default_label_font_family))
            self.font_combo.blockSignals(False)
            
        if hasattr(self, 'font_size_spin'):
            self.font_size_spin.blockSignals(True)
            self.font_size_spin.setValue(tab.default_label_size)
            self.font_size_spin.blockSignals(False)
            
        # Update color swatch highlights
        self.update_toolbar_color_highlight(tab.default_label_color)
        
        # Sync profile toggle action state
        self.sync_profile_button_state()
        
        # Sync grid overlay dialog settings
        if hasattr(self, '_grid_overlay_dialog') and self._grid_overlay_dialog:
            self._grid_overlay_dialog.update_for_active_canvas()
        
        # Update window title and status
        self.update_window_title()
        if tab.project.image_path:
            self.show_status_message(f"Switched to: {os.path.basename(tab.project.image_path)}")
        else:
            self.show_status_message("Switched to empty tab.")

    def handle_next_edit_changed(self, text: str):
        tab = self.active_tab
        if tab:
            tab.next_label_text = text

    def open_image_dialog(self):
        """Prompts user to select one or multiple gel images and loads them into tabs."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Gel Electrophoresis Image(s)", "", 
            "Image Files (*.png *.jpg *.jpeg *.tif *.tiff *.bmp)"
        )
        
        if not file_paths:
            return
            
        for idx, file_path in enumerate(file_paths):
            tab = self.active_tab
            
            # If the active tab already has an image, OR this is not the first file,
            # we create a new tab.
            if not tab or tab.project.image_path or idx > 0:
                tab = self.add_new_tab(os.path.basename(file_path))
            elif tab and tab.project.is_dirty:
                reply = QMessageBox.question(
                    self, "Unsaved Changes",
                    f"The current tab has unsaved changes. Overwrite with '{os.path.basename(file_path)}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    tab = self.add_new_tab(os.path.basename(file_path))
                
            reader = QImage(file_path)
            if reader.isNull():
                QMessageBox.critical(self, "Load Error", f"Failed to load image file: {os.path.basename(file_path)}")
                continue
                
            tab.project.reset()
            tab.project.load_image(file_path, reader.width(), reader.height())
            tab.profile_panel.set_project(tab.project)
            
            # Rename tab to image filename
            t_idx = self.tab_widget.indexOf(tab)
            if t_idx >= 0:
                self.tab_widget.setTabText(t_idx, f"📁 {os.path.basename(file_path)}")
                
            tab.canvas.load_project_image()
            
        self.show_status_message(f"Successfully loaded {len(file_paths)} gel image(s).")
        self.update_window_title()

    def open_folder_dialog(self):
        """Prompts user to select a directory and loads all gel images inside it in alphabetical order."""
        dir_path = QFileDialog.getExistingDirectory(self, "Open Folder of Gel Images", "")
        if not dir_path:
            return
            
        # Scan for common image files
        valid_extensions = ('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp')
        img_files = []
        try:
            for entry in os.scandir(dir_path):
                if entry.is_file() and entry.name.lower().endswith(valid_extensions):
                    img_files.append(entry.path)
        except Exception as e:
            QMessageBox.critical(self, "Read Error", f"Failed to scan folder: {e}")
            return
            
        if not img_files:
            QMessageBox.warning(self, "No Images Found", "No valid gel images were found in the selected folder.")
            return
            
        # Sort alphabetically so they open in order
        img_files.sort(key=lambda x: os.path.basename(x).lower())
        
        # Cap batch folder loading at 100 images to prevent memory exhaustion
        max_batch = 100
        if len(img_files) > max_batch:
            reply = QMessageBox.question(
                self, "Large Batch Warning",
                f"Found {len(img_files)} images in folder. Loading all of them may consume high memory. Limit to first {max_batch} images?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                img_files = img_files[:max_batch]

        from PyQt6.QtWidgets import QApplication
        for idx, file_path in enumerate(img_files):
            tab = self.active_tab
            
            if not tab or tab.project.image_path or idx > 0:
                tab = self.add_new_tab(os.path.basename(file_path))
                
            reader = QImage(file_path)
            if reader.isNull():
                continue
                
            tab.project.reset()
            tab.project.load_image(file_path, reader.width(), reader.height())
            tab.profile_panel.set_project(tab.project)
            
            t_idx = self.tab_widget.indexOf(tab)
            if t_idx >= 0:
                self.tab_widget.setTabText(t_idx, f"📁 {os.path.basename(file_path)}")
                
            tab.canvas.load_project_image()
            if idx % 10 == 0:
                QApplication.processEvents()
            
        self.show_status_message(f"Successfully loaded {len(img_files)} gel image(s) from folder.")
        self.update_window_title()


    def open_grid_dialog(self):
        """Spawns the modeless GridOverlayDialog to configure reference grid lines."""
        if not self.active_tab or not self.active_tab.project.image_path:
            QMessageBox.warning(self, "No Image", "Please load a gel image before enabling the grid overlay.")
            return
            
        if hasattr(self, '_grid_overlay_dialog') and self._grid_overlay_dialog:
            self._grid_overlay_dialog.raise_()
            self._grid_overlay_dialog.activateWindow()
            return
            
        self._grid_overlay_dialog = GridOverlayDialog(self)
        self._grid_overlay_dialog.finished.connect(self.handle_grid_dialog_closed)
        self._grid_overlay_dialog.show()

    def handle_grid_dialog_closed(self):
        self._grid_overlay_dialog = None

    def open_colony_counter_dialog(self):
        """Launches the standalone AI Vision Colony & Seed Counter dialog."""
        from gel_labeler.gui.colony_counter_dialog import ColonyCounterDialog
        dialog = ColonyCounterDialog(self)
        dialog.exec()

    def start_span_marking_dialog(self):
        """Opens config dialog and starts interactive 2-click span marking."""
        if not self.project.image_path:
            QMessageBox.warning(self, "No Image", "Please load a gel image before defining boundaries.")
            return
            
        from PyQt6.QtWidgets import QDialog, QComboBox, QSpinBox, QPushButton, QFormLayout, QLineEdit
        
        class SpanConfigDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Mark Deck Span")
                self.setStyleSheet(parent.styleSheet())  # Inherit styling
                layout = QFormLayout(self)
                layout.setSpacing(12)
                layout.setContentsMargins(16, 16, 16, 16)
                
                self.tier_combo = QComboBox()
                self.tier_combo.addItems(["Tier 1 (Top)", "Tier 2 (Bottom)"])
                layout.addRow("Select Deck:", self.tier_combo)
                
                self.pattern_input = QLineEdit()
                self.pattern_input.setText("Ladder, 1-29")
                layout.addRow("Lanes Pattern:", self.pattern_input)
                
                self.rot_combo = QComboBox()
                self.rot_combo.addItems([
                    "0° (Horizontal)",
                    "90° (Vertical Down)",
                    "270° (Vertical Up)",
                    "45° (Slanted)"
                ])
                self.rot_combo.setCurrentIndex(0)
                layout.addRow("Text Rotation:", self.rot_combo)
                
                self.size_spin = QSpinBox()
                self.size_spin.setRange(8, 72)
                self.size_spin.setValue(12)
                layout.addRow("Font Size (px):", self.size_spin)
                
                btn_layout = QHBoxLayout()
                self.cancel_btn = QPushButton("❌ Cancel")
                self.cancel_btn.clicked.connect(self.reject)
                self.ok_btn = QPushButton("🚀 Start Marking")
                self.ok_btn.setObjectName("primaryBtn")
                self.ok_btn.clicked.connect(self.accept)
                
                btn_layout.addStretch()
                btn_layout.addWidget(self.cancel_btn)
                btn_layout.addWidget(self.ok_btn)
                layout.addRow(btn_layout)
                
            def get_selected_rotation(self) -> float:
                idx = self.rot_combo.currentIndex()
                if idx == 1:
                    return 90.0
                elif idx == 2:
                    return 270.0
                elif idx == 3:
                    return 45.0
                return 0.0
                
            def get_config(self):
                from gel_labeler.core.pattern_parser import parse_label_pattern
                pattern = self.pattern_input.text().strip()
                labels = parse_label_pattern(pattern)
                return {
                    "name": self.tier_combo.currentText(),
                    "labels": labels,
                    "color": DEFAULT_COLOR,  # Default color from config
                    "font_size": self.size_spin.value(),
                    "rotation": self.get_selected_rotation()
                }
                
        dialog = SpanConfigDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_config()
            self.canvas.enter_span_mode(config)

    def start_ladder_marking_dialog(self):
        """Opens configuration dialog and enters interactive ladder labeling mode."""
        if not self.project.image_path:
            QMessageBox.warning(self, "No Image", "Please load a gel image before annotating a ladder.")
            return
            
        from PyQt6.QtWidgets import QDialog, QComboBox, QFormLayout, QLineEdit, QPushButton, QSpinBox
        
        class LadderConfigDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Label Ladder Bands")
                self.setStyleSheet(parent.styleSheet())
                layout = QFormLayout(self)
                layout.setSpacing(12)
                layout.setContentsMargins(16, 16, 16, 16)
                
                self.ladder_combo = QComboBox()
                self.ladder_combo.addItems([
                    "100bp Ladder (100bp - 1000bp)",
                    "1kb Ladder (250bp - 10kb)",
                    "Custom (Comma-separated)"
                ])
                layout.addRow("Ladder Preset:", self.ladder_combo)
                
                self.custom_input = QLineEdit()
                self.custom_input.setPlaceholderText("e.g. 1000, 500, 200, 100")
                self.custom_input.setEnabled(False)
                layout.addRow("Custom Sizes:", self.custom_input)
                
                self.ladder_combo.currentIndexChanged.connect(self.toggle_custom)
                
                self.align_combo = QComboBox()
                self.align_combo.addItems(["Left", "Right"])
                layout.addRow("Alignment:", self.align_combo)
                
                self.size_spin = QSpinBox()
                self.size_spin.setRange(6, 24)
                self.size_spin.setValue(10)
                layout.addRow("Font Size (px):", self.size_spin)
                
                self.rot_combo = QComboBox()
                self.rot_combo.addItems([
                    "0° (Horizontal)",
                    "90° (Vertical Down)",
                    "270° (Vertical Up)",
                    "45° (Slanted)"
                ])
                self.rot_combo.setCurrentIndex(2)
                layout.addRow("Text Rotation:", self.rot_combo)
                
                btn_layout = QHBoxLayout()
                self.cancel_btn = QPushButton("❌ Cancel")
                self.cancel_btn.clicked.connect(self.reject)
                self.ok_btn = QPushButton("🚀 Start Marking")
                self.ok_btn.setObjectName("primaryBtn")
                self.ok_btn.clicked.connect(self.accept)
                
                btn_layout.addStretch()
                btn_layout.addWidget(self.cancel_btn)
                btn_layout.addWidget(self.ok_btn)
                layout.addRow(btn_layout)
                
            def toggle_custom(self, idx):
                self.custom_input.setEnabled(idx == 2)
                
            def get_bands(self) -> list:
                idx = self.ladder_combo.currentIndex()
                if idx == 0:
                    return ["1000bp", "900bp", "800bp", "700bp", "600bp", "500bp", "400bp", "300bp", "200bp", "100bp"]
                elif idx == 1:
                    return ["10kb", "8kb", "6kb", "5kb", "4kb", "3kb", "2.5kb", "2kb", "1.5kb", "1kb", "750bp", "500bp", "250bp"]
                else:
                    text = self.custom_input.text().strip()
                    if not text:
                        return ["Band"]
                    return [b.strip() for b in text.split(",") if b.strip()]
                    
            def get_selected_rotation(self) -> float:
                idx = self.rot_combo.currentIndex()
                if idx == 1:
                    return 90.0
                elif idx == 2:
                    return 270.0
                elif idx == 3:
                    return 45.0
                return 0.0
                
            def get_config(self) -> dict:
                return {
                    "bands": self.get_bands(),
                    "alignment": self.align_combo.currentText(),
                    "color": "#FFFFFF",  # Pure white looks best for ladder annotations next to lanes
                    "font_size": self.size_spin.value(),
                    "rotation": self.get_selected_rotation()
                }
                
        dialog = LadderConfigDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_config()
            self.canvas.enter_ladder_mode(config)

    def export_image_dialog(self):
        """Saves the graphical canvas directly into image pixels (high quality)."""
        if not self.project.image_path:
            QMessageBox.warning(self, "No Image", "Please load a gel image before exporting.")
            return
            
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Labeled Gel Image", 
            os.path.splitext(self.project.image_path)[0] + "_labeled.png",
            "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg)"
        )
        
        if file_path:
            # Create a blank high-resolution image matching scene coordinates
            scene_rect = self.canvas.scene.sceneRect()
            output_image = QImage(scene_rect.size().toSize(), QImage.Format.Format_ARGB32)
            
            # Fill background appropriately
            is_jpeg = file_path.lower().endswith(('.jpg', '.jpeg'))
            if is_jpeg:
                output_image.fill(Qt.GlobalColor.white)
            else:
                output_image.fill(Qt.GlobalColor.transparent)
            
            # Use QPainter to draw the scene directly onto the image
            painter = QPainter(output_image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            
            self.canvas.scene.render(painter)
            painter.end()
            
            if is_jpeg:
                output_image = output_image.convertToFormat(QImage.Format.Format_RGB32)
            
            # Save final image
            success = output_image.save(file_path)
            if success:
                self.show_status_message(f"Image successfully exported to: {os.path.basename(file_path)}")
            else:
                QMessageBox.critical(self, "Export Error", "Failed to save the exported image.")


    def save_json_dialog(self):
        """Saves the label coordinates and properties database as JSON."""
        if not self.project.image_path:
            QMessageBox.warning(self, "No Image", "Please load a gel image before saving label data.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Labels Database (JSON)", 
            os.path.splitext(self.project.image_path)[0] + "_labels.json",
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                self.project.save_to_json(file_path)
                self.show_status_message(f"Labels saved to: {os.path.basename(file_path)}")
                self.update_window_title()
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save JSON file: {e}")

    def load_json_dialog(self):
        """Loads a labels database from JSON and repopulates the canvas."""
        if not self.project.image_path:
            QMessageBox.warning(self, "No Image", "Please load the corresponding gel image before loading label data.")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Labels Database (JSON)", "", 
            "JSON Files (*.json)"
        )
        
        if file_path:
            if self.project.load_from_json(file_path):
                # Repopulate items on canvas (deferred to prevent PyQt selection crashes)
                QTimer.singleShot(0, self.canvas.deferred_reload)
                self.show_status_message(f"Loaded labels from: {os.path.basename(file_path)}")
                self.update_window_title()
            else:
                QMessageBox.critical(self, "Load Error", "Failed to parse labels from JSON.")

    def export_csv_dialog(self):
        """Exports the label database as a CSV spreadsheet."""
        if not self.project.image_path:
            QMessageBox.warning(self, "No Image", "Please load a gel image before exporting database.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Labels to CSV", 
            os.path.splitext(self.project.image_path)[0] + "_labels.csv",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                self.project.export_to_csv(file_path)
                self.show_status_message(f"Database exported to: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export CSV: {e}")

    def export_pptx_dialog(self):
        """Exports selected tabs as widescreen PowerPoint slides compiled into a single file."""
        dialog = PptxExportDialog(self.tab_widget, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        selected_info = dialog.get_selected_tab_indices_and_titles()
        if not selected_info:
            QMessageBox.warning(self, "No Tabs Selected", "Please select at least one tab to export.")
            return
            
        existing_pptx_path = dialog.get_existing_pptx_path()
        default_save_path = existing_pptx_path if existing_pptx_path else "compiled_gel_presentation.pptx"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Selected Gels to PowerPoint (PPTX)", 
            default_save_path,
            "PowerPoint Files (*.pptx)"
        )
        
        if file_path:
            try:
                # Compile projects with their names and titles
                projects_with_names = []
                for idx, slide_title in selected_info:
                    tab = self.tab_widget.widget(idx)
                    tab_name = self.tab_widget.tabText(idx).replace("📁 ", "")
                    projects_with_names.append((tab.project, tab_name, slide_title))
                    
                from gel_labeler.core.project import GelProject
                GelProject.compile_projects_to_pptx(file_path, projects_with_names, existing_pptx_path)
                self.show_status_message(f"PowerPoint slide deck successfully compiled: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export compiled PPTX: {e}")

    def copy_labels(self):
        """Copies selected labels (or all labels if none are selected) to the layout template clipboard."""
        active_tab = self.active_tab
        if not active_tab:
            return
            
        selected_items = [item for item in active_tab.canvas.scene.selectedItems() if hasattr(item, 'label_data')]
        
        # If nothing is selected, copy all labels
        if not selected_items:
            labels_to_copy = list(active_tab.project.labels.values())
        else:
            labels_to_copy = [item.label_data for item in selected_items]
            
        if not labels_to_copy:
            self.show_status_message("No labels to copy.")
            return
            
        self.clipboard_labels = [label.to_dict() for label in labels_to_copy]
        self.show_status_message(f"Copied {len(self.clipboard_labels)} label(s) to layout template clipboard.")

    def paste_labels(self):
        """Pastes copied labels onto the current active tab at their original coordinates."""
        active_tab = self.active_tab
        if not active_tab:
            return
            
        if not self.clipboard_labels:
            self.show_status_message("Clipboard is empty. Copy labels first.")
            return
            
        project = active_tab.project
        project.save_undo_state()
        
        from gel_labeler.core.label import GelLabel
        pasted_count = 0
        new_ids = []
        
        # Clear selection first so we can highlight pasted ones cleanly
        active_tab.canvas.scene.clearSelection()
        
        for label_dict in self.clipboard_labels:
            copied_dict = dict(label_dict)
            copied_dict["id"] = None
            new_label = GelLabel.from_dict(copied_dict)
            
            project.labels[new_label.id] = new_label
            new_ids.append(new_label.id)
            active_tab.canvas.create_label_item(new_label)
            pasted_count += 1
            
        if pasted_count > 0:
            project.is_dirty = True
            self.update_window_title()
            
            # Select the newly pasted labels so user can move them immediately
            for lid in new_ids:
                if lid in active_tab.canvas.label_items:
                    active_tab.canvas.label_items[lid].setSelected(True)
                    
            self.show_status_message(f"Pasted {pasted_count} label(s) onto the current tab.")


    def clear_labels_confirm(self):
        """Prompts user to confirm clearing all active labels."""
        if not self.project.labels:
            return
            
        reply = QMessageBox.question(
            self, "Clear Labels",
            "Are you sure you want to clear all labels?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.canvas.clear_all_labels()

    def undo_action_trigger(self):
        """Restores the previous state from the project's undo stack."""
        if self.project.undo():
            # Reload from updated project labels (deferred to prevent PyQt selection crashes)
            QTimer.singleShot(0, self.canvas.deferred_reload)
            self.show_status_message("Undo successful.")
        else:
            self.show_status_message("Nothing to undo.")

    def align_everything(self):
        """Aligns all horizontal tiers and vertical ladders in the project."""
        if not self.project.labels:
            QMessageBox.information(self, "No Labels", "There are no labels to align.")
            return
            
        if self.project.align_all_labels():
            # Defer reloading to prevent PyQt selection crashes
            QTimer.singleShot(0, self.canvas.deferred_reload)
            self.show_status_message("Successfully aligned all tiers and ladders!")
        else:
            QMessageBox.information(self, "Alignment", "No components (tiers or ladders) with 2 or more labels were found to align.")

    def trigger_align_mode(self):
        """Enters interactive 2-click alignment mode on the canvas."""
        if not self.project.image_path:
            QMessageBox.warning(self, "No Image", "Please load a gel image before aligning.")
            return
        self.canvas.enter_align_mode()

    def open_manual_rotate_dialog(self):
        """Opens a dialog to manually rotate the image by a specific angle."""
        if not self.project.image_path:
            QMessageBox.warning(self, "No Image", "Please load a gel image before rotating.")
            return
            
        from PyQt6.QtWidgets import QDialog, QDoubleSpinBox, QFormLayout, QPushButton
        
        class RotateDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Rotate Image (Manual)")
                self.setModal(True)
                self.setStyleSheet(parent.styleSheet() if parent else "")
                
                layout = QFormLayout(self)
                layout.setSpacing(12)
                layout.setContentsMargins(16, 16, 16, 16)
                
                self.angle_spin = QDoubleSpinBox()
                self.angle_spin.setRange(-180.0, 180.0)
                self.angle_spin.setDecimals(1)
                self.angle_spin.setSingleStep(0.5)
                self.angle_spin.setValue(0.0)
                self.angle_spin.setSuffix("°")
                layout.addRow("Rotation Angle:", self.angle_spin)
                
                btn_layout = QHBoxLayout()
                cancel_btn = QPushButton("Cancel")
                cancel_btn.clicked.connect(self.reject)
                ok_btn = QPushButton("Apply")
                ok_btn.setObjectName("primaryBtn")
                ok_btn.clicked.connect(self.accept)
                
                btn_layout.addStretch()
                btn_layout.addWidget(cancel_btn)
                btn_layout.addWidget(ok_btn)
                layout.addRow(btn_layout)
                
            def get_angle(self) -> float:
                return self.angle_spin.value()
                
        dialog = RotateDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            angle = dialog.get_angle()
            if abs(angle) > 0.01:
                self.project.rotate_image(angle)
                # Defer reloading to prevent PyQt selection crashes
                QTimer.singleShot(0, self.canvas.deferred_reload)
                self.show_status_message(f"Rotated image manually by {angle}°")

    def increment_next_label(self, current_text: str):
        """Increments the next label text box counter."""
        if not current_text:
            self.next_edit.setText("1")
            return
        trimmed = current_text.strip()
        if trimmed.lower() in ("ladder", "nc", "pc", "blank", "ctrl", "control", "water", "ntc", "marker"):
            self.next_edit.setText(current_text)
            return

        import re
        match = re.search(r"(\d+)$", current_text)
        if match:
            num_str = match.group(1)
            num_val = int(num_str) + 1
            new_num_str = str(num_val).zfill(len(num_str))
            next_text = current_text[:match.start()] + new_num_str
        else:
            next_text = current_text + "1"
            
        self.next_edit.setText(next_text)

    def select_all_labels(self):
        """Selects all label items on the canvas."""
        for item in self.canvas.label_items.values():
            item.setSelected(True)
        self.show_status_message(f"Selected all {len(self.canvas.label_items)} labels. Click any color dot to change their colors.")

    def change_selected_labels_color(self, selected_color: str):
        """Changes the color of all selected labels, and updates default label color."""
        self.default_label_color = selected_color
        self.update_toolbar_color_highlight(selected_color)
        
        selected_items = self.canvas.scene.selectedItems()
        modified = False
        if selected_items:
            self.project.save_undo_state()
            for item in selected_items:
                if hasattr(item, 'label_data'):
                    item.label_data.update_style(color=selected_color)
                    item.refresh()
                    modified = True
                    
        if modified:
            self.project.is_dirty = True
            self.update_window_title()
            self.show_status_message(f"Changed color of selected labels to {selected_color}.")

    def change_selected_labels_font_family(self, font):
        """Changes the font family of all selected labels, and updates default font family."""
        font_family = font.family()
        self.default_label_font_family = font_family
        
        selected_items = self.canvas.scene.selectedItems()
        modified = False
        if selected_items:
            self.project.save_undo_state()
            for item in selected_items:
                if hasattr(item, 'label_data'):
                    item.label_data.update_style(font_family=font_family)
                    item.refresh()
                    modified = True
                    
        if modified:
            self.project.is_dirty = True
            self.update_window_title()
            self.show_status_message(f"Changed font family of selected labels to {font_family}.")

    def change_selected_labels_font_size(self, size: int):
        """Changes the font size of all selected labels, and updates default font size."""
        self.default_label_size = size
        
        selected_items = self.canvas.scene.selectedItems()
        modified = False
        if selected_items:
            self.project.save_undo_state()
            for item in selected_items:
                if hasattr(item, 'label_data'):
                    item.label_data.update_style(font_size=size)
                    item.refresh()
                    modified = True
                    
        if modified:
            self.project.is_dirty = True
            self.update_window_title()
            self.show_status_message(f"Changed font size of selected labels to {size}px.")

    def update_toolbar_color_highlight(self, active_color: str):
        """Highlights the active color button in the toolbar."""
        if not hasattr(self, 'toolbar_color_buttons') or not self.toolbar_color_buttons:
            return
        for hex_val, btn in self.toolbar_color_buttons:
            border_color = "#FFFFFF" if hex_val.upper() == "#000000" else "#000000"
            if hex_val.upper() == active_color.upper():
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_val};
                        border: 2px solid {border_color};
                        border-radius: 9px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_val};
                        border: 1px solid #3A3A4A;
                        border-radius: 9px;
                    }}
                    QPushButton:hover {{
                        border-color: #FFFFFF;
                        border-width: 1.5px;
                    }}
                """)

    def show_about_dialog(self):
        """Displays application details."""
        QMessageBox.about(
            self, "About Gel Labeler",
            "<h3>Gel Labeler — Gel Electrophoresis Suite</h3>"
            "<p>A professional utility for annotating molecular gel wells and counting bacterial colonies.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "  <li>Precise pixel-locked coordinates & alignment tools</li>"
            "  <li>Draggable & style-adjustable text items</li>"
            "  <li>Subtle high-contrast text glow/drop shadows</li>"
            "  <li>AI Vision Colony & Seed Counter with CFU estimation</li>"
            "  <li>JSON Database, CSV Spreadsheet, and PowerPoint (PPTX) export</li>"
            "  <li>High-resolution pixel-perfect image export</li>"
            "</ul>"
            "<p>Author: Devanandan K C</p>"
        )

    # --- State Sync & Updates ---

    def handle_project_modified(self):
        """Triggered whenever labels are added, dragged, or deleted."""
        self.update_window_title()

    def handle_click_mode_changed(self, mode: str):
        """Changes the canvas drag mode depending on selected click mode."""
        tab = self.active_tab
        if tab:
            tab.click_mode = mode
            if tab.canvas:
                from PyQt6.QtWidgets import QGraphicsView
                if "Disabled" in mode:
                    tab.canvas.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
                else:
                    tab.canvas.setDragMode(QGraphicsView.DragMode.NoDrag)

    def update_window_title(self):
        """Updates window title showing file name and modification state."""
        title = "Gel Labeler"
        if self.project.image_path:
            filename = os.path.basename(self.project.image_path)
            dirty_star = "*" if self.project.is_dirty else ""
            title = f"{filename}{dirty_star} - {title}"
        self.setWindowTitle(title)

    def show_status_message(self, message: str):
        """Updates the status bar message."""
        self.status_bar.showMessage(message, 5000)

    def update_selection_status(self):
        """Updates coordination readouts if any items are active."""
        if not self.active_tab or not self.canvas or not self.canvas.scene:
            if hasattr(self, 'coord_label'):
                self.coord_label.setText("")
            return
            
        selected_items = self.canvas.scene.selectedItems()
        if selected_items:
            item = selected_items[0]
            pos = item.pos()
            self.coord_label.setText(f"Selected: '{item.toPlainText()}' at pixel: ({int(pos.x())}, {int(pos.y())})")
            
            # Real-time profile graph update on selection
            if hasattr(self, 'profile_panel') and hasattr(item, 'label_data') and self.profile_panel:
                self.profile_panel.set_selected_label(item.label_data)
            
            # Update toolbar controls to match selected item style
            if hasattr(self, 'font_combo') and hasattr(self, 'font_size_spin'):
                self.font_combo.blockSignals(True)
                self.font_size_spin.blockSignals(True)
                
                from PyQt6.QtGui import QFont
                self.font_combo.setCurrentFont(QFont(item.label_data.font_family))
                self.font_size_spin.setValue(item.label_data.font_size)
                
                self.font_combo.blockSignals(False)
                self.font_size_spin.blockSignals(False)
        else:
            self.coord_label.setText("")
            if hasattr(self, 'profile_panel') and self.profile_panel:
                self.profile_panel.set_selected_label(None)

    def on_selected_label_dragged(self, label_id: str, new_x: float, new_y: float):
        """Triggered in real time when a selected label is dragged."""
        if hasattr(self, 'profile_panel') and self.profile_panel:
            self.profile_panel.update_drag_position(label_id, new_x, new_y)

    def toggle_profile_panel(self):
        """Toggles the visibility of the lane profile panel."""
        if hasattr(self, 'profile_panel') and self.profile_panel:
            visible = not self.profile_panel.isVisible()
            self.profile_panel.setVisible(visible)
            self.sync_profile_button_state()

    def sync_profile_button_state(self):
        """Syncs the toolbar/menu action state with the panel visibility."""
        if hasattr(self, 'profile_panel') and self.profile_panel:
            if hasattr(self, 'profile_toggle_act'):
                self.profile_toggle_act.blockSignals(True)
                self.profile_toggle_act.setChecked(self.profile_panel.isVisible())
                self.profile_toggle_act.blockSignals(False)
            if hasattr(self, 'profile_toolbar_btn'):
                self.profile_toolbar_btn.blockSignals(True)
                self.profile_toolbar_btn.setChecked(self.profile_panel.isVisible())
                self.profile_toolbar_btn.blockSignals(False)

