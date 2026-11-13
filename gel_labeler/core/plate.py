"""
Core data models, serialisation, and export engine for Multiwell Plate Layouts (6, 12, 24, 48, 96, 384, custom).
"""
import os
import json
import logging
import tempfile
import csv
import io
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from PyQt6.QtCore import QStandardPaths

logger = logging.getLogger("gel_labeler.core.plate")

# Standard Sample Roles with high-contrast, professional palette
STANDARD_ROLE_COLORS = {
    "Sample": "#2563eb",      # Vibrant Blue
    "Standard": "#ea580c",    # Amber/Orange
    "Control": "#16a34a",     # Emerald Green
    "Blank": "#64748b",       # Slate Gray
    "Positive": "#dc2626",    # Crimson Red
    "Negative": "#0891b2",    # Cyan/Teal
    "Treated": "#9333ea",     # Royal Purple
    "Empty": "#25282c"        # Neutral Dark Unfilled
}

STANDARD_PLATE_FORMATS = {
    "6-Well (2 × 3)": (2, 3),
    "12-Well (3 × 4)": (3, 4),
    "24-Well (4 × 6)": (4, 6),
    "48-Well (6 × 8)": (6, 8),
    "96-Well (8 × 12)": (8, 12),
    "384-Well (16 × 24)": (16, 24),
}


