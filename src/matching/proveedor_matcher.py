"""
Matching logic using canonical column names (tax_id, supplier_name).
Works on a DataFrame that has already been converted to canonical form
by ColumnMapper.to_canonical().
"""

import re
import pandas as pd
from rapidfuzz import fuzz


def normalize_nit(value) -> str:
    if value is None:
        return ""
    return re.sub(r"[^\d]", "", str(value))


def normalize_text(value) -> str:
    if value is None:
        return ""
    value = str(value).upper().strip()
    value = re.sub(r"\s+", " ", value)
    return value


def match_by_nit(df: pd.DataFrame, entity: dict):
    entity_nit = normalize_nit(entity.get("nit"))
    if not entity_nit or len(entity_nit) < 4:
        return None

    if "tax_id" not in df.columns:
        return None

    series = df["tax_id"].apply(normalize_nit)

    exact = df[series == entity_nit]
    if not exact.empty:
        return exact.index[0]

    contains = df[series.str.contains(entity_nit, na=False)]
    if not contains.empty:
        return contains.index[0]

    reverse = df[series.apply(lambda x: x != "" and entity_nit.startswith(x))]
    if not reverse.empty:
        return reverse.index[0]

    return None


def match_by_name(df: pd.DataFrame, entity: dict):
    entity_name = normalize_text(entity.get("empresa"))
    if not entity_name or len(entity_name) < 3:
        return None

    if "supplier_name" not in df.columns:
        return None

    best_index = None
    best_score = 0

    for idx, row in df.iterrows():
        row_name = normalize_text(row.get("supplier_name"))
        if not row_name:
            continue

        score = max(
            fuzz.token_sort_ratio(entity_name, row_name),
            fuzz.partial_ratio(entity_name, row_name),
        )

        if score > best_score:
            best_score = score
            best_index = idx

    return best_index if best_score >= 75 else None


def match_proveedor(df: pd.DataFrame, entity: dict):
    index = match_by_nit(df, entity)
    if index is not None:
        return index
    return match_by_name(df, entity)
