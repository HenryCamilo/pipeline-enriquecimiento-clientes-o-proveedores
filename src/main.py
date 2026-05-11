"""
Pipeline principal: extracción, matching y actualización de proveedores.
Soporta modos fast/balanced/deep, caché, paralelismo local, y budget GPT.

Comandos:
  python -m src.main                           # pipeline con .env
  python -m src.main --config cfg.json         # pipeline con config JSON
  python -m src.main --config cfg.json --json-logs
  python -m src.main detect-columns --excel f.xlsx [--sheet 0] [--header-row 0]
  python -m src.main list-profiles [--dir config/mappings]
"""

import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from src.agents.gpt_client import GPTBudget
from src.agents.mini_agent import MiniAgent
from src.cache.cache_manager import CacheManager
from src.config.settings import (
    CACHE_DIR, CACHE_ENABLED, DOCUMENTOS_PATH, EXCEL_PATH,
    EXECUTION_MODE, MAX_GPT_DOC_RATIO, OUTPUT_PATH, PARALLEL_WORKERS,
)
from src.enrichment.dataframe_normalizer import normalize_dataframe
from src.enrichment.excel_updater import update_row
from src.matching.proveedor_matcher import match_proveedor
from src.schema.column_detector import detect_columns, suggestions_to_mapping
from src.schema.column_mapper import ColumnMapper
from src.schema.mapping_profile import load_profile, list_profiles, DEFAULT_PROFILES_DIR

# ── JSON event emitter ────────────────────────────────────────────────────────

_json_logs_enabled = False


def emit(data: dict) -> None:
    if _json_logs_enabled:
        print(json.dumps(data, ensure_ascii=False), flush=True)


# ── Logging setup ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


# ── Helpers ───────────────────────────────────────────────────────────────────

def collect_pdfs(directory: str) -> list[str]:
    files = []
    for name in sorted(os.listdir(directory)):
        if name.lower().endswith(".pdf"):
            files.append(os.path.join(directory, name))
    return files


def process_single_document(path: str, mode: str) -> list[dict]:
    """Extracción standalone (sin df, sin GPT). Usada en paralelismo local."""
    agent = MiniAgent(mode=mode)
    try:
        return agent.process_file(path, df=None)
    except Exception as e:
        logger.error("Error procesando %s: %s", os.path.basename(path), e)
        return []


def needs_gpt_for_match(entity: dict, df: pd.DataFrame) -> bool:
    from src.utils.confidence import needs_gpt_review
    index = match_proveedor(df, entity)
    return needs_gpt_review(entity, index)


def _build_mapper(cfg: dict, excel_path: str, sheet_name, header_row: int) -> ColumnMapper:
    """Build ColumnMapper from config or auto-detection."""
    if "column_mapping" in cfg and cfg["column_mapping"]:
        return ColumnMapper(cfg["column_mapping"])

    if "mapping_profile" in cfg and cfg["mapping_profile"]:
        profile = load_profile(Path(cfg["mapping_profile"]))
        return ColumnMapper(profile.mapping)

    # Auto-detect
    logger.info("Detectando columnas automáticamente desde '%s'…", excel_path)
    _, suggestions = detect_columns(excel_path, sheet_name=sheet_name, header_row=header_row)
    mapping = suggestions_to_mapping(suggestions)
    if not mapping:
        # Fall back to the default profile if it exists
        default_path = DEFAULT_PROFILES_DIR / "default.yaml"
        if default_path.exists():
            logger.info("Usando perfil por defecto: %s", default_path)
            profile = load_profile(default_path)
            return ColumnMapper(profile.mapping)
    return ColumnMapper(mapping)


# ── Sub-commands ──────────────────────────────────────────────────────────────

def cmd_detect_columns(args) -> None:
    """Output JSON with detected column mapping for an Excel file."""
    from src.schema.column_detector import _cli_detect
    _cli_detect(args.excel, args.sheet, args.header_row)


