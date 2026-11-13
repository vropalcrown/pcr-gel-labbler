"""
Core data models and persistent storage for Custom Lab Protocols and Standard Operating Procedures (SOPs).
"""
import os
import json
import logging
import tempfile
import uuid
from dataclasses import dataclass, field
from typing import List, Optional
from PyQt6.QtCore import QStandardPaths

logger = logging.getLogger("gel_labeler")


@dataclass
class ProtocolStep:
    step_num: int
    title: str
    instruction: str
    duration_seconds: Optional[int] = None  # None for instant steps, int for timed steps
    is_completed: bool = False
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "step_num": self.step_num,
            "title": self.title,
            "instruction": self.instruction,
            "duration_seconds": self.duration_seconds,
            "is_completed": self.is_completed,
            "notes": self.notes
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProtocolStep":
        return cls(
            step_num=int(data.get("step_num", 1)),
            title=data.get("title", ""),
            instruction=data.get("instruction", ""),
            duration_seconds=data.get("duration_seconds"),
            is_completed=bool(data.get("is_completed", False)),
            notes=data.get("notes", "")
        )


@dataclass
class Protocol:
    id: str
    name: str
    category: str
    description: str
    estimated_time: str
    steps: List[ProtocolStep] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "estimated_time": self.estimated_time,
            "steps": [s.to_dict() for s in self.steps]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Protocol":
        steps = [ProtocolStep.from_dict(s) for s in data.get("steps", [])]
        proto_id = data.get("id") or f"proto_{uuid.uuid4().hex[:8]}"
        return cls(
            id=proto_id,
            name=data.get("name", "Untitled Protocol"),
            category=data.get("category", "General"),
            description=data.get("description", ""),
            estimated_time=data.get("estimated_time", "Unknown"),
            steps=steps
        )

    def reset_progress(self):
        for s in self.steps:
            s.is_completed = False
            s.notes = ""

    def get_progress_percent(self) -> int:
        if not self.steps:
            return 0
        done = sum(1 for s in self.steps if s.is_completed)
        return int((done / len(self.steps)) * 100)


# Empty list as requested: all default pre-loaded protocols removed
STANDARD_PROTOCOLS: List[Protocol] = []


def get_protocols_file_path() -> str:
    """Returns the writable AppData directory path for protocols.json."""
    app_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not app_dir:
        app_dir = os.path.join(tempfile.gettempdir(), "GelLabeler")
    try:
        os.makedirs(app_dir, exist_ok=True)
    except Exception:
        app_dir = tempfile.gettempdir()
    return os.path.join(app_dir, "protocols.json")


def load_user_protocols() -> List[Protocol]:
    """Loads custom user protocols from AppData protocols.json."""
    path = get_protocols_file_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [Protocol.from_dict(d) for d in data if isinstance(d, dict)]
        elif isinstance(data, dict) and "protocols" in data:
            return [Protocol.from_dict(d) for d in data["protocols"] if isinstance(d, dict)]
    except Exception as e:
        logger.error(f"Failed to load user protocols from {path}: {e}")
    return []


def save_user_protocols(protocols: List[Protocol]) -> bool:
    """Saves user protocols to AppData protocols.json atomically."""
    path = get_protocols_file_path()
    temp_path = f"{path}.tmp"
    try:
        data = [p.to_dict() for p in protocols]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(temp_path, path)
        return True
    except Exception as e:
        logger.error(f"Failed to save user protocols to {path}: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False


def export_protocol_to_json(protocol: Protocol, file_path: str) -> bool:
    """Exports a single protocol to a designated JSON file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(protocol.to_dict(), f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Failed to export protocol to {file_path}: {e}")
        return False


def import_protocol_from_json(file_path: str) -> Optional[Protocol]:
    """Imports a protocol from a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            if "name" in data and "steps" in data:
                if not data.get("id"):
                    data["id"] = f"proto_{uuid.uuid4().hex[:8]}"
                return Protocol.from_dict(data)
    except Exception as e:
        logger.error(f"Failed to import protocol from {file_path}: {e}")
    return None
