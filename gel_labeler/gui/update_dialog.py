"""
Modern, interactive Update Dialog for checking and viewing GitHub Releases.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QProgressBar, QFrame
)
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from gel_labeler.core.updater import (
    CURRENT_VERSION, GITHUB_REPO_URL, GITHUB_RELEASES_URL,
    UpdateCheckWorker
)


class UpdateDialog(QDialog):
    """Dialog displaying current version, latest GitHub release status, and update notes."""

    def __init__(self, parent=None, auto_start_check: bool = True):
        super().__init__(parent)
        self.setWindowTitle("Check for Updates — Gel Labeler")
        self.setFixedSize(520, 420)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #cfcfcf;
            }
            QLabel {
                color: #cfcfcf;
                font-size: 12px;
            }
            QTextEdit {
                background-color: #151515;
                border: 1px solid #333333;
                border-radius: 4px;
                color: #dcdcdc;
                padding: 8px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11px;
            }
            QPushButton {
                background-color: #3b3b3b;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                color: #ffffff;
                font-weight: bold;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #e29c3d;
            }
            QPushButton:disabled {
                background-color: #252525;
                border-color: #333333;
                color: #666666;
            }
            QProgressBar {
                background-color: #151515;
                border: 1px solid #333333;
                border-radius: 3px;
                height: 6px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #e29c3d;
            }
        """)

        self.worker = None
        self.release_url = GITHUB_RELEASES_URL
        self.download_url = GITHUB_RELEASES_URL

        self.init_ui()
        if auto_start_check:
            self.start_check()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header Banner
        header_layout = QHBoxLayout()
        icon_lbl = QLabel("🧬")
        icon_lbl.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        title_lbl = QLabel("Gel Labeler Suite Updates")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        self.ver_lbl = QLabel(f"Installed Version: <b>v{CURRENT_VERSION}</b>")
        self.ver_lbl.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(self.ver_lbl)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2b2b2b;")
        main_layout.addWidget(sep)

        # 2. Status Card
        self.status_box = QFrame()
        self.status_box.setStyleSheet("background-color: #25282c; border: 1px solid #363a45; border-radius: 6px; padding: 10px;")
        status_layout = QVBoxLayout(self.status_box)
        status_layout.setSpacing(6)

        self.status_header = QLabel("Connecting to GitHub...")
        self.status_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #e29c3d;")
        self.status_detail = QLabel("Checking for the latest releases on github.com/vropalcrown/pcr-gel-labbler...")
        self.status_detail.setWordWrap(True)
        self.status_detail.setStyleSheet("color: #cfcfcf; font-size: 11px;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate pulsing animation
        self.progress_bar.setFixedHeight(5)

        status_layout.addWidget(self.status_header)
        status_layout.addWidget(self.status_detail)
        status_layout.addWidget(self.progress_bar)

        main_layout.addWidget(self.status_box)

        # 3. Release Notes / Changelog area
        notes_label = QLabel("Release Information / What's New:")
        notes_label.setStyleSheet("font-weight: bold; color: #8e95a5; font-size: 11px;")
        main_layout.addWidget(notes_label)

        self.notes_edit = QTextEdit()
        self.notes_edit.setReadOnly(True)
        self.notes_edit.setPlaceholderText("Release notes will appear here...")
        main_layout.addWidget(self.notes_edit, stretch=1)

        # 4. Action Buttons Footer
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)

        self.github_repo_btn = QPushButton("🌐 View on GitHub")
        self.github_repo_btn.setToolTip("Open GitHub repository in browser")
        self.github_repo_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_REPO_URL)))
        footer_layout.addWidget(self.github_repo_btn)

        footer_layout.addStretch()

        self.check_again_btn = QPushButton("🔄 Check Again")
        self.check_again_btn.clicked.connect(self.start_check)
        footer_layout.addWidget(self.check_again_btn)

        self.action_btn = QPushButton("🚀 Open Release Page")
        self.action_btn.setEnabled(False)
        self.action_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                border: 1px solid #2ea043;
                color: #ffffff;
                font-weight: bold;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
            QPushButton:disabled {
                background-color: #25282c;
                border: 1px solid #363a45;
                color: #666666;
            }
        """)
        self.action_btn.clicked.connect(self.on_action_clicked)
        footer_layout.addWidget(self.action_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(self.close_btn)

        main_layout.addLayout(footer_layout)

    def start_check(self):
        """Starts asynchronous check in worker thread."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_header.setText("Checking GitHub for Updates...")
        self.status_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #e29c3d;")
        self.status_detail.setText("Querying repository releases at api.github.com...")
        self.action_btn.setEnabled(False)
        self.check_again_btn.setEnabled(False)

        self.worker = UpdateCheckWorker(local_version=CURRENT_VERSION, parent=self)
        self.worker.check_completed.connect(self.on_check_completed)
        self.worker.check_failed.connect(self.on_check_failed)
        self.worker.start()

    def on_check_completed(self, has_update: bool, latest_version: str, release_url: str, release_notes: str, download_url: str):
        self.progress_bar.setVisible(False)
        self.check_again_btn.setEnabled(True)
        self.release_url = release_url
        self.download_url = download_url
        self.notes_edit.setText(release_notes if release_notes else "No release notes provided for this version.")

        if has_update:
            self.status_header.setText(f"🎉 Update Available: {latest_version}!")
            self.status_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #58a6ff;")
            self.status_detail.setText(
                f"A newer version (<b>{latest_version}</b>) is available on GitHub. "
                f"You are currently running version <b>v{CURRENT_VERSION}</b>."
            )
            self.action_btn.setText("🚀 Download Latest Version")
            self.action_btn.setEnabled(True)
        else:
            self.status_header.setText("✔️ You're Running the Latest Version!")
            self.status_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #3fb950;")
            self.status_detail.setText(
                f"Gel Labeler <b>v{CURRENT_VERSION}</b> is currently up to date. "
                "No newer version is published on GitHub."
            )
            self.action_btn.setText("View Releases")
            self.action_btn.setEnabled(True)

    def on_check_failed(self, error_message: str):
        self.progress_bar.setVisible(False)
        self.check_again_btn.setEnabled(True)
        self.status_header.setText("⚠️ Unable to Check for Updates")
        self.status_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #f85149;")
        self.status_detail.setText(
            f"Could not connect to GitHub:\n{error_message}\n\n"
            "You can still check releases manually by clicking 'View on GitHub'."
        )
        self.action_btn.setText("Open Releases in Browser")
        self.action_btn.setEnabled(True)

    def on_action_clicked(self):
        target = self.download_url or self.release_url or GITHUB_RELEASES_URL
        QDesktopServices.openUrl(QUrl(target))
