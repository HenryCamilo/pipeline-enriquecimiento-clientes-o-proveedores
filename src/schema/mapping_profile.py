"""
Save and load column mapping profiles (YAML or JSON).
Profiles live in config/mappings/ by default.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Union

import yaml

DEFAULT_PROFILES_DIR = Path("config/mappings")


@dataclass
class MappingProfile:
    name: str
    mapping: dict[str, str]         # canonical_key → original_excel_column
    sheet_name: Union[int, str] = 0
    header_row: int = 0
    export_mode: str = "original"   # "original" | "canonical"
    description: str = ""


# ── Persistence ───────────────────────────────────────────────────────────────

def save_profile(
    profile: MappingProfile,
    profiles_dir: Path = DEFAULT_PROFILES_DIR,
    fmt: str = "yaml",
) -> Path:
    """Save a profile as YAML (default) or JSON. Returns the saved path."""
    profiles_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(profile.name)
    ext = ".yaml" if fmt == "yaml" else ".json"
    path = profiles_dir / (stem + ext)

    data = {
        "name": profile.name,
        "description": profile.description,
        "sheet_name": profile.sheet_name,
        "header_row": profile.header_row,
        "export_mode": profile.export_mode,
        "mapping": profile.mapping,
    }

    with open(path, "w", encoding="utf-8") as f:
        if fmt == "yaml":
            yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        else:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return path


def load_profile(path: Path) -> MappingProfile:
    """Load a profile from YAML or JSON file."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) if path.suffix in (".yaml", ".yml") else json.load(f)

    return MappingProfile(
        name=data.get("name", path.stem),
        mapping=data.get("mapping", {}),
        sheet_name=data.get("sheet_name", 0),
        header_row=int(data.get("header_row", 0)),
        export_mode=data.get("export_mode", "original"),
        description=data.get("description", ""),
    )


def list_profiles(profiles_dir: Path = DEFAULT_PROFILES_DIR) -> list[MappingProfile]:
    """Return all profiles found in a directory, sorted by name."""
    if not profiles_dir.exists():
        return []
    paths = sorted(
        p for p in profiles_dir.iterdir()
        if p.suffix in (".yaml", ".yml", ".json")
    )
    profiles = []
    for p in paths:
        try:
            profiles.append(load_profile(p))
        except Exception:
            pass
    return profiles


def profile_to_dict(profile: MappingProfile) -> dict:
    return asdict(profile)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_stem(name: str) -> str:
    """Turn a profile name into a safe filename stem."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s]+", "_", name)
    return name[:64] or "profile"
