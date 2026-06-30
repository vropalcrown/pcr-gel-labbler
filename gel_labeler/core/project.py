import json
import csv
import os
from typing import Dict, List, Optional
import cv2
import numpy as np
from PyQt6.QtGui import QImage, QTransform
from PyQt6.QtCore import QPointF, QRectF, QRect, Qt
from gel_labeler.core.label import GelLabel

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

    def rotate_image(self, angle_deg: float):
        """Rotates the background image and maps label coordinates to the new rotated space."""
        if not self.image_path:
            return
        self.save_undo_state()
        
        image = QImage(self.image_path)
        if image.isNull():
            return
            
        transform = QTransform().rotate(angle_deg)
        rotated_image = image.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        
        # Save to processed file path
        base, ext = os.path.splitext(self.image_path)
        if not base.endswith("_processed"):
            new_path = f"{base}_processed.png"
        else:
            new_path = f"{base}.png"
            
        rotated_image.save(new_path)
        
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
        self.is_dirty = True
        self.gray_data = cv2.imread(new_path, cv2.IMREAD_GRAYSCALE)


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

    def to_dict(self) -> dict:
        """Serializes the project configuration."""
        return {
            "image_path": self.image_path,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "labels": [label.to_dict() for label in self.labels.values()]
        }

    def save_to_json(self, file_path: str):
        """Saves label data to a JSON file."""
        data = self.to_dict()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        self.is_dirty = False

    def load_from_json(self, file_path: str) -> bool:
        """Loads label data from a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Note: We keep the current image_path if it doesn't match or is missing,
            # but update labels.
            self.labels.clear()
            for label_data in data.get("labels", []):
                label = GelLabel.from_dict(label_data)
                self.labels[label.id] = label
            
            self.is_dirty = False
            return True
        except Exception as e:
            print(f"Error loading project JSON: {e}")
            return False

    def export_to_csv(self, file_path: str):
        """Exports the labels database to a CSV file."""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write Header
            writer.writerow(["label_id", "text", "pixel_x", "pixel_y", "color", "font_size", "font_family"])
            # Write label rows
            for label in self.labels.values():
                writer.writerow([
                    label.id,
                    label.text,
                    round(label.x, 2),
                    round(label.y, 2),
                    label.color,
                    label.font_size,
                    label.font_family
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
            # Filter out old labels close to this line segment region to prevent overlap
            y_min, y_max = min(y1, y2) - 40, max(y1, y2) + 40
            x_min, x_max = min(x1, x2) - 40, max(x1, x2) + 40
            
            self.labels = {
                lid: lbl for lid, lbl in self.labels.items()
                if not (x_min <= lbl.x <= x_max and y_min <= lbl.y <= y_max)
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
            
            # If slide title is specified and not empty, add a centered title textbox at the top of the slide
            has_title = bool(slide_title and slide_title.strip())
            if has_title:
                title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.33), Inches(0.8))
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
                box_w_in = 6.0
                box_h_in = 1.0
                tx_shape = slide.shapes.add_textbox(
                    Inches(3.66), Inches(3.25), Inches(box_w_in), Inches(box_h_in)
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
                
            # Calculate fit layout to center the gel image on the 13.33" x 7.5" slide
            slide_w_in = 13.33
            slide_h_in = 7.5
            
            if has_title:
                # Reserve top 1.3" for title. Available height for gel image is 5.7" (with 0.5" bottom margin)
                avail_h_in = 5.7
                top_offset_in = 1.3
            else:
                avail_h_in = 7.5
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
                    from PyQt6.QtWidgets import QGraphicsTextItem, QApplication
                    from PyQt6.QtGui import QFont
                    
                    app = QApplication.instance()
                    if not app:
                        app = QApplication([])
                        
                    item = QGraphicsTextItem()
                    item.setPlainText(label.text)
                    font = QFont(label.font_family or 'Arial', label.font_size)
                    font.setBold(True)
                    item.setFont(font)
                    rect = item.boundingRect()
                    w_px = rect.width()
                    h_px = rect.height()
                except Exception:
                    # Sensible approximation
                    w_px = max(15.0, len(label.text) * label.font_size * 0.6 + 10.0)
                    h_px = label.font_size * 1.5
                
                # Calculate center position in pixels
                cx_px = label.x + w_px / 2.0
                cy_px = label.y + h_px / 2.0
                
                # Convert center to slide inches
                cx_in = left_in + cx_px * scale
                cy_in = top_in + cy_px * scale
                
                # Set text box dimensions in inches
                # Add a tiny padding to prevent any wrapping issues
                box_w_in = (w_px + 10.0) * scale
                box_h_in = (h_px + 2.0) * scale
                
                tx = cx_in - box_w_in / 2.0
                ty = cy_in - box_h_in / 2.0
                
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




