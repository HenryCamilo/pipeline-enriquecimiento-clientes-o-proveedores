"""
Re-exports the canonical schema constants so the rest of the codebase
can import from here without changing call sites.

The actual canonical definitions live in src/schema/canonical_schema.py.
The FIELD_MAPPING here maps extraction entity keys → canonical field keys
(not Excel column names — that translation is done by ColumnMapper at I/O time).
"""

from src.schema.canonical_schema import (
    TEXT_CANONICAL    as TEXT_COLUMNS,
    INTEGER_CANONICAL as CATEGORICAL_COLUMNS_SET,
    CANONICAL_FIELDS,
    EXTRACTION_TO_CANONICAL as FIELD_MAPPING,
)

# Re-export CATEGORICAL_COLUMNS as a dict {canonical_key: allowed_domain}
# so field_validators.py can look up allowed values.
CATEGORICAL_COLUMNS: dict[str, frozenset] = {
    key: field.domain
    for key, field in CANONICAL_FIELDS.items()
    if field.dtype == "integer" and field.domain is not None
}

__all__ = ["TEXT_COLUMNS", "CATEGORICAL_COLUMNS", "FIELD_MAPPING", "CANONICAL_FIELDS"]
