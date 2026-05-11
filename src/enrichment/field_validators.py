"""
Domain validation and sanitization for values before writing to the DataFrame.
Works with canonical column names (tax_id, supplier_name, address, …).
Returns (cleaned_value, is_valid, reject_reason).
"""

import re
from typing import Any

from src.config.excel_schema import TEXT_COLUMNS, CATEGORICAL_COLUMNS


def _clean_string(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _try_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def validate_and_sanitize(column: str, value: Any) -> tuple[Any, bool, str]:
    if value is None:
        return None, False, "valor nulo"

    if isinstance(value, str) and value.strip() == "":
        return None, False, "string vacío"

    if column in TEXT_COLUMNS:
        cleaned = _clean_string(value)
        if not cleaned:
            return None, False, "string vacío tras limpiar"

        # NIT validation: canonical name is "tax_id"
        if column == "tax_id":
            digits = re.sub(r"[^\d]", "", cleaned)
            if len(digits) < 4:
                return None, False, f"NIT muy corto ({len(digits)} dígitos)"
            return cleaned, True, ""

        return cleaned, True, ""

    if column in CATEGORICAL_COLUMNS:
        allowed = CATEGORICAL_COLUMNS[column]
        as_int = _try_int(value)
        if as_int is None:
            return None, False, f"no se pudo convertir a entero: {value!r}"
        if as_int not in allowed:
            return None, False, f"valor {as_int} fuera de dominio {sorted(allowed)}"
        return as_int, True, ""

    return value, True, ""
