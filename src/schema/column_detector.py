"""
Automatic column detection: reads an Excel's headers and suggests
a canonical mapping using exact alias matching + fuzzy scoring.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from rapidfuzz import fuzz, process as fuzz_process

ALIASES_PATH = Path(__file__).parent / "schema_aliases.yaml"


@dataclass
class ColumnSuggestion:
    canonical_key: str
    excel_column: str
    confidence: float   # 0.0 – 1.0
    method: str         # "exact" | "fuzzy"


def _load_aliases() -> dict[str, list[str]]:
    with open(ALIASES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _normalize(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace/punctuation."""
    text = text.lower().strip()
    accents = str.maketrans(
        "áéíóúäëïöüàèìòùâêîôûãõñç",
        "aeiouaeiouaeiouaeiouaonc",
    )
    text = text.translate(accents)
    text = re.sub(r"[\s_\-\.]+", " ", text).strip()
    return text


def detect_columns(
    excel_path: str,
    sheet_name: int | str = 0,
    header_row: int = 0,
) -> tuple[list[str], list[ColumnSuggestion]]:
    """
    Returns:
        excel_columns  — all column names found in the sheet (non-blank)
        suggestions    — ranked list of canonical↔excel mappings with confidence
    """
    df = pd.read_excel(
        excel_path, sheet_name=sheet_name, header=header_row, nrows=0,
    )
    excel_columns: list[str] = [
        str(c).strip()
        for c in df.columns
        if str(c).strip() and not str(c).startswith("Unnamed")
    ]

    aliases = _load_aliases()

    # Build: normalized_alias → (canonical_key, is_primary_alias)
    alias_lookup: dict[str, str] = {}
    canonical_aliases: dict[str, list[str]] = {}
    for canonical_key, alias_list in aliases.items():
        normalized_list = [_normalize(a) for a in alias_list]
        canonical_aliases[canonical_key] = normalized_list
        for norm in normalized_list:
            alias_lookup[norm] = canonical_key

    # For each canonical key, find the best-scoring Excel column
    # canonical_key → (excel_column, score, method)
    best: dict[str, tuple[str, float, str]] = {}

    for col in excel_columns:
        col_norm = _normalize(col)

        for canonical_key, norm_aliases in canonical_aliases.items():
            # Exact alias match → confidence 1.0
            if col_norm in norm_aliases:
                score, method = 1.0, "exact"
            else:
                # Fuzzy: best ratio against alias list
                result = fuzz_process.extractOne(
                    col_norm,
                    norm_aliases,
                    scorer=fuzz.token_sort_ratio,
                )
                if result and result[1] >= 65:
                    score = round(result[1] / 100.0 * 0.88, 3)  # cap fuzzy at 0.88
                    method = "fuzzy"
                else:
                    continue

            existing = best.get(canonical_key)
            if existing is None or score > existing[1]:
                best[canonical_key] = (col, score, method)

    # Resolve conflicts: one Excel column per canonical field
    used_columns: set[str] = set()
    suggestions: list[ColumnSuggestion] = []
    for canonical_key, (col, score, method) in sorted(
        best.items(), key=lambda x: x[1][1], reverse=True
    ):
        if col not in used_columns:
            suggestions.append(
                ColumnSuggestion(
                    canonical_key=canonical_key,
                    excel_column=col,
                    confidence=score,
                    method=method,
                )
            )
            used_columns.add(col)

    return excel_columns, suggestions


def suggestions_to_mapping(suggestions: list[ColumnSuggestion]) -> dict[str, str]:
    """Convert suggestion list → {canonical_key: excel_column}."""
    return {s.canonical_key: s.excel_column for s in suggestions}


# ── CLI entry point (called by Tauri via subprocess) ─────────────────────────

def _cli_detect(excel_path: str, sheet_name: Any, header_row: int) -> None:
    try:
        sheet: int | str = int(sheet_name) if str(sheet_name).isdigit() else sheet_name
        columns, suggestions = detect_columns(excel_path, sheet_name=sheet, header_row=header_row)
        result = {
            "excel_columns": columns,
            "suggestions": [asdict(s) for s in suggestions],
        }
        print(json.dumps(result, ensure_ascii=False), flush=True)
    except Exception as e:
        print(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            flush=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--excel", required=True)
    p.add_argument("--sheet", default=0)
    p.add_argument("--header-row", type=int, default=0)
    a = p.parse_args()
    _cli_detect(a.excel, a.sheet, a.header_row)
