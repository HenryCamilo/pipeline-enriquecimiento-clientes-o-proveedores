"""
Casts canonical target columns to safe dtypes when loading the DataFrame.
Text columns → object/str, integer columns → Int64 (nullable integer).
Non-canonical columns are left untouched.
"""

import pandas as pd

from src.config.excel_schema import TEXT_COLUMNS, CATEGORICAL_COLUMNS


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    for col in TEXT_COLUMNS:
        if col not in df.columns:
            continue
        df[col] = df[col].astype(object)
        df[col] = df[col].where(df[col].notna(), other=None)

    for col in CATEGORICAL_COLUMNS:
        if col not in df.columns:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df[col] = df[col].astype("Int64")

    return df
