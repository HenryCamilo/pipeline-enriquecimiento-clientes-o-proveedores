import os
from dotenv import load_dotenv

load_dotenv()

# --- Azure OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2025-01-01-preview")
MODEL_NAME = os.getenv("AZURE_DEPLOYMENT", "gpt-5-nano")

# --- Execution mode: "fast", "balanced", "deep" ---
EXECUTION_MODE = os.getenv("EXECUTION_MODE", "balanced")

# --- GPT budget / limits ---
MAX_GPT_DOC_RATIO = float(os.getenv("MAX_GPT_DOC_RATIO", "0.3"))
MAX_GPT_PAGES_PER_DOC = int(os.getenv("MAX_GPT_PAGES_PER_DOC", "3"))
MAX_GPT_RETRIES_PER_DOC = int(os.getenv("MAX_GPT_RETRIES_PER_DOC", "1"))

# --- Parallelism ---
PARALLEL_WORKERS = int(os.getenv("PARALLEL_WORKERS", "4"))

# --- Cache ---
CACHE_DIR = os.getenv("CACHE_DIR", "cache")
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"

# --- Paths ---
EXCEL_PATH = os.getenv("EXCEL_PATH", "data/raw/excel/proveedores.xlsx")
DOCUMENTOS_PATH = os.getenv("DOCUMENTOS_PATH", "data/raw/facturas/")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "data/raw/proveedores_actualizado.xlsx")
