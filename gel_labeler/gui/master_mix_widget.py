"""
Interactive Master Mix and PCR/qPCR Reaction Calculator GUI Widget with custom preset persistence.
"""
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, 
    QDoubleSpinBox, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox, QFileDialog, QApplication, QGroupBox,
    QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from gel_labeler.core.master_mix import (
    MasterMixRecipe, MasterMixComponent, STANDARD_PRESETS,
    load_user_master_mixes, save_user_master_mixes
)


class MasterMixWidget(QWidget):
    """Modern interactive widget for calculating PCR/qPCR/Enzyme Master Mixes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_presets = load_user_master_mixes()
        self.recipe = MasterMixRecipe("Custom Mix")
        self._is_updating = False

        self.init_ui()
        self.populate_preset_combo()
        first_std = list(STANDARD_PRESETS.keys())[0] if STANDARD_PRESETS else None
        if first_std:
            self.load_preset_by_recipe(STANDARD_PRESETS[first_std])

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header & Preset Selector
        header_layout = QHBoxLayout()
        title_lbl = QLabel("🧪 Master Mixer — Reaction Recipe Calculator")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #e29c3d;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        preset_lbl = QLabel("Preset:")
        preset_lbl.setStyleSheet("font-weight: bold; color: #cfcfcf;")
        self.preset_combo = QComboBox()
        self.preset_combo.setFixedWidth(320)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)

        self.save_preset_btn = QPushButton("💾 Save Preset")
        self.save_preset_btn.setToolTip("Save the current component recipe as a user preset")
        self.save_preset_btn.clicked.connect(self.save_current_as_preset)
        self.save_preset_btn.setStyleSheet("""
            QPushButton {
                background-color: #233446;
                color: #58a6ff;
                border: 1px solid #388bfd;
                border-radius: 4px;
                padding: 4px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388bfd;
                color: #ffffff;
            }
        """)

        self.del_preset_btn = QPushButton("🗑️")
        self.del_preset_btn.setToolTip("Delete this custom user preset")
        self.del_preset_btn.clicked.connect(self.delete_current_user_preset)
        self.del_preset_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b2225;
                color: #f85149;
                border: 1px solid #da3633;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da3633;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #25282c;
                color: #555555;
                border: 1px solid #333333;
            }
        """)

        header_layout.addWidget(preset_lbl)
        header_layout.addWidget(self.preset_combo)
        header_layout.addWidget(self.save_preset_btn)
        header_layout.addWidget(self.del_preset_btn)
        main_layout.addLayout(header_layout)

        # 2. Reaction Configuration Panel
        config_group = QGroupBox("Reaction Parameters")
        config_layout = QHBoxLayout(config_group)
        config_layout.setSpacing(20)

        # Number of reactions
        rxn_vbox = QVBoxLayout()
        rxn_lbl = QLabel("Number of Samples / Reactions:")
        rxn_lbl.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        self.rxn_spin = QSpinBox()
        self.rxn_spin.setRange(1, 384)
        self.rxn_spin.setValue(8)
        self.rxn_spin.setFixedWidth(90)
        self.rxn_spin.valueChanged.connect(self.on_rxn_changed)
        rxn_vbox.addWidget(rxn_lbl)
        rxn_vbox.addWidget(self.rxn_spin)
        config_layout.addLayout(rxn_vbox)

        # Excess %
        excess_vbox = QVBoxLayout()
        excess_lbl = QLabel("Pipetting Excess Margin (%):")
        excess_lbl.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        self.excess_spin = QDoubleSpinBox()
        self.excess_spin.setRange(0.0, 50.0)
        self.excess_spin.setSingleStep(2.5)
        self.excess_spin.setValue(10.0)
        self.excess_spin.setSuffix("%")
        self.excess_spin.setFixedWidth(90)
        self.excess_spin.valueChanged.connect(self.on_excess_changed)
        excess_vbox.addWidget(excess_lbl)
        excess_vbox.addWidget(self.excess_spin)
        config_layout.addLayout(excess_vbox)

        # Single reaction volume
        vol_vbox = QVBoxLayout()
        vol_lbl = QLabel("Target 1x Rxn Volume (µL):")
        vol_lbl.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        self.vol_spin = QDoubleSpinBox()
        self.vol_spin.setRange(5.0, 1000.0)
        self.vol_spin.setSingleStep(5.0)
        self.vol_spin.setValue(50.0)
        self.vol_spin.setSuffix(" µL")
        self.vol_spin.setFixedWidth(100)
        self.vol_spin.valueChanged.connect(self.on_total_vol_changed)
        vol_vbox.addWidget(vol_lbl)
        vol_vbox.addWidget(self.vol_spin)
        config_layout.addLayout(vol_vbox)

        # Effective multiplier readout
        config_layout.addStretch()
        self.multiplier_lbl = QLabel("Scale: 8.80x")
        self.multiplier_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #00ffcc; padding-top: 10px;")
        config_layout.addWidget(self.multiplier_lbl)

        main_layout.addWidget(config_group)

        # 3. Component Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Component Name", "1x Volume (µL)", "In Master Mix?", "Total Master Mix (µL)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellChanged.connect(self.on_table_cell_changed)
        main_layout.addWidget(self.table)

        # 4. Table Controls & Action Buttons
        btn_layout = QHBoxLayout()

        self.add_comp_btn = QPushButton("➕ Add Component")
        self.add_comp_btn.clicked.connect(self.add_custom_component)
        self.del_comp_btn = QPushButton("🗑 Remove Selected")
        self.del_comp_btn.clicked.connect(self.remove_selected_component)

        btn_layout.addWidget(self.add_comp_btn)
        btn_layout.addWidget(self.del_comp_btn)
        btn_layout.addStretch()

        self.copy_btn = QPushButton("📋 Copy Bench Recipe")
        self.copy_btn.setToolTip("Copy formatted bench card to clipboard for lab notebook or protocol documentation")
        self.copy_btn.clicked.connect(self.copy_recipe_to_clipboard)

        self.export_csv_btn = QPushButton("📊 Export CSV...")
        self.export_csv_btn.clicked.connect(self.export_csv)

        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.export_csv_btn)
        main_layout.addLayout(btn_layout)

        # 5. Summary Banner
        self.summary_box = QGroupBox("Master Mix Preparation Instructions")
        summary_layout = QHBoxLayout(self.summary_box)
        
        self.summary_text_lbl = QLabel("")
        self.summary_text_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        summary_layout.addWidget(self.summary_text_lbl)
        
        main_layout.addWidget(self.summary_box)

    def populate_preset_combo(self, select_preset_name: Optional[str] = None):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()

        # 1. Standard Presets
        for name in STANDARD_PRESETS.keys():
            self.preset_combo.addItem(f"⭐ {name}", userData=("standard", name))

        # 2. User Presets
        if self.user_presets:
            for name in sorted(self.user_presets.keys()):
                self.preset_combo.addItem(f"👤 {name}", userData=("user", name))

        # 3. Custom Scratchpad
        self.preset_combo.addItem("✏️ Custom Recipe", userData=("custom", "Custom Recipe"))

        target_index = 0
        if select_preset_name:
            for i in range(self.preset_combo.count()):
                data = self.preset_combo.itemData(i)
                if data and data[1] == select_preset_name:
                    target_index = i
                    break
        self.preset_combo.setCurrentIndex(target_index)
        self.preset_combo.blockSignals(False)
        self.update_preset_button_states()

    def update_preset_button_states(self):
        data = self.preset_combo.currentData()
        if data and data[0] == "user":
            self.del_preset_btn.setEnabled(True)
        else:
            self.del_preset_btn.setEnabled(False)

    def on_preset_changed(self, index: int):
        data = self.preset_combo.itemData(index)
        if not data:
            return
        tag, name = data
        if tag == "standard" and name in STANDARD_PRESETS:
            self.load_preset_by_recipe(STANDARD_PRESETS[name])
        elif tag == "user" and name in self.user_presets:
            self.load_preset_by_recipe(self.user_presets[name])
        elif tag == "custom":
            pass
        self.update_preset_button_states()

    def load_preset_by_recipe(self, preset: MasterMixRecipe):
        comps = [
            MasterMixComponent(
                c.name, c.vol_per_rxn, c.in_master_mix, c.is_water
            ) for c in preset.components
        ]
        self.recipe = MasterMixRecipe(
            name=preset.name,
            total_rxn_volume=preset.total_rxn_volume,
            num_reactions=self.rxn_spin.value(),
            excess_percent=self.excess_spin.value(),
            components=comps
        )
        self.vol_spin.blockSignals(True)
        self.vol_spin.setValue(self.recipe.total_rxn_volume)
        self.vol_spin.blockSignals(False)
        self.refresh_table()

    def save_current_as_preset(self):
        current_data = self.preset_combo.currentData()
        default_name = ""
        if current_data:
            tag, name = current_data
            if tag == "user":
                default_name = name
            elif tag == "standard":
                default_name = f"{name} (Custom)"
            else:
                default_name = "My Master Mix"

        name, ok = QInputDialog.getText(
            self, "Save Master Mix Preset",
            "Preset Name:",
            text=default_name
        )
        if not ok or not name.strip():
            return

        name = name.strip()

        if name in STANDARD_PRESETS:
            QMessageBox.warning(
                self, "Cannot Overwrite Built-in",
                f"'{name}' is a built-in standard preset name. Please choose a different name for your custom preset."
            )
            return

        if name in self.user_presets:
            reply = QMessageBox.question(
                self, "Overwrite Preset?",
                f"A user preset named '{name}' already exists. Do you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        comps = [
            MasterMixComponent(
                name=c.name,
                vol_per_rxn=c.vol_per_rxn,
                in_master_mix=c.in_master_mix,
                is_water=c.is_water
            ) for c in self.recipe.components
        ]
        saved_recipe = MasterMixRecipe(
            name=name,
            total_rxn_volume=self.vol_spin.value(),
            num_reactions=self.rxn_spin.value(),
            excess_percent=self.excess_spin.value(),
            components=comps
        )

        self.user_presets[name] = saved_recipe
        if save_user_master_mixes(self.user_presets):
            self.populate_preset_combo(select_preset_name=name)
            QMessageBox.information(
                self, "Preset Saved",
                f"Preset '{name}' has been saved to your AppData presets!"
            )
        else:
            QMessageBox.critical(
                self, "Save Error",
                f"Could not save preset '{name}' to AppData."
            )

    def delete_current_user_preset(self):
        current_data = self.preset_combo.currentData()
        if not current_data or current_data[0] != "user":
            return

        name = current_data[1]
        reply = QMessageBox.question(
            self, "Delete Preset",
            f"Are you sure you want to delete user preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if name in self.user_presets:
            del self.user_presets[name]
            save_user_master_mixes(self.user_presets)
            first_std = list(STANDARD_PRESETS.keys())[0] if STANDARD_PRESETS else None
            self.populate_preset_combo(select_preset_name=first_std)
            if first_std:
                self.load_preset_by_recipe(STANDARD_PRESETS[first_std])

    def _switch_to_custom_if_standard(self):
        data = self.preset_combo.currentData()
        if data and data[0] == "standard":
            for i in range(self.preset_combo.count()):
                d = self.preset_combo.itemData(i)
                if d and d[0] == "custom":
                    self.preset_combo.blockSignals(True)
                    self.preset_combo.setCurrentIndex(i)
                    self.preset_combo.blockSignals(False)
                    self.update_preset_button_states()
                    break

    def on_rxn_changed(self, val: int):
        self.recipe.num_reactions = val
        self.refresh_table()

    def on_excess_changed(self, val: float):
        self.recipe.excess_percent = val
        self.refresh_table()

    def on_total_vol_changed(self, val: float):
        self.recipe.total_rxn_volume = val
        self.recipe.calculate_water_volume()
        self.refresh_table()

    def refresh_table(self):
        self._is_updating = True
        self.recipe.calculate_water_volume()
        rows = self.recipe.get_summary_rows()

        self.table.setRowCount(len(rows))
        for row_idx, r in enumerate(rows):
            # 0: Component Name
            item_name = QTableWidgetItem(r["component"])
            if self.recipe.components[row_idx].is_water:
                item_name.setForeground(QColor("#00ffcc"))
            self.table.setItem(row_idx, 0, item_name)

            # 1: 1x Volume
            item_vol = QTableWidgetItem(f"{r['vol_1x']:.2f}")
            item_vol.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 1, item_vol)

            # 2: In Master Mix? (Checkbox item)
            item_chk = QTableWidgetItem("Yes" if r["in_mm"] else "No")
            item_chk.setCheckState(Qt.CheckState.Checked if r["in_mm"] else Qt.CheckState.Unchecked)
            self.table.setItem(row_idx, 2, item_chk)

            # 3: Total Master Mix Volume (Read-only calculated)
            mm_text = f"{r['total_mm_vol']:.2f} µL" if r["in_mm"] else "— (Individual)"
            item_mm = QTableWidgetItem(mm_text)
            item_mm.setFlags(item_mm.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_mm.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if r["in_mm"]:
                item_mm.setForeground(QColor("#e29c3d"))
                f = item_mm.font()
                f.setBold(True)
                item_mm.setFont(f)
            else:
                item_mm.setForeground(QColor("#777777"))
            self.table.setItem(row_idx, 3, item_mm)

        self._is_updating = False

        # Update multiplier readout
        n = self.recipe.num_reactions
        mult = self.recipe.total_multiplier
        exc = self.recipe.excess_percent
        self.multiplier_lbl.setText(f"Batch Multiplier: {mult:.2f}x ({n} rxns + {exc:.0f}% margin)")

        # Update summary banner
        total_mm = sum(r["total_mm_vol"] for r in rows if r["in_mm"])
        mm_aliquot = sum(r["vol_1x"] for r in rows if r["in_mm"])
        indiv_aliquot = sum(r["vol_1x"] for r in rows if not r["in_mm"])

        self.summary_text_lbl.setText(
            f"🧪 Prepare <b>{total_mm:.2f} µL</b> in one master mix tube. "
            f"Dispense <b>{mm_aliquot:.2f} µL</b> Master Mix per reaction tube, "
            f"then add <b>{indiv_aliquot:.2f} µL</b> of individual sample/template."
        )

    def on_table_cell_changed(self, row: int, col: int):
        if self._is_updating or row >= len(self.recipe.components):
            return

        comp = self.recipe.components[row]
        item = self.table.item(row, col)
        if not item:
            return

        self._switch_to_custom_if_standard()

        if col == 0:
            comp.name = item.text().strip()
        elif col == 1:
            try:
                comp.vol_per_rxn = max(0.0, float(item.text().strip()))
            except ValueError:
                pass
        elif col == 2:
            comp.in_master_mix = (item.checkState() == Qt.CheckState.Checked)

        self.refresh_table()

    def add_custom_component(self):
        self._switch_to_custom_if_standard()
        new_comp = MasterMixComponent(name="New Component", vol_per_rxn=1.0)
        self.recipe.components.append(new_comp)
        self.refresh_table()

    def remove_selected_component(self):
        current_row = self.table.currentRow()
        if current_row >= 0 and current_row < len(self.recipe.components):
            self._switch_to_custom_if_standard()
            del self.recipe.components[current_row]
            self.refresh_table()

    def copy_recipe_to_clipboard(self):
        text_card = self.recipe.format_as_text_card()
        clipboard = QApplication.clipboard()
        clipboard.setText(text_card)
        QMessageBox.information(
            self, "Copied to Clipboard",
            "Master mix recipe copied to clipboard! You can paste it directly into your lab notebook, electronic protocol, or messages."
        )

    def export_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Master Mix Recipe to CSV", "master_mix_recipe.csv",
            "CSV Spreadsheet (*.csv)"
        )
        if not file_path:
            return
        try:
            csv_text = self.recipe.export_to_csv()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(csv_text)
            QMessageBox.information(self, "Export Successful", f"Recipe exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV: {e}")
