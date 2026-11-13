import os
import sys
import tempfile
import json
import unittest

# Ensure gel_labeler is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gel_labeler.core.pattern_parser import parse_label_pattern
from gel_labeler.core.project import GelProject
from gel_labeler.core.label import GelLabel
from gel_labeler.core.colony_detector import ColonyDetector


class TestAuditRemediation(unittest.TestCase):

    def test_pattern_parser_and_resource_capping(self):
        """S9: Test pattern parsing and range safety capping."""
        labels = parse_label_pattern("Ladder, 1-10, P1-P4")
        self.assertEqual(len(labels), 15)
        self.assertEqual(labels[0], "Ladder")
        self.assertEqual(labels[10], "10")
        self.assertEqual(labels[11], "P1")

        # Hostile huge range capping
        large_labels = parse_label_pattern("1-10000")
        self.assertLessEqual(len(large_labels), 500)

    def test_label_rotation_flexibility(self):
        """N6: Test that custom rotation on ladder labels is respected."""
        lbl_horiz = GelLabel("Ladder", 10, 10, rotation=0.0)
        self.assertEqual(lbl_horiz.rotation, 0.0)

        lbl_custom = GelLabel("My ladder marker", 20, 20, rotation=90.0)
        self.assertEqual(lbl_custom.rotation, 90.0)

        lbl_custom.update_style(text="Updated Ladder", rotation=45.0)
        self.assertEqual(lbl_custom.rotation, 45.0)

    def test_csv_formula_injection_neutralization(self):
        """S4/C5: Test DDE / formula injection protection in CSV exports."""
        proj = GelProject()
        proj.add_label("=CMD|' /C calc'!A0", 10, 10, "#FFFFFF", 12, "Arial")
        proj.add_label("+SUM(1,2)", 20, 10, "#FFFFFF", 12, "Arial")
        proj.add_label("-10% discount", 30, 10, "#FFFFFF", 12, "Arial")
        proj.add_label("@evil_ref", 40, 10, "#FFFFFF", 12, "Arial")

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            tmp_path = tf.name

        try:
            proj.export_to_csv(tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("'=CMD", content)
            self.assertIn("'+SUM", content)
            self.assertIn("'-10%", content)
            self.assertIn("'@evil_ref", content)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_export_reading_order(self):
        """N11: Test that exported rows come out in top-to-bottom tier, left-to-right reading order."""
        proj = GelProject()
        # Add labels out of order
        proj.add_label("Tier2-Lane2", 150, 160, "#00FF00", 12, "Arial")
        proj.add_label("Tier1-Lane2", 150, 60, "#00FF00", 12, "Arial")
        proj.add_label("Tier2-Lane1", 50, 160, "#00FF00", 12, "Arial")
        proj.add_label("Tier1-Lane1", 50, 60, "#00FF00", 12, "Arial")

        ordered = proj.get_labels_reading_order()
        texts = [l.text for l in ordered]
        self.assertEqual(texts, ["Tier1-Lane1", "Tier1-Lane2", "Tier2-Lane1", "Tier2-Lane2"])

    def test_json_schema_validation(self):
        """S1 / H10: Test loading corrupted or hostile JSON data."""
        proj = GelProject()

        # 1. Non-dict root
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tf:
            json.dump(["not", "a", "dict"], tf)
            tmp1 = tf.name

        try:
            self.assertFalse(proj.load_from_json(tmp1))
        finally:
            if os.path.exists(tmp1):
                os.remove(tmp1)

        # 2. Missing labels array
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tf:
            json.dump({"image_path": "test.png"}, tf)
            tmp2 = tf.name

        try:
            self.assertFalse(proj.load_from_json(tmp2))
        finally:
            if os.path.exists(tmp2):
                os.remove(tmp2)

    def test_span_segment_perpendicular_distance(self):
        """M5: Test that span mode deletes only labels near the actual line segment, not a broad bounding box."""
        proj = GelProject()
        # Label far away in the bounding box corner but far from the diagonal segment
        proj.add_label("Distant", 10, 190, "#FFFFFF", 12, "Arial")
        # Label directly on the line
        proj.add_label("OnLine", 100, 100, "#FFFFFF", 12, "Arial")

        # Span from (0, 0) to (200, 200)
        proj.generate_span_labels(["S1", "S2", "S3"], 0, 0, 200, 200, "#00FF00", 12)

        active_texts = [l.text for l in proj.get_labels_list()]
        self.assertIn("Distant", active_texts, "Distant label should NOT be deleted by span mode")
        self.assertNotIn("OnLine", active_texts, "OnLine label should be replaced")

    def test_cfu_calculation(self):
        """Test Colony & Seed CFU calculator logic."""
        cfu = ColonyDetector.calculate_cfu(count=150, plated_volume_ml=0.1, dilution_factor=1000.0)
        self.assertEqual(cfu, 1500000.0)

        # Zero volume guard
        self.assertEqual(ColonyDetector.calculate_cfu(count=100, plated_volume_ml=0.0, dilution_factor=1.0), 0.0)

    def test_pattern_parser_spaced_prefixes_and_padding(self):
        """Test space-separated range prefixes and zero-padding behavior."""
        # Space-separated prefix
        labels_spaced = parse_label_pattern("Lane 1 - Lane 5")
        self.assertEqual(labels_spaced, ["Lane 1", "Lane 2", "Lane 3", "Lane 4", "Lane 5"])

        # Zero-padded prefixed range
        labels_padded = parse_label_pattern("L01-L04")
        self.assertEqual(labels_padded, ["L01", "L02", "L03", "L04"])

        # Spaced and padded
        labels_sample = parse_label_pattern("Sample 08 - Sample 11")
        self.assertEqual(labels_sample, ["Sample 08", "Sample 09", "Sample 10", "Sample 11"])

    def test_csv_rotation_export(self):
        """Test that label rotation is preserved in CSV export header and rows."""
        proj = GelProject()
        proj.add_label("Ladder90", 100, 100, "#FFFFFF", 12, "Arial", rotation=90.0)
        proj.add_label("Slanted45", 200, 100, "#FFFFFF", 12, "Arial", rotation=45.0)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            tmp_path = tf.name

        try:
            proj.export_to_csv(tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            header = lines[0].strip().split(",")
            self.assertIn("rotation", header)
            rot_idx = header.index("rotation")

            row1 = lines[1].strip().split(",")
            row2 = lines[2].strip().split(",")
            self.assertEqual(float(row1[rot_idx]), 90.0)
            self.assertEqual(float(row2[rot_idx]), 45.0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_colony_detector_inverted_radius_bounds(self):
        """Test ColonyDetector handles inverted min/max radius gracefully."""
        import numpy as np
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        # min_radius > max_radius should not crash and should normalize
        colonies, dish = ColonyDetector.detect_colonies(img, min_radius=30, max_radius=5)
        self.assertIsInstance(colonies, list)

    def test_project_add_and_undo(self):
        """Test adding individual labels and undoing."""
        proj = GelProject()
        lbl = proj.add_label("Test1", 50, 100, "#FFFFFF", 14, "Arial", 0.0)
        self.assertEqual(len(proj.labels), 1)
        self.assertEqual(proj.labels[lbl.id].text, "Test1")
        self.assertTrue(proj.is_dirty)

        # Undo should revert
        self.assertTrue(proj.undo())
        self.assertEqual(len(proj.labels), 0)

    def test_on_selected_label_dragged_signature(self):
        """Test that MainWindow has the on_selected_label_dragged method matching label_item callback."""
        from gel_labeler.gui.main_window import MainWindow
        self.assertTrue(hasattr(MainWindow, "on_selected_label_dragged"))

    def test_master_mix_calculations(self):
        """Test MasterMixRecipe calculation, water auto-balancing, and CSV export."""
        from gel_labeler.core.master_mix import MasterMixRecipe, MasterMixComponent
        recipe = MasterMixRecipe(
            name="Test Taq",
            total_rxn_volume=50.0,
            num_reactions=10,
            excess_percent=10.0,  # 10 rxns + 10% = 11.0x multiplier
            components=[
                MasterMixComponent("Buffer", vol_per_rxn=5.0, in_master_mix=True),
                MasterMixComponent("dNTPs", vol_per_rxn=1.0, in_master_mix=True),
                MasterMixComponent("Water", vol_per_rxn=0.0, in_master_mix=True, is_water=True),
                MasterMixComponent("Template", vol_per_rxn=2.0, in_master_mix=False)
            ]
        )
        self.assertAlmostEqual(recipe.total_multiplier, 11.0)
        water_vol = recipe.calculate_water_volume()
        self.assertAlmostEqual(water_vol, 42.0)  # 50 - (5 + 1 + 2) = 42

        rows = recipe.get_summary_rows()
        buffer_row = next(r for r in rows if r["component"] == "Buffer")
        self.assertAlmostEqual(buffer_row["total_mm_vol"], 55.0)  # 5.0 * 11

        template_row = next(r for r in rows if r["component"] == "Template")
        self.assertAlmostEqual(template_row["total_mm_vol"], 0.0)  # Excluded from MM tube

        csv_text = recipe.export_to_csv()
        self.assertIn("Test Taq", csv_text)
        self.assertIn("Buffer", csv_text)

        # Test to_dict and from_dict
        d = recipe.to_dict()
        rebuilt = MasterMixRecipe.from_dict(d)
        self.assertEqual(rebuilt.name, "Test Taq")
        self.assertEqual(len(rebuilt.components), 4)
        self.assertEqual(rebuilt.components[0].name, "Buffer")
        self.assertAlmostEqual(rebuilt.components[0].vol_per_rxn, 5.0)

    def test_master_mix_persistence(self):
        """Test user master mix dictionary saving and loading to temporary json."""
        from gel_labeler.core.master_mix import MasterMixRecipe, MasterMixComponent
        presets = {
            "Custom Mix 1": MasterMixRecipe(
                name="Custom Mix 1",
                total_rxn_volume=25.0,
                num_reactions=16,
                excess_percent=15.0,
                components=[
                    MasterMixComponent("Primer F", vol_per_rxn=1.0, in_master_mix=True),
                    MasterMixComponent("Water", vol_per_rxn=24.0, in_master_mix=True, is_water=True)
                ]
            )
        }
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tf:
            json.dump({k: v.to_dict() for k, v in presets.items()}, tf)
            tmp_path = tf.name

        try:
            with open(tmp_path, "r", encoding="utf-8") as f:
                loaded_raw = json.load(f)
            loaded = {k: MasterMixRecipe.from_dict(v) for k, v in loaded_raw.items()}
            self.assertIn("Custom Mix 1", loaded)
            self.assertEqual(loaded["Custom Mix 1"].num_reactions, 16)
            self.assertAlmostEqual(loaded["Custom Mix 1"].excess_percent, 15.0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_protocol_engine(self):
        """Test Protocol step completion, progress calculation, and reset."""
        from gel_labeler.core.protocol import (
            Protocol, ProtocolStep, STANDARD_PROTOCOLS,
            export_protocol_to_json, import_protocol_from_json
        )
        # Verify no hardcoded protocols exist
        self.assertEqual(len(STANDARD_PROTOCOLS), 0)

        proto = Protocol(
            id="test_proto",
            name="Test Protocol",
            category="Testing",
            description="Unit test protocol",
            estimated_time="10 min",
            steps=[
                ProtocolStep(1, "Step 1", "Instruction 1", duration_seconds=120),
                ProtocolStep(2, "Step 2", "Instruction 2"),
                ProtocolStep(3, "Step 3", "Instruction 3"),
                ProtocolStep(4, "Step 4", "Instruction 4")
            ]
        )
        self.assertEqual(proto.get_progress_percent(), 0)
        proto.steps[0].is_completed = True
        self.assertEqual(proto.get_progress_percent(), 25)
        proto.steps[1].is_completed = True
        self.assertEqual(proto.get_progress_percent(), 50)
        proto.reset_progress()
        self.assertEqual(proto.get_progress_percent(), 0)

        # Test export and import
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            tmp_export = tf.name

        try:
            success = export_protocol_to_json(proto, tmp_export)
            self.assertTrue(success)

            imported = import_protocol_from_json(tmp_export)
            self.assertIsNotNone(imported)
            self.assertEqual(imported.name, "Test Protocol")
            self.assertEqual(len(imported.steps), 4)
            self.assertEqual(imported.steps[0].duration_seconds, 120)
        finally:
            if os.path.exists(tmp_export):
                os.remove(tmp_export)

    def test_plate_grid_and_coordinates(self):
        """Test multiwell plate row letters, well coordinates, and parsing."""
        from gel_labeler.core.plate import (
            row_index_to_letter, row_letter_to_index,
            make_well_id, parse_well_id
        )
        self.assertEqual(row_index_to_letter(0), "A")
        self.assertEqual(row_index_to_letter(7), "H")
        self.assertEqual(row_index_to_letter(25), "Z")
        self.assertEqual(row_index_to_letter(26), "AA")

        self.assertEqual(row_letter_to_index("A"), 0)
        self.assertEqual(row_letter_to_index("H"), 7)
        self.assertEqual(row_letter_to_index("Z"), 25)

        self.assertEqual(make_well_id(0, 0), "A1")
        self.assertEqual(make_well_id(7, 11), "H12")
        self.assertEqual(make_well_id(15, 23), "P24")

        self.assertEqual(parse_well_id("A1"), (0, 0))
        self.assertEqual(parse_well_id("H12"), (7, 11))
        self.assertEqual(parse_well_id("P24"), (15, 23))

    def test_plate_project_operations_and_exports(self):
        """Test PlateProject resize, batch styling, series numbering, CSV exports, and persistence."""
        from gel_labeler.core.plate import (
            PlateProject, export_plate_to_json, import_plate_from_json
        )
        plate = PlateProject(name="Test 96-Well", rows=8, cols=12)
        self.assertEqual(len(plate.wells), 96)
        self.assertEqual(plate.get_stats()["total"], 96)
        self.assertEqual(plate.get_stats()["filled"], 0)

        # Batch apply
        well_ids = ["A1", "A2", "A3", "A4"]
        plate.apply_batch(well_ids, title="Control", role="Control", color="#16a34a")
        self.assertEqual(plate.get_stats()["filled"], 4)
        self.assertEqual(plate.get_stats()["Control"], 4)

        # Series numbering
        sample_ids = ["B1", "B2", "B3", "B4"]
        plate.apply_series(sample_ids, prefix="Drug", start_num=1, pad=2, role="Sample", color="#2563eb")
        self.assertEqual(plate.get_well(1, 0).title, "Drug 01")
        self.assertEqual(plate.get_well(1, 3).title, "Drug 04")
        self.assertEqual(plate.get_well(1, 0).role, "Sample")

        # Test formula injection protection in CSV exports
        plate.apply_batch(["C1"], title="=CMD|' /C calc'!A0", role="Sample")
        matrix_csv = plate.export_matrix_csv()
        self.assertIn("'=CMD", matrix_csv)

        table_csv = plate.export_table_csv()
        self.assertIn("'=CMD", table_csv)
        self.assertIn("Drug 01", table_csv)

        # Test resize
        plate.resize(4, 6)
        self.assertEqual(plate.rows, 4)
        self.assertEqual(plate.cols, 6)
        self.assertEqual(len(plate.wells), 24)
        self.assertEqual(plate.get_well(0, 0).title, "Control")

        # Test JSON export and import
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            tmp_plate = tf.name

        try:
            self.assertTrue(export_plate_to_json(plate, tmp_plate))
            loaded = import_plate_from_json(tmp_plate)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.name, "Test 96-Well")
            self.assertEqual(loaded.rows, 4)
            self.assertEqual(loaded.cols, 6)
            self.assertEqual(loaded.get_well(0, 0).title, "Control")
        finally:
            if os.path.exists(tmp_plate):
                os.remove(tmp_plate)

    def test_updater_version_comparison(self):
        """Test semantic version parsing and newer release detection."""
        from gel_labeler.core.updater import parse_version_string, is_version_newer

        self.assertEqual(parse_version_string("v1.0.0"), (1, 0, 0))
        self.assertEqual(parse_version_string("1.2.3"), (1, 2, 3))
        self.assertEqual(parse_version_string("v2.0-beta"), (2, 0))
        self.assertEqual(parse_version_string(""), (0, 0, 0))

        # Newer version tests
        self.assertTrue(is_version_newer("v1.0.1", "1.0.0"))
        self.assertTrue(is_version_newer("1.1.0", "1.0.9"))
        self.assertTrue(is_version_newer("v2.0.0", "1.9.9"))

        # Same or older tests
        self.assertFalse(is_version_newer("1.0.0", "1.0.0"))
        self.assertFalse(is_version_newer("v1.0.0", "1.0.0"))
        self.assertFalse(is_version_newer("v0.9.9", "1.0.0"))
        self.assertFalse(is_version_newer("1.0.0", "1.0.1"))


if __name__ == "__main__":
    unittest.main()

