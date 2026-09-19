import json
import csv
import os
import re
import time
import math
import logging
from typing import Dict, List, Optional
import cv2
import numpy as np
from PyQt6.QtGui import QImage, QTransform
from PyQt6.QtCore import QPointF, QRectF, Qt
from gel_labeler.core.label import GelLabel

logger = logging.getLogger("gel_labeler")

class GelProject:
    """Manages the current gel image state and its labels.
    
    Provides capabilities for loading/saving label configurations, exporting to CSV,
    and tracking image file paths.
    """
    
    def __init__(self):
        self.image_path: Optional[str] = None
        self.labels: Dict[str, GelLabel] = {}
        self.image_width: int = 0
        self.image_height: int = 0
        self.is_dirty: bool = False  # Track unsaved changes
        self.undo_stack: List[List[dict]] = []
        self._in_batch_operation: bool = False
        self.gray_data: Optional[np.ndarray] = None

    def reset(self):
        """Resets the project state."""
        self.image_path = None
        self.labels.clear()
        self.image_width = 0
        self.image_height = 0
        self.is_dirty = False
        self.undo_stack.clear()
        self._in_batch_operation = False
        self.gray_data = None

    def save_undo_state(self):
        """Saves the current label states to the undo stack."""
        if self._in_batch_operation:
            return
        if len(self.undo_stack) >= 50:
            self.undo_stack.pop(0)
        # Deep copy/serialize current labels
        state = [label.to_dict() for label in self.labels.values()]
        # Also store image_path and dimensions in the state metadata
        self.undo_stack.append({
            "labels": state,
            "image_path": self.image_path,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "is_dirty": self.is_dirty
        })

    def undo(self) -> bool:
        """Restores the previous state from the undo stack."""
        if not self.undo_stack:
            return False
        state_data = self.undo_stack.pop()
        
        # If stack contains old format (just label lists), handle it
        if isinstance(state_data, list):
            self.labels.clear()
            for label_data in state_data:
                label = GelLabel.from_dict(label_data)
                self.labels[label.id] = label
            self.is_dirty = True
        else:
            self.labels.clear()
            for label_data in state_data.get("labels", []):
                label = GelLabel.from_dict(label_data)
                self.labels[label.id] = label
            old_path = self.image_path
            self.image_path = state_data.get("image_path")
            self.image_width = state_data.get("image_width", self.image_width)
            self.image_height = state_data.get("image_height", self.image_height)
            self.is_dirty = state_data.get("is_dirty", True)
            
            # If path changed during undo (e.g. rotated back), reload gray data
            if self.image_path != old_path:
                if self.image_path:
                    self.gray_data = cv2.imread(self.image_path, cv2.IMREAD_GRAYSCALE)
                else:
                    self.gray_data = None
            
        return True

    def load_image(self, path: str, width: int, height: int):
        """Loads a new gel image and sets its original dimensions."""
        self.image_path = path
        self.image_width = width
        self.image_height = height
        self.labels.clear()
        self.is_dirty = False
        self.gray_data = cv2.imread(path, cv2.IMREAD_GRAYSCALE)

    def rotate_image(self, angle_deg: float) -> bool:
        """Rotates the background image and maps label coordinates to the new rotated space.
        
        Saves the rotated image to a uniquely named file without overwriting source images.
        Returns True if rotation succeeded, False otherwise.
        """
        if not self.image_path or not os.path.exists(self.image_path):
            return False
            
        image = QImage(self.image_path)
        if image.isNull():
            logger.error(f"Cannot rotate null or invalid image: {self.image_path}")
            return False
            
        transform = QTransform().rotate(angle_deg)
        rotated_image = image.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        if rotated_image.isNull():
            logger.error("Rotation transformed image is null.")
            return False
            
        # Generate non-colliding unique filename
        dir_name = os.path.dirname(self.image_path)
        base_name = os.path.splitext(os.path.basename(self.image_path))[0]
        # Clean any preexisting timestamp suffix to avoid overly long chains
        base_clean = re.sub(r"_rotated_\d{8}_\d{6}_\d+", "", base_name)
        base_clean = re.sub(r"_processed$", "", base_clean)
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        unique_suffix = f"_rotated_{timestamp_str}_{int((time.time() % 1) * 1000):03d}"
        new_path = os.path.join(dir_name, f"{base_clean}{unique_suffix}.png")
        
        # Attempt to save
        if not rotated_image.save(new_path, "PNG"):
            logger.error(f"Failed to save rotated image to {new_path}")
            return False
            
        # Verify saved image can be read by cv2
        new_gray = cv2.imread(new_path, cv2.IMREAD_GRAYSCALE)
        if new_gray is None:
            logger.error(f"Saved rotated image could not be loaded back by cv2: {new_path}")
            try:
                os.remove(new_path)
            except Exception:
                pass
            return False

        self.save_undo_state()
        
        # Map existing labels
        rect = QRectF(0, 0, self.image_width, self.image_height)
        rotated_rect = transform.mapRect(rect)
        tx = -rotated_rect.left()
        ty = -rotated_rect.top()
        
        for label in self.labels.values():
            p = transform.map(QPointF(label.x, label.y))
            label.update_position(p.x() + tx, p.y() + ty)
            
        self.image_path = new_path
        self.image_width = rotated_image.width()
        self.image_height = rotated_image.height()
        self.gray_data = new_gray
        self.is_dirty = True
        return True


    def add_label(self, text: str, x: float, y: float, 
                  color: str, font_size: int, font_family: str, rotation: float = 0.0) -> GelLabel:
        """Creates and adds a new GelLabel to the project."""
        self.save_undo_state()
        label = GelLabel(text, x, y, color, font_size, font_family, rotation)
        self.labels[label.id] = label
        self.is_dirty = True
        return label

    def remove_label(self, label_id: str) -> bool:
        """Removes a label by its unique ID."""
        if label_id in self.labels:
            self.save_undo_state()
            del self.labels[label_id]
            self.is_dirty = True
            return True
        return False

    def get_labels_list(self) -> List[GelLabel]:
        """Returns the list of active labels."""
        return list(self.labels.values())

    def clear_labels(self):
        """Clears all labels from the project."""
        if self.labels:
            self.save_undo_state()
            self.labels.clear()
            self.is_dirty = True

    def get_labels_reading_order(self) -> List[GelLabel]:
        """Returns labels sorted in natural reading order (top-to-bottom tier, left-to-right lane)."""
        return sorted(self.labels.values(), key=lambda l: (round(l.y / 20.0), l.x))

    def to_dict(self) -> dict:
        """Serializes the project configuration."""
        return {
            "image_path": self.image_path,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "labels": [label.to_dict() for label in self.get_labels_reading_order()]
        }

    def save_to_json(self, file_path: str):
        """Saves label data to a JSON file."""
        data = self.to_dict()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        self.is_dirty = False

    def load_from_json(self, file_path: str) -> bool:
        """Loads label data from a JSON file with schema validation."""
        try:
            if not os.path.exists(file_path):
                logger.error(f"JSON file does not exist: {file_path}")
                return False
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                logger.error("Project JSON root must be an object.")
                return False
                
            labels_raw = data.get("labels")
            if labels_raw is None or not isinstance(labels_raw, list):
                logger.error("Project JSON missing valid 'labels' array.")
                return False
                
            self.save_undo_state()
            self.labels.clear()
            for label_data in labels_raw:
                if isinstance(label_data, dict):
                    label = GelLabel.from_dict(label_data)
                    self.labels[label.id] = label
            
            self.is_dirty = True
            return True
        except Exception as e:
            logger.error(f"Error loading project JSON: {e}", exc_info=True)
            return False

    @staticmethod
    def sanitize_csv_cell(val) -> str:
        """Neutralizes CSV / Excel Formula Injection (DDE).
        
        If a string begins with =, +, -, @, \t, or \r, prepends a single quote (').
        """
        if val is None:
            return ""
        s = str(val)
        if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
            return f"'{s}"
        return s

    def export_to_csv(self, file_path: str):
        """Exports the labels database to a CSV file in reading order with DDE formula injection neutralization."""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write Header
            writer.writerow(["label_id", "text", "pixel_x", "pixel_y", "color", "font_size", "font_family"])
            # Write label rows in natural reading order
            for label in self.get_labels_reading_order():
                writer.writerow([
                    self.sanitize_csv_cell(label.id),
                    self.sanitize_csv_cell(label.text),
                    round(label.x, 2),
                    round(label.y, 2),
                    self.sanitize_csv_cell(label.color),
                    label.font_size,
                    self.sanitize_csv_cell(label.font_family)
                ])

    def generate_grid_from_tiers(self, tiers_config: List[dict],
                                 color: str, font_size: int, rotation: float, font_family: str = "Arial"):
        """Batch generates labels according to tier specifications.
        
        tiers_config is a list of dicts:
        [
            {"name": "Tier 1", "labels": ["Ladder", "1", ...], "y": 60, "x_start": 20, "pitch": 26.5},
            ...
        ]
        """
        self.save_undo_state()
        self._in_batch_operation = True
        try:
            # Clear existing labels first
            self.labels.clear()
            
            for tier in tiers_config:
                labels_list = tier.get("labels", [])
                y = tier.get("y", 60)
                x_start = tier.get("x_start", 20)
                pitch = tier.get("pitch", 26.5)
                xs = tier.get("xs")
                
                for lane_idx, label_text in enumerate(labels_list):
                    # Use exact detected coordinate if available, otherwise calculate uniform grid position
                    if xs and lane_idx < len(xs):
                        x = xs[lane_idx]
                    else:
                        x = x_start + lane_idx * pitch
                    
                    self.add_label(
                        text=label_text,
                        x=x,
                        y=y,
                        color=color,
                        font_size=font_size,
                        rotation=rotation,
                        font_family=font_family
                    )
            self.is_dirty = True
        finally:
            self._in_batch_operation = False

    def generate_span_labels(self, labels: List[str], x1: float, y1: float, x2: float, y2: float, 
                             color: str, font_size: int, rotation: float = 0.0, font_family: str = "Arial"):
        """Generates labels by linearly interpolating between two clicked coordinates (slanted or straight).
        
        Clears existing labels in the span region to prevent overlap.
        """
        self.save_undo_state()
        self._in_batch_operation = True
        try:
            dx = x2 - x1
            dy = y2 - y1
            seg_len_sq = dx * dx + dy * dy
            
            def dist_to_segment(px: float, py: float) -> float:
                if seg_len_sq <= 0:
                    return math.hypot(px - x1, py - y1)
                t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / seg_len_sq))
                proj_x = x1 + t * dx
                proj_y = y1 + t * dy
                return math.hypot(px - proj_x, py - proj_y)

            # Filter out old labels within 30px perpendicular distance to prevent overlap
            self.labels = {
                lid: lbl for lid, lbl in self.labels.items()
                if dist_to_segment(lbl.x, lbl.y) > 30.0
            }
            
            n_labels = len(labels)
            for i, label_text in enumerate(labels):
                t = i / (n_labels - 1) if n_labels > 1 else 0.5
                x = x1 + t * (x2 - x1)
                y = y1 + t * (y2 - y1)
                    
                self.add_label(
                    text=label_text,
                    x=x,
                    y=y,
                    color=color,
                    font_size=font_size,
                    rotation=rotation,
                    font_family=font_family
                )
            self.is_dirty = True
        finally:
            self._in_batch_operation = False

    def generate_ladder_labels(self, bands: List[str], x1: float, y1: float, x2: float, y2: float, 
                               alignment: str, color: str, font_size: int, rotation: float = 0.0, font_family: str = "Arial"):
        """Generates molecular weight labels vertically down a ladder lane.
        
        Aligns the labels to the left or right of the vertical lane to prevent obscuring bands.
        """
        self.save_undo_state()
        self._in_batch_operation = True
        try:
            # Determine X offset to sit neatly next to the bands
            offset_x = -45 if alignment == "Left" else 15
            
            n_bands = len(bands)
            for i, band_text in enumerate(bands):
                t = i / (n_bands - 1) if n_bands > 1 else 0.5
                x = x1 + t * (x2 - x1) + offset_x
                # Shift slightly vertically to center text on the band line
                y = y1 + t * (y2 - y1) - (font_size / 2)
                
                self.add_label(
                    text=band_text,
                    x=x,
                    y=y,
                    color=color,
                    font_size=font_size,
                    rotation=rotation,
                    font_family=font_family
                )
            self.is_dirty = True
        finally:
            self._in_batch_operation = False

    def align_all_labels(self) -> bool:
        """Aligns all horizontal tiers and vertical ladders between their endpoints.
        
        Horizontal tiers are groups of labels with small Y difference.
        Vertical ladders are groups of labels with small X difference.
        """
        self.save_undo_state()
        labels = self.get_labels_list()
        n = len(labels)
        if n < 2:
            return False
            
        # 1. Identify vertical ladders/lanes (sets of 3+ labels with small X difference)
        visited_v = [False] * n
        v_components = []
        
        for i in range(n):
            if visited_v[i]:
                continue
            comp = [i]
            for j in range(n):
                if j != i and not visited_v[j]:
                    if abs(labels[j].x - labels[i].x) < 25:
                        comp.append(j)
            
            if len(comp) >= 3:
                xs = [labels[idx].x for idx in comp]
                ys = [labels[idx].y for idx in comp]
                x_span = max(xs) - min(xs)
                y_span = max(ys) - min(ys)
                if y_span > 2.0 * x_span:
                    v_components.append(comp)
                    for idx in comp:
                        visited_v[idx] = True
                        
        # 2. Group the remaining pool of labels by Y coordinate into horizontal tiers
        remaining_indices = [i for i in range(n) if not visited_v[i]]
        h_components = []
        if remaining_indices:
            remaining_indices.sort(key=lambda idx: labels[idx].y)
            
            current_comp = [remaining_indices[0]]
            for idx in remaining_indices[1:]:
                if labels[idx].y - labels[current_comp[-1]].y < 50:
                    current_comp.append(idx)
                else:
                    if len(current_comp) >= 2:
                        h_components.append(current_comp)
                    current_comp = [idx]
            if len(current_comp) >= 2:
                h_components.append(current_comp)
                
        modified = False
        
        # Process horizontal components
        for comp in h_components:
            comp.sort(key=lambda idx: labels[idx].x)
            first_lbl = labels[comp[0]]
            last_lbl = labels[comp[-1]]
            x0, y0 = first_lbl.x, first_lbl.y
            x1, y1 = last_lbl.x, last_lbl.y
            
            count = len(comp)
            for i, idx in enumerate(comp):
                t = i / (count - 1)
                new_x = x0 + t * (x1 - x0)
                new_y = y0 + t * (y1 - y0)
                labels[idx].update_position(new_x, new_y)
            modified = True
            
        # Process vertical components
        for comp in v_components:
            comp.sort(key=lambda idx: labels[idx].y)
            first_lbl = labels[comp[0]]
            last_lbl = labels[comp[-1]]
            x0, y0 = first_lbl.x, first_lbl.y
            x1, y1 = last_lbl.x, last_lbl.y
            
            count = len(comp)
            for i, idx in enumerate(comp):
                t = i / (count - 1)
                new_x = x0 + t * (x1 - x0)
                new_y = y0 + t * (y1 - y0)
                labels[idx].update_position(new_x, new_y)
            modified = True
            
        if modified:
            self.is_dirty = True
            
        return modified

    def export_to_pptx(self, file_path: str):
        """Exports the current gel image and all its labels to a PowerPoint (.pptx) file.
        
        The gel image is added as a centered picture on a standard 16:9 widescreen slide,
        and all labels are added as editable text box shapes layered at exact relative positions.
        """
        self.compile_projects_to_pptx(file_path, [(self, "Gel")])

    @classmethod
    def compile_projects_to_pptx(cls, file_path: str, projects_with_names: list, existing_pptx_path: str = None):
        """Compiles multiple projects into a single PowerPoint (.pptx) file.
        
        projects_with_names is a list of tuples: (project_instance, tab_name_str)
        """
        import os
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN
        
        # Load existing presentation or create new
        if existing_pptx_path and os.path.exists(existing_pptx_path):
            prs = Presentation(existing_pptx_path)
        else:
            prs = Presentation()
            # Set slide width and height to standard widescreen 16:9 ratio
            prs.slide_width = Inches(13.33)
            prs.slide_height = Inches(7.5)
        
        # Select layout index safely (index 6 is blank layout in standard templates)
        if len(prs.slide_layouts) > 6:
            blank_slide_layout = prs.slide_layouts[6]
        else:
            blank_slide_layout = prs.slide_layouts[0]
        
        for item in projects_with_names:
            if len(item) == 3:
                project, tab_name, slide_title = item
            else:
                project, tab_name = item
                slide_title = ""
                
            slide = prs.slides.add_slide(blank_slide_layout)
            
            # Dynamically derive slide dimensions from presentation (supports 16:9, 4:3, or custom decks)
            try:
                slide_w_in = float(prs.slide_width.inches)
                slide_h_in = float(prs.slide_height.inches)
            except Exception:
                slide_w_in = float(prs.slide_width) / 914400.0
                slide_h_in = float(prs.slide_height) / 914400.0

            # If slide title is specified and not empty, add a centered title textbox at the top of the slide
            has_title = bool(slide_title and slide_title.strip())
            if has_title:
                title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(max(1.0, slide_w_in - 1.0)), Inches(0.8))
                tf_title = title_box.text_frame
                tf_title.word_wrap = True
                tf_title.margin_left = Inches(0)
                tf_title.margin_right = Inches(0)
                tf_title.margin_top = Inches(0)
                tf_title.margin_bottom = Inches(0)
                
                p_title = tf_title.paragraphs[0]
                p_title.text = slide_title.strip()
                p_title.alignment = PP_ALIGN.CENTER
                p_title.font.name = 'Arial'
                p_title.font.size = Pt(24)
                p_title.font.bold = True
                p_title.font.color.rgb = RGBColor(40, 40, 40)
            
            # If no image is loaded or path does not exist, show an empty title placeholder on slide
            if not project.image_path or not os.path.exists(project.image_path):
                box_w_in = min(6.0, max(2.0, slide_w_in - 2.0))
                box_h_in = 1.0
                tx_shape = slide.shapes.add_textbox(
                    Inches((slide_w_in - box_w_in) / 2.0), Inches((slide_h_in - box_h_in) / 2.0), Inches(box_w_in), Inches(box_h_in)
                )
                tf = tx_shape.text_frame
                p = tf.paragraphs[0]
                p.text = f"Empty Gel: {tab_name}"
                p.alignment = PP_ALIGN.CENTER
                p.font.size = Pt(24)
                p.font.color.rgb = RGBColor(128, 128, 128)
                continue
                
            # Get image dimensions
            img_w_px = project.image_width
            img_h_px = project.image_height
            
            if img_w_px <= 0 or img_h_px <= 0:
                continue
                
            # Calculate fit layout to center the gel image on the slide
            if has_title:
                avail_h_in = max(1.0, slide_h_in - 1.8)
                top_offset_in = 1.3
            else:
                avail_h_in = slide_h_in
                top_offset_in = 0.0
                
            scale = min(slide_w_in / img_w_px, avail_h_in / img_h_px)
            
            img_w_in = img_w_px * scale
            img_h_in = img_h_px * scale
            
            left_in = (slide_w_in - img_w_in) / 2.0
            if has_title:
                top_in = top_offset_in + (avail_h_in - img_h_in) / 2.0
            else:
                top_in = (slide_h_in - img_h_in) / 2.0
                
            # Add the gel image to the slide
            slide.shapes.add_picture(
                project.image_path,
                Inches(left_in),
                Inches(top_in),
                width=Inches(img_w_in),
                height=Inches(img_h_in)
            )
            
            # Add all labels as text boxes
            for label in project.labels.values():
                # Get exact GUI bounding box size in pixels (fallback to approximation if headless/errors)
                w_px = 60.0
                h_px = 24.0
                try:
                    from PyQt6.QtWidgets import QApplication
                    if QApplication.instance() is not None:
                        from PyQt6.QtGui import QFont, QFontMetricsF
                        font = QFont(label.font_family or 'Arial', label.font_size)
                        font.setBold(True)
                        fm = QFontMetricsF(font)
                        rect = fm.boundingRect(label.text)
                        w_px = max(15.0, rect.width() + 10.0)
                        h_px = max(10.0, rect.height() + 4.0)
                    else:
                        w_px = max(15.0, len(label.text) * label.font_size * 0.8 + 10.0)
                        h_px = label.font_size * 1.5
                except Exception:
                    w_px = max(15.0, len(label.text) * label.font_size * 0.8 + 10.0)
                    h_px = label.font_size * 1.5

                # Set text box dimensions in inches
                box_w_in = max(w_px + 10.0, 60.0) * scale
                box_h_in = max(h_px + 2.0, 24.0) * scale

                tx = left_in + (label.x - 5.0) * scale
                ty = top_in + (label.y - 1.0) * scale

                tx_shape = slide.shapes.add_textbox(
                    Inches(tx),
                    Inches(ty),
                    Inches(box_w_in),
                    Inches(box_h_in)
                )
                
                # Configure text box properties
                tf = tx_shape.text_frame
                tf.word_wrap = False
                # Remove default margins to ensure perfect positioning
                tf.margin_left = Inches(0)
                tf.margin_right = Inches(0)
                tf.margin_top = Inches(0)
                tf.margin_bottom = Inches(0)
                
                p = tf.paragraphs[0]
                p.text = label.text
                p.alignment = PP_ALIGN.CENTER
                
                # Styling: font family, size, color
                p.font.name = label.font_family or 'Arial'
                # Convert px to pt (1 px ~ 0.75 pt)
                font_size_pt = max(6, int(round(label.font_size * 0.75)))
                p.font.size = Pt(font_size_pt)
                p.font.bold = True
                
                # Color conversion (from hex to RGBColor)
                hex_color = label.color.lstrip('#')
                if len(hex_color) == 6:
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                    p.font.color.rgb = RGBColor(r, g, b)
                else:
                    p.font.color.rgb = RGBColor(255, 255, 255) # default white
                    
                # Rotation (powerpoint shape rotation is clockwise in degrees, 0 to 360)
                if abs(label.rotation) > 0.01:
                    # Rotate shapes directly in pptx
                    rot = label.rotation % 360
                    tx_shape.rotation = rot
                    
        prs.save(file_path)




