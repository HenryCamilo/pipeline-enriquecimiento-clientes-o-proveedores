"""
Bidirectional column mapper: converts a DataFrame between its original
Excel column names and the pipeline's canonical names.
"""

from __future__ import annotations

import pandas as pd


class ColumnMapper:
    """
    mapping: {canonical_key: original_excel_column}
    """

    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping                                  # canonical → original
        self._reverse = {v: k for k, v in mapping.items()}     # original  → canonical

    # ── Conversion ────────────────────────────────────────────────────────────

    def to_canonical(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename mapped original columns to canonical names. Unmapped columns untouched."""
        rename = {orig: canon for canon, orig in self.mapping.items() if orig in df.columns}
        return df.rename(columns=rename)

    def from_canonical(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename canonical columns back to original names."""
        rename = {canon: orig for canon, orig in self.mapping.items() if canon in df.columns}
        return df.rename(columns=rename)

    # ── Queries ───────────────────────────────────────────────────────────────

    def original_for(self, canonical_key: str) -> str | None:
        return self.mapping.get(canonical_key)

    def canonical_for(self, original_col: str) -> str | None:
        return self._reverse.get(original_col)

    def has_canonical(self, canonical_key: str) -> bool:
        return canonical_key in self.mapping

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(self, df: pd.DataFrame) -> list[str]:
        """
        Returns a list of validation error strings.
        Empty list means the mapping is valid and the pipeline can proceed.
        """
        errors: list[str] = []

        # At least one identity field must be mapped
        if not self.mapping.get("tax_id") and not self.mapping.get("supplier_name"):
            errors.append(
                "El mapping debe incluir al menos 'tax_id' (NIT) o 'supplier_name' (nombre)."
            )

        # All mapped columns must exist in the DataFrame
        for canon, orig in self.mapping.items():
            if orig not in df.columns:
                errors.append(
                    f"La columna '{orig}' (mapeada a '{canon}') no existe en el Excel."
                )

        # No two canonical fields may point to the same Excel column
        seen: dict[str, list[str]] = {}
        for canon, orig in self.mapping.items():
            seen.setdefault(orig, []).append(canon)
        for orig, keys in seen.items():
            if len(keys) > 1:
                errors.append(
                    f"La columna Excel '{orig}' está mapeada a múltiples campos: {keys}."
                )

        # DataFrame must have at least one data row
        if len(df) == 0:
            errors.append("El Excel no contiene filas de datos.")

        return errors
