"""
GPT client with budget tracking and structured extraction prompt.
GPT is a RESCUER, not the primary engine.
"""
import json
import re
import threading

from openai import AzureOpenAI
from src.config.settings import (
    OPENAI_API_KEY, AZURE_ENDPOINT, AZURE_API_VERSION, MODEL_NAME,
    MAX_GPT_RETRIES_PER_DOC,
)

client = AzureOpenAI(
    api_key=OPENAI_API_KEY,
    azure_endpoint=AZURE_ENDPOINT,
    api_version=AZURE_API_VERSION,
)

SYSTEM_PROMPT = """Eres un experto extractor de datos contables colombianos. Tu trabajo es leer documentos (facturas, RUTs, invoices, cuentas de cobro, recibos de servicios públicos, tiquetes aéreos, contratos, etc.) y extraer la información del PROVEEDOR o EMISOR del documento (quien emite la factura/documento, NO el cliente/adquiriente).

REGLAS DE EXTRACCIÓN:
- Busca la información del emisor/proveedor/vendedor, NO del comprador/cliente/adquiriente.
- Los datos pueden aparecer con variaciones: "Dir:", "Dirección:", "Domicilio:", "Sede:", etc.
- El NIT puede aparecer como "NIT:", "Nit.", "N.I.T.", "CC:", "C.C.", "Identificación:", o simplemente un número largo cerca del nombre.
- El teléfono puede ser "PBX:", "Tel:", "Teléfono:", "Cel:", "Celular:", "Contacto:", o un número con formato (xxx) xxx-xxxx.
- La dirección puede incluir abreviaturas colombianas: CR, CRA, CL, CLL, KR, TV, DG, AV, etc.
- El email puede estar en cualquier parte del documento.
- La ubicación/ciudad puede aparecer como "Ciudad:", "Municipio:", "Sede:", o estar dentro de la dirección.

CAMPOS A EXTRAER (devuelve TODOS, usa null si no encuentras):
{
  "empresa": "Razón social o nombre completo de la empresa/persona emisora",
  "nit": "Número de identificación tributaria (solo dígitos y guión de verificación)",
  "person_type": 1 o 2 (1=Persona Natural, 2=Persona Jurídica),
  "retention_type": 0-3 (0=Ninguna, 1=Exento, 2=Agente retenedor, 3=Autorretenedor),
  "contribution_type": 0-5 (0=No responsable IVA, 1=Responsable IVA, 2=Estatal, 3=Gran Contribuyente, 4=Régimen Simple, 5=Exento),
  "state_enterprise_type": 0-3 (0=No aplica, 1=Municipal, 2=Departamental, 3=Distrital),
  "electronic_biller": 0 o 1 (1 si factura electrónica),
  "direccion": "Dirección física completa",
  "cod_ciudad": "Código postal o código DANE si aparece",
  "ubicacion": "Ciudad, Departamento",
  "telefono": "Número(s) de teléfono",
  "email_rut": "Correo electrónico"
}

IMPORTANTE: Devuelve SOLO el JSON, sin explicaciones."""


class GPTBudget:
    def __init__(self, max_ratio: float, total_docs: int):
        self._lock = threading.Lock()
        self._max_calls = max(1, int(total_docs * max_ratio))
        self._calls_made = 0

    @property
    def calls_made(self) -> int:
        return self._calls_made

    @property
    def calls_remaining(self) -> int:
        return max(0, self._max_calls - self._calls_made)

    def can_call(self) -> bool:
        with self._lock:
            return self._calls_made < self._max_calls

    def register_call(self) -> bool:
        with self._lock:
            if self._calls_made >= self._max_calls:
                return False
            self._calls_made += 1
            return True


def extract_with_gpt(text: str, budget: GPTBudget | None = None) -> dict:
    if budget is not None:
        if not budget.register_call():
            return {}

    for attempt in range(MAX_GPT_RETRIES_PER_DOC):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Extrae los datos del proveedor/emisor:\n\n{text[:6000]}"},
                ],
            )

            content = response.choices[0].message.content.strip()
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                content = json_match.group(0)

            return json.loads(content)
        except json.JSONDecodeError:
            continue
        except Exception as e:
            if attempt == MAX_GPT_RETRIES_PER_DOC - 1:
                raise
            continue

    return {}


def extract_with_gpt_entities(text: str, budget: GPTBudget | None = None) -> list[dict]:
    result = extract_with_gpt(text, budget=budget)
    if isinstance(result, dict) and result:
        return [result]
    if isinstance(result, list):
        return result
    return []