def cmd_list_profiles(args) -> None:
    """Output JSON list of available mapping profiles."""
    profiles_dir = Path(args.dir)
    profiles = list_profiles(profiles_dir)
    result = [
        {
            "name": p.name,
            "description": p.description,
            "export_mode": p.export_mode,
            "mapping": p.mapping,
        }
        for p in profiles
    ]
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def main() -> None:
    global _json_logs_enabled

    parser = argparse.ArgumentParser(
        description="Pipeline de actualización de proveedores",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Sub-command: detect-columns
    p_detect = subparsers.add_parser("detect-columns", help="Detectar columnas de un Excel")
    p_detect.add_argument("--excel", required=True, help="Ruta al archivo Excel")
    p_detect.add_argument("--sheet", default=0, help="Hoja (índice o nombre)")
    p_detect.add_argument("--header-row", type=int, default=0, metavar="N",
                          help="Fila donde está el encabezado (0-indexed)")

    # Sub-command: list-profiles
    p_list = subparsers.add_parser("list-profiles", help="Listar perfiles de mapeo")
    p_list.add_argument("--dir", default=str(DEFAULT_PROFILES_DIR),
                        help="Carpeta de perfiles")

    # Default pipeline args
    parser.add_argument("--config", metavar="PATH",
                        help="Ruta al JSON de configuración")
    parser.add_argument("--json-logs", action="store_true",
                        help="Emitir eventos JSON por stdout")

    args = parser.parse_args()

    # Route sub-commands
    if args.command == "detect-columns":
        cmd_detect_columns(args)
        return
    if args.command == "list-profiles":
        cmd_list_profiles(args)
        return

    # ── Pipeline ──────────────────────────────────────────────────────────────
    _json_logs_enabled = args.json_logs

    if args.config:
        try:
            with open(args.config, encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"ERROR: no se pudo leer el config: {e}", file=sys.stderr)
            sys.exit(1)

        excel_path    = cfg.get("excel_path", EXCEL_PATH)
        docs_path     = cfg.get("documents_path", DOCUMENTOS_PATH)
        output_path   = cfg.get("output_path", OUTPUT_PATH)
        mode          = cfg.get("execution_mode", EXECUTION_MODE)
        workers       = int(cfg.get("parallel_workers", PARALLEL_WORKERS))
        cache_enabled = bool(cfg.get("cache_enabled", CACHE_ENABLED))
        use_gpt       = bool(cfg.get("use_gpt", True))
        max_gpt_ratio = float(cfg.get("max_gpt_doc_ratio", MAX_GPT_DOC_RATIO))
        sheet_name    = cfg.get("sheet_name", 0)
        header_row    = int(cfg.get("header_row", 0))
        export_mode   = cfg.get("export_mode", "original")
    else:
        cfg           = {}
        excel_path    = EXCEL_PATH
        docs_path     = DOCUMENTOS_PATH
        output_path   = OUTPUT_PATH
        mode          = EXECUTION_MODE
        workers       = PARALLEL_WORKERS
        cache_enabled = CACHE_ENABLED
        use_gpt       = True
        max_gpt_ratio = MAX_GPT_DOC_RATIO
        sheet_name    = 0
        header_row    = 0
        export_mode   = "original"

    if not use_gpt:
        max_gpt_ratio = 0.0

    t0 = time.time()
    logger.info("Modo: %s | Workers: %d | GPT: %s | Cache: %s",
                mode, workers, use_gpt, cache_enabled)

    # ── Cargar Excel ──────────────────────────────────────────────────────────
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)
    except (OSError, ValueError) as e:
        msg = f"No se pudo leer el Excel '{excel_path}': {e}"
        logger.error(msg)
        emit({"event": "error", "message": msg})
        sys.exit(1)

    original_columns = df.columns.tolist()
    df.columns = [str(col).strip() for col in df.columns]
    logger.info("Excel cargado: %d filas, %d columnas", len(df), len(df.columns))

    # ── Construir mapper y convertir a nombres canónicos ──────────────────────
    try:
        mapper = _build_mapper(cfg, excel_path, sheet_name, header_row)
    except Exception as e:
        msg = f"Error construyendo el mapeo de columnas: {e}"
        logger.error(msg)
        emit({"event": "error", "message": msg})
        sys.exit(1)

    validation_errors = mapper.validate(df)
    if validation_errors:
        for err in validation_errors:
            logger.error("Validación: %s", err)
        emit({"event": "error", "message": " | ".join(validation_errors)})
        sys.exit(1)

    df = mapper.to_canonical(df)
    df = normalize_dataframe(df)

    # ── Recolectar PDFs ───────────────────────────────────────────────────────
    try:
        pdf_files = collect_pdfs(docs_path)
    except (OSError, FileNotFoundError) as e:
        msg = f"No se pudo leer la carpeta de documentos '{docs_path}': {e}"
        logger.error(msg)
        emit({"event": "error", "message": msg})
        sys.exit(1)

    total_docs = len(pdf_files)
    logger.info("PDFs encontrados: %d", total_docs)

    if total_docs == 0:
        msg = f"No se encontraron PDFs en '{docs_path}'"
        logger.warning(msg)
        emit({"event": "error", "message": msg})
        return

    emit({"event": "started", "total_documents": total_docs})

    cache  = CacheManager(CACHE_DIR) if cache_enabled else None
    budget = GPTBudget(max_ratio=max_gpt_ratio, total_docs=total_docs)
    logger.info("GPT budget: %d llamadas máx", budget.calls_remaining)
    logger.info("-" * 60)

    # ── Fase 1: extracción paralela ───────────────────────────────────────────
    extracted: dict[str, list[dict]] = {}
    cached_count = 0

    if workers > 1 and mode != "deep":
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures: dict = {}
            for path in pdf_files:
                if cache:
                    fh = cache.get_hash(path)
                    cached = cache.load(fh)
                    if cached and cached.get("entities") is not None:
                        extracted[path] = cached["entities"]
                        cached_count += 1
                        continue
                futures[executor.submit(process_single_document, path, mode)] = path

            for future in as_completed(futures):
                path = futures[future]
                try:
                    extracted[path] = future.result()
                except Exception as e:
                    logger.error("Error paralelo %s: %s", os.path.basename(path), e)
                    extracted[path] = []
    else:
        for path in pdf_files:
            if cache:
                fh = cache.get_hash(path)
                cached_data = cache.load(fh)
                if cached_data and cached_data.get("entities") is not None:
                    extracted[path] = cached_data["entities"]
                    cached_count += 1
                    continue
            extracted[path] = process_single_document(path, mode)

    if cached_count:
        logger.info("Cache hits: %d documentos", cached_count)

    # ── Fase 2: matching + GPT rescue + actualización ─────────────────────────
    stats = {
        "procesados": 0, "actualizados": 0, "sin_match": 0,
        "errores": 0, "gpt_invocados": 0, "cached": cached_count,
    }

    agent_seq = MiniAgent(mode=mode, gpt_budget=budget, cache=cache)

    for i, path in enumerate(pdf_files, 1):
        fname = os.path.basename(path)
        entities = extracted.get(path, [])
        stats["procesados"] += 1

        emit({"event": "document_start", "current": i, "total": total_docs, "file": fname})

        if not entities:
            if mode in ("balanced", "deep") and budget.can_call():
                try:
                    entities = agent_seq.process_file(path, df=df)
                    stats["gpt_invocados"] += 1
                    emit({"event": "gpt_used", "file": fname, "reason": "entidades_vacías"})
                except Exception as e:
                    logger.error("[%s] GPT rescue: %s", fname, e)
                    stats["errores"] += 1
                    emit({"event": "document_done", "current": i, "total": total_docs,
                          "file": fname, "status": "error", "error": str(e)})
                    continue

            if not entities:
                emit({"event": "document_done", "current": i, "total": total_docs,
                      "file": fname, "status": "no_data"})
                continue

        matched_any = False
        updated_row_idx: int | None = None

        for entity in entities:
            index = match_proveedor(df, entity)
            if index is None:
                stats["sin_match"] += 1
                logger.info("[%s] Sin match: %s", fname, entity.get("empresa", "?"))
                continue

            df = update_row(df, index, entity)
            stats["actualizados"] += 1
            matched_any = True
            updated_row_idx = int(index)
            logger.info("[%s] Actualizado fila %d", fname, index)

        if not matched_any and mode in ("balanced", "deep") and budget.can_call():
            first_entity = entities[0] if entities else None
            if first_entity and needs_gpt_for_match(first_entity, df):
                try:
                    gpt_entities = agent_seq.process_file(path, df=df)
                    stats["gpt_invocados"] += 1
                    emit({"event": "gpt_used", "file": fname, "reason": "sin_match_excel"})
                    for ge in gpt_entities:
                        idx = match_proveedor(df, ge)
                        if idx is not None:
                            df = update_row(df, idx, ge)
                            stats["actualizados"] += 1
                            matched_any = True
                            updated_row_idx = int(idx)
                except Exception as e:
                    logger.warning("[%s] GPT rescue falló: %s", fname, e)

        if matched_any:
            emit({"event": "document_done", "current": i, "total": total_docs,
                  "file": fname, "status": "updated", "row": updated_row_idx})
        else:
            emit({"event": "document_done", "current": i, "total": total_docs,
                  "file": fname, "status": "no_match"})

    # ── Fase 3: exportar ──────────────────────────────────────────────────────
    if export_mode == "original":
        df_out = mapper.from_canonical(df)
        # Restore original column order (unmapped columns remain at their position)
        cols_available = [c for c in original_columns if c in df_out.columns]
        df_out = df_out[cols_available]
    else:
        df_out = df

    try:
        df_out.to_excel(output_path, index=False)
    except (OSError, PermissionError) as e:
        msg = f"No se pudo escribir el Excel de salida '{output_path}': {e}"
        logger.error(msg)
        emit({"event": "error", "message": msg})
        sys.exit(1)

    elapsed = round(time.time() - t0, 1)
    logger.info("=" * 60)
    logger.info("Archivo: %s | Tiempo: %.1fs", output_path, elapsed)
    logger.info("Docs: %d | Act: %d | Sin match: %d | Errores: %d | GPT: %d",
                stats["procesados"], stats["actualizados"], stats["sin_match"],
                stats["errores"], budget.calls_made)

    emit({
        "event": "finished",
        "output_path": output_path,
        "updated_rows": stats["actualizados"],
        "no_match": stats["sin_match"],
        "errors": stats["errores"],
        "gpt_calls": budget.calls_made,
        "cached": stats["cached"],
        "elapsed_seconds": elapsed,
    })


if __name__ == "__main__":
    main()
