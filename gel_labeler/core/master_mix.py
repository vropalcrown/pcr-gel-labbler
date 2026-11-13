import os
import json
import logging
import tempfile
from dataclasses import dataclass, field
from typing import List, Dict
import csv
import io
from PyQt6.QtCore import QStandardPaths

logger = logging.getLogger("gel_labeler.core.master_mix")


@dataclass
class MasterMixComponent:
    name: str
    vol_per_rxn: float = 0.0
    in_master_mix: bool = True
    is_water: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "vol_per_rxn": self.vol_per_rxn,
            "in_master_mix": self.in_master_mix,
            "is_water": self.is_water
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MasterMixComponent":
        return cls(
            name=data.get("name", "Component"),
            vol_per_rxn=float(data.get("vol_per_rxn", 0.0)),
            in_master_mix=bool(data.get("in_master_mix", True)),
            is_water=bool(data.get("is_water", False))
        )


@dataclass
class MasterMixRecipe:
    name: str
    total_rxn_volume: float = 50.0
    num_reactions: int = 8
    excess_percent: float = 10.0  # +10% pipetting excess
    components: List[MasterMixComponent] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total_rxn_volume": self.total_rxn_volume,
            "num_reactions": self.num_reactions,
            "excess_percent": self.excess_percent,
            "components": [c.to_dict() for c in self.components]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MasterMixRecipe":
        raw_comps = data.get("components", [])
        components = [MasterMixComponent.from_dict(c) for c in raw_comps if isinstance(c, dict)]
        return cls(
            name=data.get("name", "Custom Mix"),
            total_rxn_volume=float(data.get("total_rxn_volume", 50.0)),
            num_reactions=int(data.get("num_reactions", 8)),
            excess_percent=float(data.get("excess_percent", 10.0)),
            components=components
        )

    @property
    def total_multiplier(self) -> float:
        """Effective reaction multiplier accounting for pipetting loss."""
        return self.num_reactions * (1.0 + max(0.0, self.excess_percent) / 100.0)

    def calculate_water_volume(self) -> float:
        """Computes remaining volume needed for nuclease-free water to hit total_rxn_volume."""
        other_vol = sum(c.vol_per_rxn for c in self.components if not c.is_water)
        water_vol = max(0.0, self.total_rxn_volume - other_vol)
        for c in self.components:
            if c.is_water:
                c.vol_per_rxn = round(water_vol, 2)
        return water_vol

    def get_summary_rows(self) -> List[dict]:
        """Calculates per-reaction and master mix volumes for all components."""
        self.calculate_water_volume()
        mult = self.total_multiplier
        rows = []
        for c in self.components:
            total_mm_vol = (c.vol_per_rxn * mult) if c.in_master_mix else 0.0
            rows.append({
                "component": c.name,
                "vol_1x": round(c.vol_per_rxn, 2),
                "in_mm": c.in_master_mix,
                "total_mm_vol": round(total_mm_vol, 2)
            })
        return rows

    def export_to_csv(self) -> str:
        """Exports the recipe table to CSV text."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["# Master Mix Recipe", self.name])
        writer.writerow(["Number of Reactions", self.num_reactions])
        writer.writerow(["Excess Pipetting Margin (%)", f"{self.excess_percent}%"])
        writer.writerow(["Effective Multiplier", f"{self.total_multiplier:.2f}x"])
        writer.writerow(["Single Reaction Volume (uL)", f"{self.total_rxn_volume:.2f}"])
        writer.writerow([])
        writer.writerow(["Component", "1x Volume (uL)", "In Master Mix", f"Total MM Volume (uL, {self.num_reactions} rxns)"])

        rows = self.get_summary_rows()
        for r in rows:
            in_mm_str = "YES" if r["in_mm"] else "NO (Add Individually)"
            mm_val = f"{r['total_mm_vol']:.2f}" if r["in_mm"] else "-"
            writer.writerow([r["component"], f"{r['vol_1x']:.2f}", in_mm_str, mm_val])

        # Write total master mix volume row
        total_mm = sum(r["total_mm_vol"] for r in rows if r["in_mm"])
        writer.writerow([])
        writer.writerow(["TOTAL MASTER MIX TUBE", "", "", f"{total_mm:.2f} uL"])
        return output.getvalue()

    def format_as_text_card(self) -> str:
        """Formats the recipe into a clean text card for copying directly into lab notebooks."""
        self.calculate_water_volume()
        rows = self.get_summary_rows()
        total_mm = sum(r["total_mm_vol"] for r in rows if r["in_mm"])
        mm_per_tube = sum(r["vol_1x"] for r in rows if r["in_mm"])

        lines = [
            f"=== {self.name.upper()} ===",
            f"Reactions: {self.num_reactions} | Excess: +{self.excess_percent:.0f}% (Scale: {self.total_multiplier:.2f}x) | Rxn Vol: {self.total_rxn_volume} µL",
            "-" * 65,
            f"{'Component':<28} {'1x (µL)':<10} {'In MM':<8} {f'Master Mix (µL)':<15}",
            "-" * 65
        ]
        for r in rows:
            in_mm = "YES" if r["in_mm"] else "NO"
            mm_vol = f"{r['total_mm_vol']:.2f}" if r["in_mm"] else "—"
            lines.append(f"{r['component']:<28} {r['vol_1x']:<10.2f} {in_mm:<8} {mm_vol:<15}")

        lines.append("-" * 65)
        lines.append(f"TOTAL MASTER MIX VOLUME: {total_mm:.2f} µL")
        lines.append(f"Aliquot {mm_per_tube:.2f} µL Master Mix into each tube, then add individual template/sample.")
        return "\n".join(lines)


# --- Standard Laboratory Presets ---

STANDARD_PRESETS: Dict[str, MasterMixRecipe] = {
    "Taq DNA Polymerase PCR (50 µL)": MasterMixRecipe(
        name="Standard Taq DNA Polymerase PCR (50 µL)",
        total_rxn_volume=50.0,
        num_reactions=8,
        excess_percent=10.0,
        components=[
            MasterMixComponent("10X PCR Buffer", vol_per_rxn=5.0, in_master_mix=True),
            MasterMixComponent("dNTP Mix (10 mM)", vol_per_rxn=1.0, in_master_mix=True),
            MasterMixComponent("Forward Primer (10 µM)", vol_per_rxn=1.0, in_master_mix=True),
            MasterMixComponent("Reverse Primer (10 µM)", vol_per_rxn=1.0, in_master_mix=True),
            MasterMixComponent("Taq DNA Polymerase (5 U/µL)", vol_per_rxn=0.25, in_master_mix=True),
            MasterMixComponent("Nuclease-Free Water", vol_per_rxn=39.75, in_master_mix=True, is_water=True),
            MasterMixComponent("Template DNA", vol_per_rxn=2.0, in_master_mix=False),
        ]
    ),
    "High-Fidelity Q5 / Phusion PCR (25 µL)": MasterMixRecipe(
        name="High-Fidelity Q5 / Phusion PCR (25 µL)",
        total_rxn_volume=25.0,
        num_reactions=8,
        excess_percent=10.0,
        components=[
            MasterMixComponent("5X Q5 / Phusion Reaction Buffer", vol_per_rxn=5.0, in_master_mix=True),
            MasterMixComponent("dNTPs (10 mM)", vol_per_rxn=0.5, in_master_mix=True),
            MasterMixComponent("Forward Primer (10 µM)", vol_per_rxn=1.25, in_master_mix=True),
            MasterMixComponent("Reverse Primer (10 µM)", vol_per_rxn=1.25, in_master_mix=True),
            MasterMixComponent("High-Fidelity DNA Polymerase", vol_per_rxn=0.25, in_master_mix=True),
            MasterMixComponent("Nuclease-Free Water", vol_per_rxn=15.75, in_master_mix=True, is_water=True),
            MasterMixComponent("Template DNA", vol_per_rxn=1.0, in_master_mix=False),
        ]
    ),
    "SYBR Green Real-Time qPCR (20 µL)": MasterMixRecipe(
        name="SYBR Green Real-Time qPCR (20 µL)",
        total_rxn_volume=20.0,
        num_reactions=16,
        excess_percent=12.0,
        components=[
            MasterMixComponent("2X SYBR Green Master Mix", vol_per_rxn=10.0, in_master_mix=True),
            MasterMixComponent("Forward Primer (10 µM)", vol_per_rxn=0.5, in_master_mix=True),
            MasterMixComponent("Reverse Primer (10 µM)", vol_per_rxn=0.5, in_master_mix=True),
            MasterMixComponent("Nuclease-Free Water", vol_per_rxn=7.0, in_master_mix=True, is_water=True),
            MasterMixComponent("cDNA Template", vol_per_rxn=2.0, in_master_mix=False),
        ]
    ),
    "Restriction Enzyme Double Digest (50 µL)": MasterMixRecipe(
        name="Restriction Enzyme Double Digest (50 µL)",
        total_rxn_volume=50.0,
        num_reactions=6,
        excess_percent=10.0,
        components=[
            MasterMixComponent("10X rCutSmart / NEBuffer", vol_per_rxn=5.0, in_master_mix=True),
            MasterMixComponent("Restriction Enzyme 1 (e.g. EcoRI-HF)", vol_per_rxn=0.5, in_master_mix=True),
            MasterMixComponent("Restriction Enzyme 2 (e.g. BamHI-HF)", vol_per_rxn=0.5, in_master_mix=True),
            MasterMixComponent("Nuclease-Free Water", vol_per_rxn=34.0, in_master_mix=True, is_water=True),
            MasterMixComponent("DNA Substrate (Plasmid/PCR)", vol_per_rxn=10.0, in_master_mix=False),
        ]
    ),
    "Reverse Transcription cDNA Synthesis (20 µL)": MasterMixRecipe(
        name="Reverse Transcription cDNA Synthesis (20 µL)",
        total_rxn_volume=20.0,
        num_reactions=8,
        excess_percent=10.0,
        components=[
            MasterMixComponent("5X RT Reaction Buffer", vol_per_rxn=4.0, in_master_mix=True),
            MasterMixComponent("dNTP Mix (10 mM)", vol_per_rxn=1.0, in_master_mix=True),
            MasterMixComponent("Oligo(dT) / Random Hexamer (50 µM)", vol_per_rxn=1.0, in_master_mix=True),
            MasterMixComponent("RNase Inhibitor (40 U/µL)", vol_per_rxn=0.5, in_master_mix=True),
            MasterMixComponent("Reverse Transcriptase (200 U/µL)", vol_per_rxn=1.0, in_master_mix=True),
            MasterMixComponent("Nuclease-Free Water", vol_per_rxn=7.5, in_master_mix=True, is_water=True),
            MasterMixComponent("Total RNA (up to 1 µg)", vol_per_rxn=5.0, in_master_mix=False),
        ]
    )
}


def get_master_mix_file_path() -> str:
    """Returns the writable AppData directory path for master_mixes.json."""
    app_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not app_dir:
        app_dir = os.path.join(tempfile.gettempdir(), "GelLabeler")
    try:
        os.makedirs(app_dir, exist_ok=True)
    except Exception:
        app_dir = tempfile.gettempdir()
    return os.path.join(app_dir, "master_mixes.json")


def load_user_master_mixes() -> Dict[str, MasterMixRecipe]:
    """Loads custom user master mix presets from AppData master_mixes.json."""
    path = get_master_mix_file_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            recipes = {}
            for name, recipe_data in data.items():
                if isinstance(recipe_data, dict):
                    recipes[name] = MasterMixRecipe.from_dict(recipe_data)
            return recipes
    except Exception as e:
        logger.error(f"Failed to load user master mixes from {path}: {e}")
    return {}


def save_user_master_mixes(recipes: Dict[str, MasterMixRecipe]) -> bool:
    """Saves user master mix recipes to AppData master_mixes.json atomically."""
    path = get_master_mix_file_path()
    temp_path = f"{path}.tmp"
    try:
        data = {name: r.to_dict() for name, r in recipes.items()}
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(temp_path, path)
        return True
    except Exception as e:
        logger.error(f"Failed to save user master mixes to {path}: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False


