import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import type {
  PipelineConfig,
  PipelineEvent,
  ProcessLog,
  DetectColumnsResult,
  MappingProfile,
  DocumentResult,
  PipelineSummary,
} from "@/types/pipeline";

// ── File / folder selection ───────────────────────────────────────────────────

export async function selectExcelFile(): Promise<string | null> {
  return invoke<string | null>("select_excel_file");
}

export async function selectPdfFolder(): Promise<string | null> {
  return invoke<string | null>("select_folder");
}

export async function selectOutputFolder(): Promise<string | null> {
  return invoke<string | null>("select_folder");
}

// ── Pipeline execution ────────────────────────────────────────────────────────

export async function startPipeline(config: PipelineConfig): Promise<void> {
  return invoke("start_pipeline", { config });
}

export async function openPath(path: string): Promise<void> {
  return invoke("open_path", { path });
}

// ── Column mapping ────────────────────────────────────────────────────────────

/**
 * Run Python column detection for the given Excel file.
 * Returns detected columns and auto-suggested mappings with confidence scores.
 */
export async function detectExcelColumns(
  excelPath: string,
  pythonPath: string,
  backendPath: string,
  sheetName: number | string = 0,
  headerRow: number = 0,
): Promise<DetectColumnsResult> {
  return invoke<DetectColumnsResult>("detect_excel_columns", {
    excelPath,
    pythonPath,
    backendPath,
    sheetName: String(sheetName),
    headerRow,
  });
}

// ── Mapping profiles ──────────────────────────────────────────────────────────

export async function listMappingProfiles(
  profilesDir: string,
): Promise<MappingProfile[]> {
  return invoke<MappingProfile[]>("list_mapping_profiles", { profilesDir });
}

export async function saveMappingProfile(
  profile: MappingProfile,
  profilesDir: string,
): Promise<string> {
  return invoke<string>("save_mapping_profile", { profile, profilesDir });
}

export async function loadMappingProfile(
  profilePath: string,
): Promise<MappingProfile> {
  return invoke<MappingProfile>("load_mapping_profile", { profilePath });
}

// ── Event listeners ───────────────────────────────────────────────────────────

export interface PipelineListeners {
  onEvent: (event: PipelineEvent) => void;
  onLog: (log: ProcessLog) => void;
  onProcessExit: (result: { success: boolean; code: number | null }) => void;
  onError: (err: { error: string }) => void;
}

export async function listenToPipeline(
  listeners: PipelineListeners,
): Promise<() => void> {
  const unlisteners: UnlistenFn[] = await Promise.all([
    listen<PipelineEvent>("pipeline-event", (e) => listeners.onEvent(e.payload)),
    listen<ProcessLog>("pipeline-log", (e) => listeners.onLog(e.payload)),
    listen<{ success: boolean; code: number | null }>(
      "pipeline-process-exit",
      (e) => listeners.onProcessExit(e.payload),
    ),
    listen<{ error: string }>("pipeline-error", (e) => listeners.onError(e.payload)),
  ]);

  return () => unlisteners.forEach((fn) => fn());
}

// ── CSV / log export (browser-side) ──────────────────────────────────────────

export function exportResultsAsCsv(
  results: DocumentResult[],
  summary: PipelineSummary,
): void {
  const header = ["Archivo", "Estado", "Fila actualizada", "GPT usado", "Error"];
  const rows = results.map((r) => [
    r.file,
    r.status,
    r.row != null ? String(r.row) : "",
    r.gpt_used ? "Sí" : "No",
    r.error ?? "",
  ]);
  const summaryRows = [
    [],
    ["=== Resumen ==="],
    ["Total documentos", String(summary.total_documents)],
    ["Filas actualizadas", String(summary.updated_rows)],
    ["Sin coincidencia", String(summary.no_match)],
    ["Errores", String(summary.errors)],
    ["Llamadas GPT", String(summary.gpt_calls)],
    ["Desde caché", String(summary.cached)],
    ["Tiempo (s)", String(summary.elapsed_seconds)],
    ["Archivo de salida", summary.output_path],
  ];

  const csv = [...[header], ...rows, ...summaryRows]
    .map((row) => row.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))
    .join("\n");

  _download("﻿" + csv, `reporte_proveedores_${_today()}.csv`, "text/csv;charset=utf-8;");
}

export function exportLogsAsText(logs: ProcessLog[]): void {
  const text = logs.map((l) => `[${l.level.toUpperCase()}] ${l.message}`).join("\n");
  _download(text, `logs_proveedores_${_today()}.txt`, "text/plain;charset=utf-8;");
}

function _download(content: string, filename: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function _today(): string {
  return new Date().toISOString().slice(0, 10);
}
