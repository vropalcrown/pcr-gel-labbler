import uuid
from gel_labeler.config import DEFAULT_COLOR

class GelLabel:
    """Represents a text label placed on the gel image.
    
    Coordinates (x, y), font_size, and rotation are defined relative to the original 
    image pixel space, ensuring that scaling the window does not distort labels.
    """
    
    def __init__(self, text: str, x: float, y: float, 
                 color: str = DEFAULT_COLOR, font_size: int = 16, 
                 font_family: str = "Arial", rotation: float = 0.0, label_id: str = None):
        self.id = label_id if label_id else str(uuid.uuid4())
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.font_size = font_size
        self.font_family = font_family
        self.rotation = 270.0 if "ladder" in text.lower() else rotation

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
        """Deserializes a dictionary back into a GelLabel object."""
        return cls(
            text=data.get("text", ""),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            color=data.get("color", "#00FF00"),
            font_size=data.get("font_size", 16),
            font_family=data.get("font_family", "Arial"),
            rotation=data.get("rotation", 0.0),
            label_id=data.get("id", None)
        )

    def update_position(self, x: float, y: float):
        """Updates the pixel coordinates of the label."""
        self.x = x
        self.y = y

    def update_style(self, text: str = None, color: str = None, font_size: int = None, rotation: float = None, font_family: str = None):
        """Updates style or content attributes of the label."""
        if text is not None:
            self.text = text
            if "ladder" in text.lower():
                self.rotation = 270.0
        if color is not None:
            self.color = color
        if font_size is not None:
            self.font_size = font_size
        if rotation is not None and (text is None or "ladder" not in text.lower()):
            self.rotation = rotation
        if font_family is not None:
            self.font_family = font_family

    def __repr__(self):
        return f"GelLabel(text='{self.text}', pos=({self.x:.1f}, {self.y:.1f}), color='{self.color}', size={self.font_size}, rot={self.rotation})"
