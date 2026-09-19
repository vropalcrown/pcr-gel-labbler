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
from gel_labeler.core.colony_detector import ColonyDetector, ColonyObject


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


if __name__ == "__main__":
    unittest.main()
