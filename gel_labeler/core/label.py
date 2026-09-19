import uuid
import re
import math
from gel_labeler.config import DEFAULT_COLOR

HEX_COLOR_REGEX = re.compile(r"^#([0-9a-fA-F]{3,8})$")

class GelLabel:
    """Represents a text label placed on the gel image.
    
    Coordinates (x, y), font_size, and rotation are defined relative to the original 
    image pixel space, ensuring that scaling the window does not distort labels.
    """
    
    def __init__(self, text: str, x: float, y: float, 
                 color: str = DEFAULT_COLOR, font_size: int = 16, 
                 font_family: str = "Arial", rotation: float = 0.0, label_id: str = None):
        self.id = str(label_id) if label_id else str(uuid.uuid4())
        self.text = str(text) if text is not None else ""
        self.x = float(x) if (isinstance(x, (int, float)) and math.isfinite(x)) else 0.0
        self.y = float(y) if (isinstance(y, (int, float)) and math.isfinite(y)) else 0.0
        
        # Validate hex color format
        color_str = str(color).strip() if color else DEFAULT_COLOR
        self.color = color_str if HEX_COLOR_REGEX.match(color_str) else DEFAULT_COLOR
        
        # Clamp font size safely between 4 and 144
        try:
            sz = int(round(float(font_size)))
        except (ValueError, TypeError):
            sz = 16
        self.font_size = max(4, min(144, sz))
        
        self.font_family = str(font_family) if font_family else "Arial"
        
        try:
            rot = float(rotation) % 360.0
        except (ValueError, TypeError):
            rot = 0.0
            
        self.rotation = 270.0 if "ladder" in self.text.lower() else rot

    def to_dict(self) -> dict:
        """Serializes the label data into a dictionary for JSON/CSV exports."""
        return {
            "id": self.id,
            "text": self.text,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "color": self.color,
            "font_size": self.font_size,
            "font_family": self.font_family,
            "rotation": round(self.rotation, 1)
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GelLabel":
        """Deserializes and validates a dictionary back into a GelLabel object."""
        if not isinstance(data, dict):
            return cls(text="", x=0.0, y=0.0)
            
        return cls(
            text=str(data.get("text", "")),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            color=data.get("color", DEFAULT_COLOR),
            font_size=data.get("font_size", 16),
            font_family=data.get("font_family", "Arial"),
            rotation=data.get("rotation", 0.0),
            label_id=data.get("id", None)
        )

    def update_position(self, x: float, y: float):
        """Updates the pixel coordinates of the label."""
        if isinstance(x, (int, float)) and math.isfinite(x):
            self.x = float(x)
        if isinstance(y, (int, float)) and math.isfinite(y):
            self.y = float(y)

    def update_style(self, text: str = None, color: str = None, font_size: int = None, rotation: float = None, font_family: str = None):
        """Updates style or content attributes of the label."""
        if text is not None:
            self.text = str(text)
            if "ladder" in self.text.lower():
                self.rotation = 270.0
        if color is not None:
            color_str = str(color).strip()
            if HEX_COLOR_REGEX.match(color_str):
                self.color = color_str
        if font_size is not None:
            try:
                sz = int(round(float(font_size)))
                self.font_size = max(4, min(144, sz))
            except (ValueError, TypeError):
                pass
        if rotation is not None and (text is None or "ladder" not in self.text.lower()):
            try:
                self.rotation = float(rotation) % 360.0
            except (ValueError, TypeError):
                pass
        if font_family is not None:
            self.font_family = str(font_family)

    def __repr__(self):
        return f"GelLabel(text='{self.text}', pos=({self.x:.1f}, {self.y:.1f}), color='{self.color}', size={self.font_size}, rot={self.rotation})"
