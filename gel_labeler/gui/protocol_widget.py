"""
Interactive Protocol & SOP Bench Runner Widget with custom protocol creation, editing, and execution.
"""
import uuid
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QScrollArea, QCheckBox, QPushButton, QProgressBar, 
    QFrame, QMessageBox, QApplication, QLineEdit, QDialog,
    QTextEdit, QSpinBox, QGroupBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer

from gel_labeler.core.protocol import (
    Protocol, ProtocolStep, load_user_protocols, save_user_protocols,
    export_protocol_to_json, import_protocol_from_json
)


class StepCardWidget(QFrame):
    """Widget card representing a single protocol step with checkbox, notes, and countdown timer."""

    def __init__(self, step: ProtocolStep, on_step_toggled=None, parent=None):
        super().__init__(parent)
        self.step = step
        self.on_step_toggled = on_step_toggled
        self.remaining_seconds = step.duration_seconds or 0
        self.is_timer_running = False

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._timer_tick)

        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            StepCardWidget {
                background-color: #242424;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 10px;
            }
            StepCardWidget[completed="true"] {
                background-color: #1a251e;
                border: 1px solid #2a9d8f;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header: Step Checkbox & Title & Timer display
        header_layout = QHBoxLayout()
        self.checkbox = QCheckBox(f"Step {self.step.step_num}: {self.step.title}")
        self.checkbox.setChecked(self.step.is_completed)
        self.checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                font-size: 13px;
                color: #e29c3d;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        self.checkbox.toggled.connect(self._handle_toggle)
        header_layout.addWidget(self.checkbox)
        header_layout.addStretch()

        # Timer Controls (if applicable)
        if self.step.duration_seconds and self.step.duration_seconds > 0:
            self.timer_lbl = QLabel(self._format_time(self.remaining_seconds))
            self.timer_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #00ffcc; padding-right: 6px;")

            self.timer_btn = QPushButton("▶ Start Timer")
            self.timer_btn.setFixedWidth(100)
            self.timer_btn.setStyleSheet("""
                QPushButton {
                    background-color: #333333;
                    border: 1px solid #444444;
                    border-radius: 3px;
                    padding: 3px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #00aa88;
                    color: #ffffff;
                }
            """)
            self.timer_btn.clicked.connect(self._toggle_timer)

            self.reset_timer_btn = QPushButton("↺")
            self.reset_timer_btn.setToolTip("Reset Timer")
            self.reset_timer_btn.setFixedWidth(28)
            self.reset_timer_btn.clicked.connect(self._reset_timer)

            header_layout.addWidget(self.timer_lbl)
            header_layout.addWidget(self.timer_btn)
            header_layout.addWidget(self.reset_timer_btn)

        layout.addLayout(header_layout)

        # Body: Instruction text
        self.instruction_lbl = QLabel(self.step.instruction)
        self.instruction_lbl.setWordWrap(True)
        self.instruction_lbl.setStyleSheet("color: #d0d0d0; font-size: 12px; line-height: 1.4;")
        layout.addWidget(self.instruction_lbl)

        # Footer: Optional Notes
        notes_layout = QHBoxLayout()
        notes_lbl = QLabel("Notes:")
        notes_lbl.setStyleSheet("color: #888888; font-size: 11px;")
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Record observations, yields, or tube labels...")
        self.notes_input.setText(self.step.notes)
        self.notes_input.setStyleSheet("""
            QLineEdit {
                background-color: #181818;
                border: 1px solid #2b2b2b;
                border-radius: 3px;
                color: #cfcfcf;
                padding: 3px 6px;
                font-size: 11px;
            }
        """)
        self.notes_input.textChanged.connect(self._handle_notes_changed)

        notes_layout.addWidget(notes_lbl)
        notes_layout.addWidget(self.notes_input)
        layout.addLayout(notes_layout)

    def _handle_toggle(self, checked: bool):
        self.step.is_completed = checked
        self.setProperty("completed", "true" if checked else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        if self.on_step_toggled:
            self.on_step_toggled()

    def _handle_notes_changed(self, text: str):
        self.step.notes = text.strip()

    def _format_time(self, secs: int) -> str:
        mins, s = divmod(secs, 60)
        hrs, mins = divmod(mins, 60)
        if hrs > 0:
            return f"⏱ {hrs:02d}:{mins:02d}:{s:02d}"
        return f"⏱ {mins:02d}:{s:02d}"

    def _toggle_timer(self):
        if self.is_timer_running:
            self.timer.stop()
            self.is_timer_running = False
            self.timer_btn.setText("▶ Resume")
        else:
            if self.remaining_seconds <= 0:
                self.remaining_seconds = self.step.duration_seconds
            self.timer.start()
            self.is_timer_running = True
            self.timer_btn.setText("⏸ Pause")

    def _reset_timer(self):
        self.timer.stop()
        self.is_timer_running = False
        self.remaining_seconds = self.step.duration_seconds or 0
        if hasattr(self, 'timer_lbl'):
            self.timer_lbl.setText(self._format_time(self.remaining_seconds))
            self.timer_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #00ffcc; padding-right: 6px;")
        if hasattr(self, 'timer_btn'):
            self.timer_btn.setText("▶ Start Timer")

    def _timer_tick(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.timer_lbl.setText(self._format_time(self.remaining_seconds))
        else:
            self.timer.stop()
            self.is_timer_running = False
            self.timer_lbl.setText("🔔 DONE!")
            self.timer_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #ff3366; padding-right: 6px;")
            self.timer_btn.setText("✔ Complete")
            self.checkbox.setChecked(True)
            # Beep alert on Windows
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass


class StepEditorRow(QFrame):
    """Row widget inside the protocol editor for configuring an individual step."""

    def __init__(self, step_num: int, title: str = "", instruction: str = "", 
                 duration_seconds: Optional[int] = None, on_delete=None, on_move_up=None, on_move_down=None, parent=None):
        super().__init__(parent)
        self.on_delete = on_delete
        self.on_move_up = on_move_up
        self.on_move_down = on_move_down

        self.setStyleSheet("""
            StepEditorRow {
                background-color: #202020;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header: Step Number, Title, Reorder & Delete buttons
        top_layout = QHBoxLayout()
        self.step_label = QLabel(f"Step {step_num}:")
        self.step_label.setStyleSheet("font-weight: bold; color: #e29c3d;")
        top_layout.addWidget(self.step_label)

        self.title_input = QLineEdit(title)
        self.title_input.setPlaceholderText("Step Title (e.g. Denaturation, Pour Gel, Add Enzyme)")
        top_layout.addWidget(self.title_input, stretch=1)

        self.up_btn = QPushButton("▲")
        self.up_btn.setFixedSize(26, 26)
        self.up_btn.setToolTip("Move Step Up")
        self.up_btn.clicked.connect(lambda: self.on_move_up(self) if self.on_move_up else None)
        top_layout.addWidget(self.up_btn)

        self.down_btn = QPushButton("▼")
        self.down_btn.setFixedSize(26, 26)
        self.down_btn.setToolTip("Move Step Down")
        self.down_btn.clicked.connect(lambda: self.on_move_down(self) if self.on_move_down else None)
        top_layout.addWidget(self.down_btn)

        self.del_btn = QPushButton("🗑")
        self.del_btn.setFixedSize(26, 26)
        self.del_btn.setToolTip("Delete Step")
        self.del_btn.setStyleSheet("color: #ff5555;")
        self.del_btn.clicked.connect(lambda: self.on_delete(self) if self.on_delete else None)
        top_layout.addWidget(self.del_btn)

        layout.addLayout(top_layout)

        # Instruction Text
        self.instruction_input = QTextEdit()
        self.instruction_input.setPlaceholderText("Detailed instructions for this step...")
        self.instruction_input.setPlainText(instruction)
        self.instruction_input.setFixedHeight(50)
        self.instruction_input.setStyleSheet("background-color: #161616; border: 1px solid #2a2a2a; border-radius: 3px;")
        layout.addWidget(self.instruction_input)

        # Timer Settings
        timer_layout = QHBoxLayout()
        self.timer_chk = QCheckBox("Requires Incubation Timer")
        total_sec = duration_seconds or 0
        mins, secs = divmod(total_sec, 60)
        self.timer_chk.setChecked(total_sec > 0)

        timer_layout.addWidget(self.timer_chk)
        timer_layout.addSpacing(10)

        timer_layout.addWidget(QLabel("Minutes:"))
        self.min_spin = QSpinBox()
        self.min_spin.setRange(0, 360)
        self.min_spin.setValue(mins)
        self.min_spin.setFixedWidth(65)
        self.min_spin.setEnabled(self.timer_chk.isChecked())
        timer_layout.addWidget(self.min_spin)

        timer_layout.addWidget(QLabel("Seconds:"))
        self.sec_spin = QSpinBox()
        self.sec_spin.setRange(0, 59)
        self.sec_spin.setValue(secs)
        self.sec_spin.setFixedWidth(55)
        self.sec_spin.setEnabled(self.timer_chk.isChecked())
        timer_layout.addWidget(self.sec_spin)

        timer_layout.addStretch()
        layout.addLayout(timer_layout)

        self.timer_chk.toggled.connect(self.min_spin.setEnabled)
        self.timer_chk.toggled.connect(self.sec_spin.setEnabled)

    def set_step_num(self, num: int):
        self.step_label.setText(f"Step {num}:")

    def get_step_data(self, step_num: int) -> ProtocolStep:
        title = self.title_input.text().strip() or f"Step {step_num}"
        instruction = self.instruction_input.toPlainText().strip()
        duration = None
        if self.timer_chk.isChecked():
            duration = self.min_spin.value() * 60 + self.sec_spin.value()
            if duration <= 0:
                duration = None
        return ProtocolStep(
            step_num=step_num,
            title=title,
            instruction=instruction,
            duration_seconds=duration
        )


class ProtocolEditorDialog(QDialog):
    """Modal dialog for creating a brand-new protocol or editing an existing protocol."""

    def __init__(self, protocol: Optional[Protocol] = None, parent=None):
        super().__init__(parent)
        self.protocol_to_edit = protocol
        self.setWindowTitle("Edit Protocol" if protocol else "➕ Create New Protocol")
        self.resize(650, 600)
        self.setMinimumSize(550, 480)

        self.step_rows: List[StepEditorRow] = []

        self.init_ui()
        if protocol:
            self.load_from_protocol(protocol)
        else:
            # Default first empty step
            self.add_step_row()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Metadata GroupBox
        meta_group = QGroupBox("Protocol Overview")
        meta_layout = QVBoxLayout(meta_group)
        meta_layout.setSpacing(8)

        # Name row
        name_layout = QHBoxLayout()
        name_lbl = QLabel("Protocol Name:*")
        name_lbl.setStyleSheet("font-weight: bold;")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Colony PCR, Plasmid Miniprep, Agarose Gel")
        name_layout.addWidget(name_lbl)
        name_layout.addWidget(self.name_edit, stretch=1)
        meta_layout.addLayout(name_layout)

        # Category and Estimated Time
        cat_time_layout = QHBoxLayout()
        cat_lbl = QLabel("Category:")
        cat_lbl.setStyleSheet("font-weight: bold;")
        self.cat_combo = QComboBox()
        self.cat_combo.setEditable(True)
        self.cat_combo.addItems([
            "PCR & Cloning", "Gels & Electrophoresis", "DNA / RNA Extraction", 
            "Microbiology", "Protein Analysis", "General Lab"
        ])
        cat_time_layout.addWidget(cat_lbl)
        cat_time_layout.addWidget(self.cat_combo, stretch=1)

        time_lbl = QLabel("Est. Time:")
        time_lbl.setStyleSheet("font-weight: bold;")
        self.time_edit = QLineEdit()
        self.time_edit.setPlaceholderText("e.g. 45 min, 2 hr")
        self.time_edit.setFixedWidth(110)
        cat_time_layout.addWidget(time_lbl)
        cat_time_layout.addWidget(self.time_edit)
        meta_layout.addLayout(cat_time_layout)

        # Description
        desc_lbl = QLabel("Brief Description:")
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Optional summary of reagents, conditions, or experiment goal...")
        meta_layout.addWidget(desc_lbl)
        meta_layout.addWidget(self.desc_edit)

        main_layout.addWidget(meta_group)

        # 2. Steps Scroll Area
        steps_header = QHBoxLayout()
        steps_lbl = QLabel("Protocol Steps:")
        steps_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #e29c3d;")
        steps_header.addWidget(steps_lbl)
        steps_header.addStretch()

        self.add_step_btn = QPushButton("➕ Add Step")
        self.add_step_btn.clicked.connect(self.add_step_row)
        steps_header.addWidget(self.add_step_btn)
        main_layout.addLayout(steps_header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: 1px solid #2a2a2a; border-radius: 4px; }")

        self.steps_container = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.setContentsMargins(6, 6, 6, 6)
        self.steps_layout.setSpacing(8)
        self.scroll.setWidget(self.steps_container)

        main_layout.addWidget(self.scroll, stretch=1)

        # 3. Action Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("💾 Save Protocol")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.validate_and_save)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

    def add_step_row(self, title: str = "", instruction: str = "", duration_seconds: Optional[int] = None):
        step_num = len(self.step_rows) + 1
        row = StepEditorRow(
            step_num=step_num,
            title=title,
            instruction=instruction,
            duration_seconds=duration_seconds,
            on_delete=self.delete_step_row,
            on_move_up=self.move_step_up,
            on_move_down=self.move_step_down
        )
        self.step_rows.append(row)
        self.steps_layout.addWidget(row)

    def delete_step_row(self, row: StepEditorRow):
        if len(self.step_rows) <= 1:
            QMessageBox.warning(self, "Step Required", "A protocol must have at least one step.")
            return
        if row in self.step_rows:
            self.step_rows.remove(row)
            self.steps_layout.removeWidget(row)
            row.deleteLater()
            self._renumber_steps()

    def move_step_up(self, row: StepEditorRow):
        idx = self.step_rows.index(row)
        if idx > 0:
            self.step_rows[idx], self.step_rows[idx - 1] = self.step_rows[idx - 1], self.step_rows[idx]
            self._rebuild_steps_layout()

    def move_step_down(self, row: StepEditorRow):
        idx = self.step_rows.index(row)
        if idx < len(self.step_rows) - 1:
            self.step_rows[idx], self.step_rows[idx + 1] = self.step_rows[idx + 1], self.step_rows[idx]
            self._rebuild_steps_layout()

    def _renumber_steps(self):
        for i, r in enumerate(self.step_rows, start=1):
            r.set_step_num(i)

    def _rebuild_steps_layout(self):
        for r in self.step_rows:
            self.steps_layout.removeWidget(r)
        for r in self.step_rows:
            self.steps_layout.addWidget(r)
        self._renumber_steps()

    def load_from_protocol(self, proto: Protocol):
        self.name_edit.setText(proto.name)
        self.cat_combo.setCurrentText(proto.category)
        self.time_edit.setText(proto.estimated_time)
        self.desc_edit.setText(proto.description)

        for step in proto.steps:
            self.add_step_row(
                title=step.title,
                instruction=step.instruction,
                duration_seconds=step.duration_seconds
            )

    def validate_and_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Name", "Please enter a Protocol Name.")
            self.name_edit.setFocus()
            return

        if not self.step_rows:
            QMessageBox.warning(self, "No Steps", "Please add at least one step to this protocol.")
            return

        steps = [row.get_step_data(i) for i, row in enumerate(self.step_rows, start=1)]
        proto_id = self.protocol_to_edit.id if self.protocol_to_edit else f"proto_{uuid.uuid4().hex[:8]}"

        self.result_protocol = Protocol(
            id=proto_id,
            name=name,
            category=self.cat_combo.currentText().strip() or "General",
            description=self.desc_edit.text().strip(),
            estimated_time=self.time_edit.text().strip() or "Variable",
            steps=steps
        )
        self.accept()


class ProtocolWidget(QWidget):
    """Full-featured Custom Lab Protocol & Standard Operating Procedure runner."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.protocols: List[Protocol] = load_user_protocols()
        self.current_protocol: Optional[Protocol] = self.protocols[0] if self.protocols else None

        self.init_ui()
        self.refresh_protocol_view()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header with Protocol Switcher and Management Actions
        header_layout = QHBoxLayout()
        title_lbl = QLabel("📋 Lab Protocols & SOP Runner")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #e29c3d;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        self.proto_lbl = QLabel("Active Protocol:")
        self.proto_lbl.setStyleSheet("font-weight: bold; color: #cfcfcf;")
        self.proto_combo = QComboBox()
        self.proto_combo.setFixedWidth(280)
        self.proto_combo.currentIndexChanged.connect(self.on_protocol_selected)

        self.new_proto_btn = QPushButton("➕ New Protocol")
        self.new_proto_btn.setObjectName("primaryBtn")
        self.new_proto_btn.clicked.connect(self.open_new_protocol_dialog)

        self.edit_proto_btn = QPushButton("✏️ Edit")
        self.edit_proto_btn.clicked.connect(self.open_edit_protocol_dialog)

        self.del_proto_btn = QPushButton("🗑️ Delete")
        self.del_proto_btn.setStyleSheet("color: #ff5555;")
        self.del_proto_btn.clicked.connect(self.delete_current_protocol)

        self.import_btn = QPushButton("📥 Import...")
        self.import_btn.clicked.connect(self.import_protocol)

        self.export_btn = QPushButton("📤 Export...")
        self.export_btn.clicked.connect(self.export_protocol)

        header_layout.addWidget(self.proto_lbl)
        header_layout.addWidget(self.proto_combo)
        header_layout.addWidget(self.new_proto_btn)
        header_layout.addWidget(self.edit_proto_btn)
        header_layout.addWidget(self.del_proto_btn)
        header_layout.addWidget(self.import_btn)
        header_layout.addWidget(self.export_btn)
        main_layout.addLayout(header_layout)

        # 2. Empty State Placeholder Widget
        self.empty_widget = QFrame()
        self.empty_widget.setStyleSheet("""
            QFrame {
                background-color: #212121;
                border: 2px dashed #3a3a3a;
                border-radius: 8px;
                padding: 40px;
            }
        """)
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(14)

        empty_icon = QLabel("📋")
        empty_icon.setStyleSheet("font-size: 48px;")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)

        empty_title = QLabel("No Lab Protocols Added Yet")
        empty_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e29c3d;")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)

        empty_sub = QLabel("You have complete freedom to define, save, and run your custom laboratory SOPs,\nPCR profiles, casting protocols, and bench checklists.")
        empty_sub.setStyleSheet("color: #888888; font-size: 12px; line-height: 1.4;")
        empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_sub)

        empty_btn = QPushButton("➕ Create Your First Protocol")
        empty_btn.setObjectName("primaryBtn")
        empty_btn.setFixedWidth(240)
        empty_btn.clicked.connect(self.open_new_protocol_dialog)
        empty_layout.addWidget(empty_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(self.empty_widget, stretch=1)

        # 3. Active Protocol Execution Container (Visible when a protocol exists)
        self.active_container = QWidget()
        active_layout = QVBoxLayout(self.active_container)
        active_layout.setContentsMargins(0, 0, 0, 0)
        active_layout.setSpacing(12)

        # Metadata & Progress Card
        meta_card = QFrame()
        meta_card.setStyleSheet("background-color: #212121; border: 1px solid #333333; border-radius: 6px; padding: 12px;")
        meta_layout = QVBoxLayout(meta_card)
        meta_layout.setSpacing(8)

        meta_top = QHBoxLayout()
        self.proto_title = QLabel("")
        self.proto_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        meta_top.addWidget(self.proto_title)
        meta_top.addStretch()

        self.time_badge = QLabel("")
        self.time_badge.setStyleSheet("background-color: #333333; color: #00ffcc; padding: 2px 8px; border-radius: 3px; font-weight: bold; font-size: 11px;")
        meta_top.addWidget(self.time_badge)
        meta_layout.addLayout(meta_top)

        self.proto_desc = QLabel("")
        self.proto_desc.setWordWrap(True)
        self.proto_desc.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        meta_layout.addWidget(self.proto_desc)

        # Progress Bar
        prog_layout = QHBoxLayout()
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setFixedHeight(8)
        self.prog_bar.setStyleSheet("""
            QProgressBar {
                background-color: #151515;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #2a9d8f;
                border-radius: 3px;
            }
        """)
        self.prog_lbl = QLabel("0% Complete")
        self.prog_lbl.setStyleSheet("font-weight: bold; font-size: 11px; color: #2a9d8f;")

        prog_layout.addWidget(self.prog_bar)
        prog_layout.addWidget(self.prog_lbl)
        meta_layout.addLayout(prog_layout)

        active_layout.addWidget(meta_card)

        # Step Cards Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.steps_container = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.setContentsMargins(0, 0, 0, 0)
        self.steps_layout.setSpacing(10)

        self.scroll_area.setWidget(self.steps_container)
        active_layout.addWidget(self.scroll_area, stretch=1)

        # Execution Action Bar
        act_layout = QHBoxLayout()
        self.reset_btn = QPushButton("🔄 Reset Progress")
        self.reset_btn.clicked.connect(self.reset_protocol_progress)

        self.copy_btn = QPushButton("📋 Copy Lab Notebook Log")
        self.copy_btn.clicked.connect(self.copy_notebook_log)

        act_layout.addWidget(self.reset_btn)
        act_layout.addStretch()
        act_layout.addWidget(self.copy_btn)
        active_layout.addLayout(act_layout)

        main_layout.addWidget(self.active_container, stretch=1)

    def refresh_protocol_combo(self):
        self.proto_combo.blockSignals(True)
        self.proto_combo.clear()
        for p in self.protocols:
            self.proto_combo.addItem(f"[{p.category}] {p.name}", p.id)
        if self.current_protocol:
            idx = next((i for i, p in enumerate(self.protocols) if p.id == self.current_protocol.id), -1)
            if idx >= 0:
                self.proto_combo.setCurrentIndex(idx)
        self.proto_combo.blockSignals(False)

    def refresh_protocol_view(self):
        has_protocols = bool(self.protocols)

        self.proto_lbl.setVisible(has_protocols)
        self.proto_combo.setVisible(has_protocols)
        self.edit_proto_btn.setVisible(has_protocols)
        self.del_proto_btn.setVisible(has_protocols)
        self.export_btn.setVisible(has_protocols)

        self.empty_widget.setVisible(not has_protocols)
        self.active_container.setVisible(has_protocols)

        self.refresh_protocol_combo()

        if has_protocols:
            if not self.current_protocol or self.current_protocol not in self.protocols:
                self.current_protocol = self.protocols[0]
            self.load_protocol(self.current_protocol)

    def on_protocol_selected(self, idx: int):
        if 0 <= idx < len(self.protocols):
            self.load_protocol(self.protocols[idx])

    def load_protocol(self, proto: Protocol):
        self.current_protocol = proto
        self.proto_title.setText(proto.name)
        self.time_badge.setText(f"Est: {proto.estimated_time}")
        self.proto_desc.setText(proto.description)

        # Clear existing step cards
        while self.steps_layout.count():
            item = self.steps_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Build cards
        for step in proto.steps:
            card = StepCardWidget(step, on_step_toggled=self.update_progress)
            self.steps_layout.addWidget(card)

        self.steps_layout.addStretch()
        self.update_progress()

    def update_progress(self):
        if not self.current_protocol:
            return
        pct = self.current_protocol.get_progress_percent()
        self.prog_bar.setValue(pct)
        done = sum(1 for s in self.current_protocol.steps if s.is_completed)
        total = len(self.current_protocol.steps)
        self.prog_lbl.setText(f"{done}/{total} Steps ({pct}%)")

    def open_new_protocol_dialog(self):
        dialog = ProtocolEditorDialog(protocol=None, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_proto = dialog.result_protocol
            self.protocols.append(new_proto)
            self.current_protocol = new_proto
            save_user_protocols(self.protocols)
            self.refresh_protocol_view()

    def open_edit_protocol_dialog(self):
        if not self.current_protocol:
            return
        dialog = ProtocolEditorDialog(protocol=self.current_protocol, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_proto = dialog.result_protocol
            idx = next((i for i, p in enumerate(self.protocols) if p.id == self.current_protocol.id), -1)
            if idx >= 0:
                self.protocols[idx] = updated_proto
                self.current_protocol = updated_proto
                save_user_protocols(self.protocols)
                self.refresh_protocol_view()

    def delete_current_protocol(self):
        if not self.current_protocol:
            return
        reply = QMessageBox.question(
            self, "Delete Protocol",
            f"Are you sure you want to delete '{self.current_protocol.name}'?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.protocols.remove(self.current_protocol)
            self.current_protocol = self.protocols[0] if self.protocols else None
            save_user_protocols(self.protocols)
            self.refresh_protocol_view()

    def reset_protocol_progress(self):
        if not self.current_protocol:
            return
        reply = QMessageBox.question(
            self, "Reset Protocol",
            "Reset all step checkboxes and timers for this protocol?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.current_protocol.reset_progress()
            self.load_protocol(self.current_protocol)

    def import_protocol(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Protocol (JSON)", "", "JSON Files (*.json)"
        )
        if not file_path:
            return
        proto = import_protocol_from_json(file_path)
        if proto:
            self.protocols.append(proto)
            self.current_protocol = proto
            save_user_protocols(self.protocols)
            self.refresh_protocol_view()
            QMessageBox.information(self, "Import Successful", f"Successfully imported protocol:\n'{proto.name}'")
        else:
            QMessageBox.critical(self, "Import Error", "Failed to parse a valid protocol from the selected file.")

    def export_protocol(self):
        if not self.current_protocol:
            return
        default_filename = f"{self.current_protocol.name.lower().replace(' ', '_')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Protocol (JSON)", default_filename, "JSON Files (*.json)"
        )
        if not file_path:
            return
        if export_protocol_to_json(self.current_protocol, file_path):
            QMessageBox.information(self, "Export Successful", f"Protocol exported to:\n{file_path}")
        else:
            QMessageBox.critical(self, "Export Error", "Failed to export protocol file.")

    def copy_notebook_log(self):
        if not self.current_protocol:
            return
        lines = [
            f"=== LAB PROTOCOL RUN: {self.current_protocol.name} ===",
            f"Category: {self.current_protocol.category} | Est. Duration: {self.current_protocol.estimated_time}",
            f"Completion Status: {self.prog_lbl.text()}",
            "-" * 65
        ]
        for s in self.current_protocol.steps:
            status = "[x] DONE" if s.is_completed else "[ ] PENDING"
            lines.append(f"{status} - Step {s.step_num}: {s.title}")
            lines.append(f"    Details: {s.instruction}")
            if s.notes:
                lines.append(f"    Observation/Notes: {s.notes}")
            lines.append("")
        lines.append("-" * 65)

        text_log = "\n".join(lines)
        clipboard = QApplication.clipboard()
        clipboard.setText(text_log)
        QMessageBox.information(
            self, "Copied to Clipboard",
            "Protocol execution summary copied to clipboard! Ready to paste into your Electronic Lab Notebook (ELN) or report."
        )
