import re


def clean_value(value):
    if not value:
        return None
    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)
    return value or None


# ── Extraction helpers ──────────────────────────────────────────────

def extract_nit(text):
    # RUT form: field 5 has 9 space-separated digit boxes, field 6 has 1 DV box
    header = re.search(
        r"5\.\s*N[uú]mero de Identificaci[oó]n Tributaria\s*\(NIT\).*?\n(.+)",
        text, re.IGNORECASE,
    )
    if header:
        data_line = header.group(1)
        # Clean approach: isolated single digits (clean PDF extraction)
        isolated = re.findall(r"(?<!\d)\d(?!\d)", data_line)
        if len(isolated) >= 9:
            return "".join(isolated[:9])

        # OCR fallback: take ALL digits from the data line (handles garbled text)
        all_digits = re.findall(r"\d", data_line)
        if len(all_digits) >= 9:
            return "".join(all_digits[:9])

    match = re.search(r"NIT\s*[:\-]?\s*([\d\.\-]+)", text, re.IGNORECASE)
    return clean_value(match.group(1)) if match else None


def extract_empresa(text):
    patterns = [
        r"Raz[oó]n Social\s*[:\-]\s*(.+)",
        r"Nombre o Raz[oó]n Social\s*[:\-]\s*(.+)",
        r"Apellidos y nombres o Raz[oó]n Social\s*[:\-]\s*(.+)",
        r"35\.\s*Raz[oó]n social\s*\n(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return clean_value(match.group(1))
    return None


def extract_direccion(text):
    patterns = [
        r"41\.\s*Direcci[oó]n principal\s*\n(.+)",
        r"Direcci[oó]n Principal\s*[:\-]\s*(.+)",
        r"Direcci[oó]n\s*[:\-]\s*(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return clean_value(match.group(1))
    return None


def extract_email(text):
    match = re.search(r"42\.\s*Correo electr[oó]nico\s*(\S+@\S+)", text, re.IGNORECASE)
    if match:
        return clean_value(match.group(1))
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text, re.IGNORECASE)
    return clean_value(match.group(0)) if match else None


def extract_ubicacion(text):
    municipio = None
    departamento = None

    municipio_match = re.search(r"Municipio\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if municipio_match:
        municipio = clean_value(municipio_match.group(1))

    departamento_match = re.search(r"Departamento\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if departamento_match:
        departamento = clean_value(departamento_match.group(1))

    if municipio and departamento:
        return f"{municipio}, {departamento}"
    return municipio or departamento


def extract_telefono(text):
    match = re.search(r"Tel[eé]fono\s*[:\-]\s*([\d\+\-\(\) ]+)", text, re.IGNORECASE)
    if match:
        return clean_value(match.group(1))
    match = re.search(r"44\.\s*Tel[eé]fono\s*1\s+([\d\s]+?)(?:\s+45\.|\n)", text, re.IGNORECASE)
    if match:
        raw = re.sub(r"\s+", "", match.group(1))
        return clean_value(raw) if len(raw) >= 7 else None
    return None


# ── Block 53: Responsabilidades, Calidades y Atributos ──────────────

def extract_responsibility_codes(text: str) -> set[str]:
    """
    Extracts DIAN responsibility codes from block 53.
    Uses two complementary strategies:
    1. Parse 'XX-' description lines within the responsibilities section
    2. Parse the '53. Código' digit sequence as 2-digit pairs
    """
    codes: set[str] = set()

    section_match = re.search(
        r"Responsabilidades,?\s*Calidades\s*y\s*Atributos(.*?)Usuarios\s*aduaneros",
        text, re.DOTALL | re.IGNORECASE,
    )
    section = section_match.group(1) if section_match else text

    for m in re.finditer(r"(\d{2})\s*[-–]\s*", section):
        codes.add(m.group(1))

    codigo_match = re.search(r"53\.\s*C[oó]digo\s+([\d\s]+)", section)
    if codigo_match:
        raw = codigo_match.group(1)[:80]
        digits = re.findall(r"\d", raw)
        for i in range(0, min(len(digits) - 1, 52), 2):
            codes.add(digits[i] + digits[i + 1])

    return codes


def infer_retention_type_from_responsibilities(codes: set[str], text: str) -> int:
    upper = text.upper()

    if "15" in codes or "AUTORRETENEDOR" in upper or "AUTORRETENEDOR ESPECIAL" in upper:
        return 3

    if (
        "07" in codes
        or "09" in codes
        or "RETENCIÓN EN LA FUENTE" in upper
        or "RETENCION EN LA FUENTE" in upper
        or "AGENTE RETENEDOR" in upper
        or "AGENTES RETENEDORES" in upper
    ):
        return 2

    if "EXENTO DE RETENCIÓN" in upper or "EXENTO DE RETENCION" in upper:
        return 1

    return 0


# ── Apartados 39 / 40: Departamento y Ciudad/Municipio ──────────────

def extract_location_codes(text: str) -> tuple[str | None, str | None]:
    """
    Extracts department code (apartado 39) and municipality code (apartado 40)
    from the UBICACIÓN data line.

    Format observed in extracted text:
      38. País 39. Departamento 40. Ciudad/Municipio
      COLOMBIA 1 6 9 [DeptName] D D [CityName] C C C

    Isolated single digits follow the pattern: 3 (country) + 2 (dept) + 3 (muni).
    """
    header_pattern = (
        r"38\.\s*Pa[ií]s\s+39\.\s*Departamento\s+40\.\s*Ciudad/Municipio\s*\n(.+)"
    )
    m = re.search(header_pattern, text, re.IGNORECASE)
    if not m:
        return None, None

    data_line = m.group(1).strip()

    digits = re.findall(r"(?<!\d)\d(?!\d)", data_line)

    if len(digits) >= 8:
        dept_code = digits[3] + digits[4]
        muni_code = digits[5] + digits[6] + digits[7]
        return dept_code, muni_code

    if len(digits) >= 5:
        dept_code = digits[-5] + digits[-4]
        muni_code = digits[-3] + digits[-2] + digits[-1]
        return dept_code, muni_code

    return None, None


def build_cod_ciudad(dept_code: str | None, muni_code: str | None) -> str | None:
    if dept_code and muni_code:
        return dept_code + muni_code
    return None


def infer_state_enterprise_type_from_rut(muni_code: str | None) -> int:
    """
    Uses only the apartado 40 (municipality) code:
      001 → 2 (Departamental)
      anything else → 1 (Municipal)
      None → 0 (No aplica)
    """
    if not muni_code:
        return 0
    if muni_code == "001":
        return 2
    return 1


# ── Generic inferences (text-based, used as fallback) ────────────────

def infer_person_type(empresa: str | None):
    if not empresa:
        return None
    upper = empresa.upper()
    juridico_keywords = ["SAS", "S.A.", "LTDA", "S EN C", "S.A.S", "S A S", "S.A", "SAS.", "E.S.P"]
    if any(keyword in upper for keyword in juridico_keywords):
        return 2
    return 1


def infer_electronic_biller(text: str, codes: set[str] | None = None):
    if codes and "52" in codes:
        return 1
    upper = text.upper()
    if "FACTURADOR ELECTRONICO" in upper or "FACTURADOR ELECTRÓNICO" in upper:
        return 1
    return None


def infer_contribution_type(text: str):
    upper = text.upper()
    if "GRAN CONTRIBUYENTE" in upper:
        return 3
    if "REGIMEN SIMPLE" in upper or "RÉGIMEN SIMPLE" in upper:
        return 4
    if "NO RESPONSABLE DE IVA" in upper:
        return 0
    if "RESPONSABLE DE IVA" in upper or "RESPONSABLES DE IVA" in upper:
        return 1
    if "EXENTO" in upper and "RETENCI" not in upper:
        return 5
    return None


# ── Main parser ──────────────────────────────────────────────────────

def parse_rut(text: str) -> dict:
    empresa = extract_empresa(text)
    codes = extract_responsibility_codes(text)
    dept_code, muni_code = extract_location_codes(text)

    return {
        "nit": extract_nit(text),
        "empresa": empresa,
        "person_type": infer_person_type(empresa),
        "retention_type": infer_retention_type_from_responsibilities(codes, text),
        "contribution_type": infer_contribution_type(text),
        "state_enterprise_type": infer_state_enterprise_type_from_rut(muni_code),
        "electronic_biller": infer_electronic_biller(text, codes),
        "direccion": extract_direccion(text),
        "cod_ciudad": build_cod_ciudad(dept_code, muni_code),
        "ubicacion": extract_ubicacion(text),
        "telefono": extract_telefono(text),
        "email_rut": extract_email(text),
        "fuente": "rut",
    }
