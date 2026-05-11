"""
Safe Excel row updater.
- Validates and sanitizes every value before writing.
- Never throws on individual cell failures.
- Logs every skip and write decision.
"""

import logging
import pandas as pd

from src.config.excel_schema import FIELD_MAPPING
from src.enrichment.field_validators import validate_and_sanitize

logger = logging.getLogger("excel_updater")


def is_empty_value(value) -> bool:
    if pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def update_row(df: pd.DataFrame, index: int, entity: dict) -> pd.DataFrame:
    for source_key, target_column in FIELD_MAPPING.items():
        if target_column not in df.columns:
            continue

        raw_value = entity.get(source_key)
        if raw_value is None or (isinstance(raw_value, str) and raw_value.strip() == ""):
            continue

        current_value = df.at[index, target_column]
        if not is_empty_value(current_value):
            logger.debug(
                "skip_write: fila=%d columna=%s motivo='celda ya tenía valor: %s'",
                index, target_column, current_value,
            )
            continue

        cleaned, is_valid, reason = validate_and_sanitize(target_column, raw_value)

        if not is_valid:
            logger.warning(
                "skip_write: fila=%d columna=%s valor=%r motivo='%s'",
                index, target_column, raw_value, reason,
            )
            continue

        try:
            df.at[index, target_column] = cleaned
            logger.debug(
                "write_ok: fila=%d columna=%s valor=%r",
                index, target_column, cleaned,
            )
        except Exception as e:
            logger.error(
                "write_fail: fila=%d columna=%s valor=%r error='%s'",
                index, target_column, cleaned, e,
            )

    return df
