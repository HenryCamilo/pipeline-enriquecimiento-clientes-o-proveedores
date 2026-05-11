"""
Determines whether GPT review is needed for a given entity + match result.
Returns False if there's enough confidence to skip GPT entirely.
"""

import re


def _has_valid_nit(entity: dict) -> bool:
    nit = entity.get("nit")
    if not nit:
        return False
    digits = re.sub(r"[^\d]", "", str(nit))
    return len(digits) >= 5


def _has_valid_name(entity: dict) -> bool:
    name = entity.get("empresa")
    if not name:
        return False
    return len(str(name).strip()) >= 3


def _count_useful_fields(entity: dict) -> int:
    useful_keys = [
        "nit", "empresa", "direccion", "telefono",
        "email_rut", "ubicacion", "person_type",
    ]
    count = 0
    for key in useful_keys:
        val = entity.get(key)
        if val is not None and str(val).strip():
            count += 1
    return count


def needs_gpt_review(
    entity: dict | None,
    match_index: int | None,
    min_useful_fields: int = 3,
) -> bool:
    if entity is None:
        return True

    has_nit = _has_valid_nit(entity)
    has_name = _has_valid_name(entity)
    has_match = match_index is not None
    useful_count = _count_useful_fields(entity)

    if has_nit and has_name and has_match:
        return False

    if has_nit and has_match and useful_count >= min_useful_fields:
        return False

    if has_name and has_match and useful_count >= min_useful_fields:
        return False

    if useful_count >= min_useful_fields + 1 and (has_nit or has_name):
        return False

    return True
