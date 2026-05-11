// ── Campos canónicos del pipeline ─────────────────────────────────────────────

export type CanonicalKey =
  | "supplier_name"
  | "tax_id"
  | "address"
  | "phone"
  | "email"
  | "city"
  | "city_code"
  | "person_type"
  | "retention_type"
  | "contribution_type"
  | "state_enterprise_type"
  | "electronic_biller";

export const CANONICAL_FIELD_LABELS: Record<CanonicalKey, string> = {
  supplier_name:          "Nombre del proveedor",
  tax_id:                 "NIT / Documento",
  address:                "Dirección",
  phone:                  "Teléfono",
  email:                  "Email",
  city:                   "Ciudad / Ubicación",
  city_code:              "Código ciudad",
  person_type:            "Tipo persona",
  retention_type:         "Tipo retención",
  contribution_type:      "Tipo contribución",
  state_enterprise_type:  "Tipo empresa estatal",
  electronic_biller:      "Facturador electrónico",
};

export const IDENTITY_CANONICAL_KEYS: CanonicalKey[] = ["tax_id", "supplier_name"];

// ── Column mapping ─────────────────────────────────────────────────────────────

/** canonical_key → original Excel column name */
export type ColumnMapping = Partial<Record<CanonicalKey, string>>;

export interface ColumnSuggestion {
  canonical_key: CanonicalKey;
  excel_column: string;
  confidence: number;   // 0.0 – 1.0
  method: "exact" | "fuzzy";
}

export interface DetectColumnsResult {
  excel_columns: string[];
  suggestions: ColumnSuggestion[];
}

// ── Mapping profile ───────────────────────────────────────────────────────────

export interface MappingProfile {
  name: string;
  description: string;
  mapping: ColumnMapping;
  sheet_name: number | string;
  header_row: number;
  export_mode: "original" | "canonical";
}

// ── Configuración que se escribe en config.json temporal ─────────────────────

export interface PipelineConfig {
  excel_path: string;
  documents_path: string;
  output_path: string;
  execution_mode: "fast" | "balanced" | "deep";
  parallel_workers: number;
  cache_enabled: boolean;
  use_gpt: boolean;
  max_gpt_doc_ratio: number;
  /** canonical_key → original Excel column name */
  column_mapping: ColumnMapping;
  sheet_name: number | string;
  header_row: number;
  export_mode: "original" | "canonical";
  /** Ejecutable de Python. Ej: "python", "python3", "wsl -e python3" */
  python_path: string;
  /** Carpeta raíz del proyecto Python backend */
  backend_path: string;
}

// ── Eventos emitidos por el pipeline Python (--json-logs) ────────────────────

export interface EvStarted {
  event: "started";
  total_documents: number;
}

export interface EvDocumentStart {
  event: "document_start";
  current: number;
  total: number;
  file: string;
}

export type DocumentStatus = "updated" | "no_match" | "no_data" | "error";

export interface EvDocumentDone {
  event: "document_done";
  current: number;
  total: number;
  file: string;
  status: DocumentStatus;
  row?: number;
  error?: string;
}

export interface EvGptUsed {
  event: "gpt_used";
  file: string;
  reason: string;
}

export interface EvFinished {
  event: "finished";
  output_path: string;
  updated_rows: number;
  no_match: number;
  errors: number;
  gpt_calls: number;
  cached: number;
  elapsed_seconds: number;
}

export interface EvError {
  event: "error";
  message: string;
}

export type PipelineEvent =
  | EvStarted
  | EvDocumentStart
  | EvDocumentDone
  | EvGptUsed
  | EvFinished
  | EvError;

// ── Log libre (stdout/stderr no-JSON del proceso Python) ─────────────────────

export interface ProcessLog {
  level: "info" | "error";
  message: string;
}

// ── Resultado por documento (para la tabla de resultados) ────────────────────

export interface DocumentResult {
  file: string;
  status: DocumentStatus | "processing" | "pending";
  row?: number;
  error?: string;
  gpt_used: boolean;
}

// ── Resumen final del pipeline ────────────────────────────────────────────────

export interface PipelineSummary {
  total_documents: number;
  updated_rows: number;
  no_match: number;
  errors: number;
  gpt_calls: number;
  cached: number;
  elapsed_seconds: number;
  output_path: string;
}

// ── Estado global de ejecución ────────────────────────────────────────────────

export type RunState = "idle" | "running" | "finished" | "error";

export type AppStep = "setup" | "mapping" | "processing" | "results";