def row_index_to_letter(row: int) -> str:
    """Converts 0-based row index to spreadsheet-style row letter (A, B, ... Z, AA, AB...)."""
    if row < 0:
        return "A"
    result = ""
    while True:
        result = chr(ord('A') + (row % 26)) + result
        row = (row // 26) - 1
        if row < 0:
            break
    return result


def row_letter_to_index(letter: str) -> int:
    """Converts row letter (A, B, ... AA) to 0-based row index."""
    s = letter.strip().upper()
    idx = 0
    for char in s:
        if 'A' <= char <= 'Z':
            idx = idx * 26 + (ord(char) - ord('A') + 1)
        else:
            return 0
    return max(0, idx - 1)


def make_well_id(row: int, col: int) -> str:
    """Constructs well coordinate string (e.g., row=0, col=0 -> 'A1')."""
    return f"{row_index_to_letter(row)}{col + 1}"


def parse_well_id(well_id: str) -> Tuple[int, int]:
    """Parses a well coordinate string like 'A1' or 'H12' into (row, col) indices."""
    well_id = well_id.strip().upper()
    letters = ""
    digits = ""
    for char in well_id:
        if char.isalpha():
            letters += char
        elif char.isdigit():
            digits += char
    row = row_letter_to_index(letters) if letters else 0
    col = (int(digits) - 1) if digits else 0
    return row, max(0, col)


@dataclass
class WellData:
    """Represents a single well on a multiwell plate."""
    row: int
    col: int
    title: str = ""
    description: str = ""
    color: str = "#25282c"
    role: str = "Empty"
    concentration: str = ""

    @property
    def well_id(self) -> str:
        return make_well_id(self.row, self.col)

    @property
    def is_empty(self) -> bool:
        return not self.title.strip() and self.role == "Empty" and self.color == "#25282c"

    def clear(self):
        self.title = ""
        self.description = ""
        self.color = "#25282c"
        self.role = "Empty"
        self.concentration = ""

    def copy_from(self, other: "WellData"):
        self.title = other.title
        self.description = other.description
        self.color = other.color
        self.role = other.role
        self.concentration = other.concentration

    def to_dict(self) -> dict:
        return {
            "row": self.row,
            "col": self.col,
            "title": self.title,
            "description": self.description,
            "color": self.color,
            "role": self.role,
            "concentration": self.concentration
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WellData":
        return cls(
            row=int(data.get("row", 0)),
            col=int(data.get("col", 0)),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            color=str(data.get("color", "#25282c")),
            role=str(data.get("role", "Empty")),
            concentration=str(data.get("concentration", ""))
        )


@dataclass
class PlateProject:
    """Represents an entire multiwell plate layout with arbitrary grid size and persistent wells."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Untitled Plate"
    rows: int = 8
    cols: int = 12
    description: str = ""
    wells: Dict[str, WellData] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        self._ensure_wells()

    def _ensure_wells(self):
        """Ensures all wells for the current rows/cols exist in self.wells dictionary."""
        for r in range(self.rows):
            for c in range(self.cols):
                wid = make_well_id(r, c)
                if wid not in self.wells:
                    self.wells[wid] = WellData(row=r, col=c)

    def resize(self, new_rows: int, new_cols: int):
        """Resizes the plate format, preserving existing data that falls within new bounds."""
        new_rows = max(1, min(26, new_rows))
        new_cols = max(1, min(48, new_cols))
        new_wells = {}
        for r in range(new_rows):
            for c in range(new_cols):
                wid = make_well_id(r, c)
                if wid in self.wells:
                    new_wells[wid] = self.wells[wid]
                else:
                    new_wells[wid] = WellData(row=r, col=c)
        self.rows = new_rows
        self.cols = new_cols
        self.wells = new_wells
        self.updated_at = datetime.now().isoformat()

    def get_well(self, row: int, col: int) -> WellData:
        wid = make_well_id(row, col)
        if wid not in self.wells:
            self.wells[wid] = WellData(row=row, col=col)
        return self.wells[wid]

    def clear_wells(self, well_ids: List[str]):
        for wid in well_ids:
            if wid in self.wells:
                self.wells[wid].clear()
        self.updated_at = datetime.now().isoformat()

    def clear_all(self):
        for well in self.wells.values():
            well.clear()
        self.updated_at = datetime.now().isoformat()

    def apply_batch(
        self,
        well_ids: List[str],
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        role: Optional[str] = None,
        concentration: Optional[str] = None
    ):
        """Applies attributes to a set of selected wells simultaneously."""
        for wid in well_ids:
            if wid in self.wells:
                w = self.wells[wid]
                if title is not None:
                    w.title = title
                if description is not None:
                    w.description = description
                if color is not None:
                    w.color = color
                if role is not None:
                    w.role = role
                if concentration is not None:
                    w.concentration = concentration
        self.updated_at = datetime.now().isoformat()

    def apply_series(
        self,
        well_ids: List[str],
        prefix: str = "Sample",
        start_num: int = 1,
        pad: int = 0,
        color: Optional[str] = None,
        role: Optional[str] = None
    ):
        """Auto-increments titles across selected wells (e.g. Sample 1, Sample 2...)."""
        current_num = start_num
        for wid in well_ids:
            if wid in self.wells:
                w = self.wells[wid]
                num_str = str(current_num).zfill(pad) if pad > 0 else str(current_num)
                w.title = f"{prefix} {num_str}".strip() if prefix else num_str
                if color is not None:
                    w.color = color
                if role is not None:
                    w.role = role
                current_num += 1
        self.updated_at = datetime.now().isoformat()

    def get_stats(self) -> Dict[str, int]:
        """Calculates breakdown of filled, empty, and categorized wells."""
        stats = {"total": self.rows * self.cols, "filled": 0, "empty": 0}
        for w in self.wells.values():
            if w.is_empty:
                stats["empty"] += 1
            else:
                stats["filled"] += 1
                stats[w.role] = stats.get(w.role, 0) + 1
        return stats

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "rows": self.rows,
            "cols": self.cols,
            "description": self.description,
            "wells": {wid: w.to_dict() for wid, w in self.wells.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlateProject":
        rows = int(data.get("rows", 8))
        cols = int(data.get("cols", 12))
        proj = cls(
            id=str(data.get("id", uuid.uuid4())),
            name=str(data.get("name", "Untitled Plate")),
            rows=rows,
            cols=cols,
            description=str(data.get("description", "")),
            created_at=str(data.get("created_at", datetime.now().isoformat())),
            updated_at=str(data.get("updated_at", datetime.now().isoformat())),
            wells={}
        )
        raw_wells = data.get("wells", {})
        if isinstance(raw_wells, dict):
            for wid, wdata in raw_wells.items():
                if isinstance(wdata, dict):
                    proj.wells[wid] = WellData.from_dict(wdata)
        proj._ensure_wells()
        return proj

    def export_matrix_csv(self) -> str:
        """Exports 2D visual matrix layout (Columns 1..N across top, Rows A..Z down side)."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([f"# Plate Matrix: {self.name} ({self.rows}x{self.cols})"])
        writer.writerow(["Row"] + [str(c + 1) for c in range(self.cols)])
        for r in range(self.rows):
            row_label = row_index_to_letter(r)
            row_cells = [row_label]
            for c in range(self.cols):
                w = self.get_well(r, c)
                cell_text = w.title if w.title else ""
                # Formula injection protection
                if cell_text.startswith(('=', '+', '-', '@')):
                    cell_text = "'" + cell_text
                row_cells.append(cell_text)
            writer.writerow(row_cells)
        return output.getvalue()

    def export_table_csv(self) -> str:
        """Exports tabular list: Well, Row, Column, Title, Role, Concentration, Description, Color."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Well", "Row", "Column", "Title", "Role", "Concentration", "Description", "Color"])
        for r in range(self.rows):
            for c in range(self.cols):
                w = self.get_well(r, c)
                if not w.is_empty:
                    title = w.title
                    if title.startswith(('=', '+', '-', '@')):
                        title = "'" + title
                    desc = w.description
                    if desc.startswith(('=', '+', '-', '@')):
                        desc = "'" + desc
                    writer.writerow([
                        w.well_id,
                        row_index_to_letter(r),
                        str(c + 1),
                        title,
                        w.role,
                        w.concentration,
                        desc,
                        w.color
                    ])
        return output.getvalue()


# --- Standard Templates ---

def create_builtin_templates() -> Dict[str, PlateProject]:
    """Generates pre-configured laboratory multiwell plate templates."""
    templates = {}

    # 1. 96-well qPCR Triplicates (8 samples x 3 replicates)
    qpcr = PlateProject(
        name="96-Well qPCR Triplicates Layout",
        rows=8,
        cols=12,
        description="Standard 96-well qPCR setup: 8 target conditions tested in technical triplicates across 4 target genes."
    )
    colors = ["#2563eb", "#059669", "#ea580c", "#9333ea", "#dc2626", "#0891b2", "#d97706", "#64748b"]
    for s_idx in range(8):
        sample_name = f"Sample {s_idx + 1}"
        col = colors[s_idx % len(colors)]
        for rep in range(3):
            c = s_idx + rep
            # Place in row A, B, C...
            w = qpcr.get_well(s_idx, rep)
            w.title = f"{sample_name}-R{rep + 1}"
            w.role = "Sample"
            w.color = col
    # NTC (No Template Controls) in Col 12
    for r in range(8):
        w = qpcr.get_well(r, 11)
        w.title = "NTC"
        w.role = "Negative"
        w.color = "#64748b"
    templates["96-Well qPCR (Triplicates & Controls)"] = qpcr

    # 2. 96-well ELISA (Standard Curve Cols 1-2, Unknowns Cols 3-12)
    elisa = PlateProject(
        name="96-Well ELISA Standard Curve & Screening",
        rows=8,
        cols=12,
        description="ELISA plate with 8-point standard curve in duplicate (Cols 1-2), Blanks (H1-H2), and sample duplicates."
    )
    std_concs = ["1000 pg/mL", "500 pg/mL", "250 pg/mL", "125 pg/mL", "62.5 pg/mL", "31.25 pg/mL", "15.6 pg/mL", "0 pg/mL (Blank)"]
    for r in range(7):
        role_str = "Standard"
        color_str = "#ea580c"
        for c in (0, 1):
            w = elisa.get_well(r, c)
            w.title = f"Std {r + 1}"
            w.role = role_str
            w.concentration = std_concs[r]
            w.color = color_str
    # Blanks row 7 (H1, H2)
    for c in (0, 1):
        w = elisa.get_well(7, c)
        w.title = "Blank"
        w.role = "Blank"
        w.concentration = "0 pg/mL"
        w.color = "#64748b"

    templates["96-Well ELISA (Standards & Duplicates)"] = elisa

    # 3. 24-Well Cell Culture Screening
    cell24 = PlateProject(
        name="24-Well Cell Culture Plate",
        rows=4,
        cols=6,
        description="24-well plate setup: Control vs 5 Treatment conditions in quadruplicate."
    )
    for r in range(4):
        w_ctrl = cell24.get_well(r, 0)
        w_ctrl.title = "Veh Ctrl"
        w_ctrl.role = "Control"
        w_ctrl.color = "#16a34a"
        for c in range(1, 6):
            w = cell24.get_well(r, c)
            w.title = f"Dose {c}"
            w.role = "Treated"
            w.color = "#9333ea"
    templates["24-Well Cell Culture Screening"] = cell24

    # 4. 6-Well Transfection Layout
    trans6 = PlateProject(
        name="6-Well Transfection Layout",
        rows=2,
        cols=3,
        description="6-well culture vessel: Untreated, Mock, Control Plasmid, and Experimental Plasmids."
    )
    wells_data = [
        (0, 0, "Untreated", "Control", "#16a34a"),
        (0, 1, "Mock / Lipid", "Control", "#16a34a"),
        (0, 2, "pEmpty Vector", "Control", "#64748b"),
        (1, 0, "Gene-OE Low", "Sample", "#2563eb"),
        (1, 1, "Gene-OE Med", "Sample", "#2563eb"),
        (1, 2, "Gene-OE High", "Sample", "#9333ea")
    ]
    for r, c, t, ro, col in wells_data:
        w = trans6.get_well(r, c)
        w.title = t
        w.role = ro
        w.color = col
    templates["6-Well Transfection & Culture"] = trans6

    return templates


# --- AppData Storage & File IO ---

def get_plates_file_path() -> str:
    """Returns writable AppData path for plates.json."""
    app_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not app_dir:
        app_dir = os.path.join(tempfile.gettempdir(), "GelLabeler")
    try:
        os.makedirs(app_dir, exist_ok=True)
    except Exception:
        app_dir = tempfile.gettempdir()
    return os.path.join(app_dir, "plates.json")


def load_user_plates() -> Dict[str, PlateProject]:
    """Loads user plates from AppData plates.json."""
    path = get_plates_file_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            plates = {}
            for name, pdata in data.items():
                if isinstance(pdata, dict):
                    plates[name] = PlateProject.from_dict(pdata)
            return plates
    except Exception as e:
        logger.error(f"Failed to load user plates from {path}: {e}")
    return {}


def save_user_plates(plates: Dict[str, PlateProject]) -> bool:
    """Saves user plates to AppData plates.json atomically."""
    path = get_plates_file_path()
    temp_path = f"{path}.tmp"
    try:
        data = {name: p.to_dict() for name, p in plates.items()}
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(temp_path, path)
        return True
    except Exception as e:
        logger.error(f"Failed to save user plates to {path}: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False


def export_plate_to_json(plate: PlateProject, file_path: str) -> bool:
    """Exports a single plate layout to a JSON file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(plate.to_dict(), f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Failed to export plate to {file_path}: {e}")
        return False


def import_plate_from_json(file_path: str) -> Optional[PlateProject]:
    """Imports a plate layout from a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return PlateProject.from_dict(data)
    except Exception as e:
        logger.error(f"Failed to import plate from {file_path}: {e}")
    return None
