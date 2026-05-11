"""
Canonical field definitions for the supplier pipeline.

Every module that reads or writes the in-memory DataFrame uses these names.
Original Excel column names are mapped to/from canonical names at I/O time
via ColumnMapper, so no business logic ever hardcodes Excel column names.
"""

from dataclasses import dataclass
from typing import Optional, FrozenSet


@dataclass(frozen=True)
class CanonicalField:
    key: str
    label_es: str
    dtype: str                          # "text" | "integer"
    domain: Optional[FrozenSet] = None  # allowed integer values
    identity: bool = False              # True = used for matching (NIT or name)


CANONICAL_FIELDS: dict[str, CanonicalField] = {
    "supplier_name": CanonicalField(
        "supplier_name", "Nombre del proveedor", "text", identity=True,
    ),
    "tax_id": CanonicalField(
        "tax_id", "NIT / Documento", "text", identity=True,
    ),
    "address": CanonicalField(
        "address", "Dirección", "text",
    ),
    "phone": CanonicalField(
        "phone", "Teléfono", "text",
    ),
    "email": CanonicalField(
        "email", "Email", "text",
    ),
    "city": CanonicalField(
        "city", "Ciudad / Ubicación", "text",
    ),
    "city_code": CanonicalField(
        "city_code", "Código ciudad", "text",
    ),
    "person_type": CanonicalField(
        "person_type", "Tipo persona", "integer",
        domain=frozenset({1, 2}),
    ),
    "retention_type": CanonicalField(
        "retention_type", "Tipo retención", "integer",
        domain=frozenset({0, 1, 2, 3}),
    ),
    "contribution_type": CanonicalField(
        "contribution_type", "Tipo contribución", "integer",
        domain=frozenset({0, 1, 2, 3, 4, 5}),
    ),
    "state_enterprise_type": CanonicalField(
        "state_enterprise_type", "Tipo empresa estatal", "integer",
        domain=frozenset({0, 1, 2, 3}),
    ),
    "electronic_biller": CanonicalField(
        "electronic_biller", "Facturador electrónico", "integer",
        domain=frozenset({0, 1}),
    ),
}

# Extraction entity keys (from regex/GPT) → canonical field keys
# Only the entity keys that actually map to writable Excel columns.
EXTRACTION_TO_CANONICAL: dict[str, str] = {
    "empresa":               "supplier_name",
    "direccion":             "address",
    "telefono":              "phone",
    "email_rut":             "email",
    "ubicacion":             "city",
    "cod_ciudad":            "city_code",
    "person_type":           "person_type",
    "retention_type":        "retention_type",
    "contribution_type":     "contribution_type",
    "state_enterprise_type": "state_enterprise_type",
    "electronic_biller":     "electronic_biller",
}

TEXT_CANONICAL    = {k for k, f in CANONICAL_FIELDS.items() if f.dtype == "text"}
INTEGER_CANONICAL = {k for k, f in CANONICAL_FIELDS.items() if f.dtype == "integer"}
IDENTITY_FIELDS   = {k for k, f in CANONICAL_FIELDS.items() if f.identity}
