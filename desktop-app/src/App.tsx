import { useState, useEffect, useCallback } from "react";
import type {
  PipelineConfig,
  PipelineEvent,
  DocumentResult,
  PipelineSummary,
  ProcessLog,
  RunState,
  AppStep,
  ColumnMapping,
  ColumnSuggestion,
} from "@/types/pipeline";
import {
  startPipeline,
  listenToPipeline,
  detectExcelColumns,
  exportLogsAsText,
} from "@/services/pipelineService";
import { FileSelectionPanel } from "@/components/FileSelectionPanel";
import { ConfigurationPanel } from "@/components/ConfigurationPanel";
import { ColumnMappingStep } from "@/components/ColumnMappingStep";
import { ProgressPanel } from "@/components/ProgressPanel";
import { LogsPanel } from "@/components/LogsPanel";
import { ResultsTable } from "@/components/ResultsTable";
import { SummaryCard } from "@/components/SummaryCard";
import { usePlatform } from "@/platform/PlatformProvider";
import { WindowsLayout } from "@/layouts/WindowsLayout";
import { UbuntuLayout } from "@/layouts/UbuntuLayout";

// ── Defaults ──────────────────────────────────────────────────────────────────

const DEFAULT_CONFIG: PipelineConfig = {
  excel_path: "",
  documents_path: "",
  output_path: "",
  execution_mode: "balanced",
  parallel_workers: 4,
  cache_enabled: true,
  use_gpt: true,
  max_gpt_doc_ratio: 0.3,
  column_mapping: {},
  sheet_name: 0,
  header_row: 0,
  export_mode: "original",
  python_path: "python",
  backend_path: "",
};

const LS_CONFIG_KEY = "act_proveedores_config_v2";
const PROFILES_DIR = "config/mappings";

function loadStoredConfig(): PipelineConfig {
  try {
    const raw = localStorage.getItem(LS_CONFIG_KEY);
    if (raw) return { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return DEFAULT_CONFIG;
}

// ── Step indicator ────────────────────────────────────────────────────────────

const STEPS: { key: AppStep; label: string; icon: string }[] = [
  { key: "setup",      label: "Configuración",  icon: "⚙" },
  { key: "mapping",    label: "Columnas",        icon: "⇄" },
  { key: "processing", label: "Procesando",      icon: "▶" },
  { key: "results",    label: "Resultados",      icon: "✓" },
];

function SidebarNav({
  current,
  onReset,
  showReset,
}: {
  current: AppStep;
  onReset: () => void;
  showReset: boolean;
}) {
  const idx = STEPS.findIndex((s) => s.key === current);
  return (
    <nav className="flex flex-col gap-1 p-4 pt-5">
      <p
        className="mb-3 px-2 text-xs font-semibold uppercase tracking-widest"
        style={{ color: "var(--app-text-muted)" }}
      >
        Pasos
      </p>
      {STEPS.map((step, i) => {
        const done = i < idx;
        const active = i === idx;
        return (
          <div
            key={step.key}
            className="flex items-center gap-2.5 rounded-md px-2 py-2"
            style={{
              background: active ? "var(--app-primary-subtle)" : "transparent",
              color: done
                ? "var(--app-success)"
                : active
                ? "var(--app-primary)"
                : "var(--app-text-disabled)",
            }}
          >
            <span className="text-sm">{done ? "✓" : step.icon}</span>
            <span className="text-sm font-medium">{step.label}</span>
          </div>
        );
      })}

      {showReset && (
        <button
          onClick={onReset}
          className="mt-4 ap-btn ap-btn-ghost ap-btn-sm w-full justify-start gap-2"
        >
          ↺ Nueva ejecución
        </button>
      )}
    </nav>
  );
}

// ── Validation ────────────────────────────────────────────────────────────────

function validateSetup(cfg: PipelineConfig): string | null {
  if (!cfg.excel_path)     return "Selecciona el archivo Excel de proveedores.";
  if (!cfg.documents_path) return "Selecciona la carpeta de documentos PDF.";
  if (!cfg.output_path)    return "Selecciona la carpeta de salida.";
  if (!cfg.python_path)    return "El ejecutable de Python no puede estar vacío.";
  if (!cfg.backend_path)   return "La carpeta raíz del backend Python no puede estar vacía.";
  return null;
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const platform = usePlatform();
  const [config, setConfig] = useState<PipelineConfig>(loadStoredConfig);
  const [step, setStep] = useState<AppStep>("setup");

  const [excelColumns, setExcelColumns] = useState<string[]>([]);
  const [suggestions, setSuggestions] = useState<ColumnSuggestion[]>([]);
  const [detectingColumns, setDetectingColumns] = useState(false);

  const [runState, setRunState] = useState<RunState>("idle");
  const [current, setCurrent] = useState(0);
  const [total, setTotal] = useState(0);
  const [currentFile, setCurrentFile] = useState<string | null>(null);
  const [results, setResults] = useState<DocumentResult[]>([]);
  const [logs, setLogs] = useState<ProcessLog[]>([]);
  const [summary, setSummary] = useState<PipelineSummary | null>(null);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    localStorage.setItem(LS_CONFIG_KEY, JSON.stringify(config));
  }, [config]);

  const updateConfig = useCallback((patch: Partial<PipelineConfig>) => {
    setConfig((prev) => ({ ...prev, ...patch }));
    setValidationError(null);
  }, []);

  const addLog = useCallback((log: ProcessLog) => {
    setLogs((prev) => [...prev, log]);
  }, []);

  async function handleProceedToMapping() {
    const err = validateSetup(config);
    if (err) { setValidationError(err); return; }

    setDetectingColumns(true);
    setValidationError(null);
    try {
      const result = await detectExcelColumns(
        config.excel_path,
        config.python_path,
        config.backend_path,
        config.sheet_name,
        config.header_row,
      );
      setExcelColumns(result.excel_columns);
      setSuggestions(result.suggestions);

      const autoMapping: ColumnMapping = {};
      for (const s of result.suggestions) {
        autoMapping[s.canonical_key] = s.excel_column;
      }
      const merged: ColumnMapping = { ...autoMapping, ...config.column_mapping };
      updateConfig({ column_mapping: merged });
      setStep("mapping");
    } catch (e) {
      setValidationError(
        `No se pudieron detectar las columnas: ${e instanceof Error ? e.message : String(e)}. ` +
        "Verifica que el ejecutable de Python y la carpeta del backend estén configurados correctamente.",
      );
    } finally {
      setDetectingColumns(false);
    }
  }

  const handleEvent = useCallback((evt: PipelineEvent) => {
    switch (evt.event) {
      case "started":
        setTotal(evt.total_documents);
        setCurrent(0);
        break;
      case "document_start":
        setCurrent(evt.current);
        setCurrentFile(evt.file);
        setResults((prev) => {
          const exists = prev.find((r) => r.file === evt.file);
          if (exists) return prev.map((r) => r.file === evt.file ? { ...r, status: "processing" } : r);
          return [...prev, { file: evt.file, status: "processing", gpt_used: false }];
        });
        addLog({ level: "info", message: `▶ Procesando: ${evt.file}` });
        break;
      case "document_done":
        setCurrent(evt.current);
        setResults((prev) =>
          prev.map((r) =>
            r.file === evt.file ? { ...r, status: evt.status, row: evt.row, error: evt.error } : r,
          ),
        );
        {
          const icons: Record<string, string> = { updated: "✅", no_match: "⚠", no_data: "○", error: "✕" };
          addLog({
            level: evt.status === "error" ? "error" : "info",
            message: `${icons[evt.status] ?? "?"} ${evt.file} → ${evt.status}${evt.row != null ? ` (fila ${evt.row})` : ""}${evt.error ? `: ${evt.error}` : ""}`,
          });
        }
        break;
      case "gpt_used":
        setResults((prev) =>
          prev.map((r) => r.file === evt.file ? { ...r, gpt_used: true } : r),
        );
        addLog({ level: "info", message: `✦ GPT: ${evt.file} (${evt.reason})` });
        break;
      case "finished":
        setRunState("finished");
        setCurrentFile(null);
        setSummary({
          total_documents: total,
          updated_rows: evt.updated_rows,
          no_match: evt.no_match,
          errors: evt.errors,
          gpt_calls: evt.gpt_calls,
          cached: evt.cached,
          elapsed_seconds: evt.elapsed_seconds,
          output_path: evt.output_path,
        });
        addLog({ level: "info", message: `🏁 Finalizado — ${evt.updated_rows} actualizados, ${evt.no_match} sin match` });
        setStep("results");
        break;
      case "error":
        setRunState("error");
        setRuntimeError(evt.message);
        addLog({ level: "error", message: `ERROR: ${evt.message}` });
        break;
    }
  }, [total, addLog]);

  async function handleStartPipeline(confirmedMapping: ColumnMapping) {
    updateConfig({ column_mapping: confirmedMapping });
    const finalConfig: PipelineConfig = { ...config, column_mapping: confirmedMapping };

    setRunState("running");
    setCurrent(0); setTotal(0); setCurrentFile(null);
    setResults([]); setLogs([]); setSummary(null);
    setRuntimeError(null);
    setStep("processing");

    const unlisten = await listenToPipeline({
      onEvent: handleEvent,
      onLog: addLog,
      onProcessExit: (result) => {
        if (!result.success && runState !== "finished") {
          setRunState("error");
          if (result.code) addLog({ level: "error", message: `Proceso terminó con código ${result.code}` });
        }
        unlisten();
      },
      onError: (err) => {
        setRunState("error");
        setRuntimeError(err.error);
        addLog({ level: "error", message: `Error: ${err.error}` });
        unlisten();
      },
    });

    try {
      await startPipeline(finalConfig);
    } catch (e) {
      setRunState("error");
      const msg = e instanceof Error ? e.message : String(e);
      setRuntimeError(msg);
      addLog({ level: "error", message: `Error al iniciar: ${msg}` });
      unlisten();
    }
  }

  function handleReset() {
    setStep("setup");
    setRunState("idle");
    setCurrent(0); setTotal(0); setCurrentFile(null);
    setResults([]); setLogs([]); setSummary(null);
    setRuntimeError(null); setValidationError(null);
    setExcelColumns([]); setSuggestions([]);
  }

  const backendPath = config.backend_path || ".";
  const profilesDir = backendPath.replace(/\\/g, "/").replace(/\/$/, "") + "/" + PROFILES_DIR;
  const showReset = step === "results" || runState === "error";

  const sidebar = (
    <SidebarNav current={step} onReset={handleReset} showReset={showReset} />
  );

  const content = (
    <div className="space-y-5">
      {/* Error banner */}
      {(validationError || runtimeError) && step !== "results" && (
        <div
          className="rounded-lg border px-5 py-3 text-sm"
          style={{
            borderColor: "var(--app-danger)",
            background: "var(--app-danger-subtle)",
            color: "var(--app-danger)",
          }}
        >
          ⚠ {validationError ?? runtimeError}
        </div>
      )}

      {/* ── Step 1: Setup ── */}
      {step === "setup" && (
        <>
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <FileSelectionPanel config={config} onChange={updateConfig} disabled={false} />
            <ConfigurationPanel config={config} onChange={updateConfig} disabled={false} />
          </div>
          <div className="flex justify-end">
            <button
              onClick={handleProceedToMapping}
              disabled={detectingColumns}
              className="ap-btn ap-btn-primary ap-btn-md px-7"
            >
              {detectingColumns ? (
                <span className="flex items-center gap-2">
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Leyendo columnas…
                </span>
              ) : (
                "Siguiente: mapear columnas →"
              )}
            </button>
          </div>
        </>
      )}

      {/* ── Step 2: Column Mapping ── */}
      {step === "mapping" && (
        <ColumnMappingStep
          excelColumns={excelColumns}
          suggestions={suggestions}
          initialMapping={config.column_mapping}
          profilesDir={profilesDir}
          onConfirm={handleStartPipeline}
          onBack={() => setStep("setup")}
        />
      )}

      {/* ── Step 3: Processing ── */}
      {step === "processing" && (
        <>
          <ProgressPanel
            current={current}
            total={total}
            currentFile={currentFile}
            runState={runState}
          />
          <ResultsTable results={results} />
          <LogsPanel logs={logs} onExport={() => exportLogsAsText(logs)} />
        </>
      )}

      {/* ── Step 4: Results ── */}
      {step === "results" && (
        <>
          {summary && <SummaryCard summary={summary} results={results} />}
          <ResultsTable results={results} />
          <LogsPanel logs={logs} onExport={() => exportLogsAsText(logs)} />
        </>
      )}

      {/* Error state mid-pipeline */}
      {runState === "error" && step === "processing" && (
        <>
          <div
            className="rounded-lg border px-5 py-4"
            style={{
              borderColor: "var(--app-danger)",
              background: "var(--app-danger-subtle)",
            }}
          >
            <p className="font-semibold" style={{ color: "var(--app-danger)" }}>
              El pipeline se detuvo por un error
            </p>
            {runtimeError && (
              <p className="mt-1 text-sm" style={{ color: "var(--app-danger)" }}>
                {runtimeError}
              </p>
            )}
          </div>
          <ResultsTable results={results} />
          <LogsPanel logs={logs} onExport={() => exportLogsAsText(logs)} />
        </>
      )}
    </div>
  );

  const Layout = platform === "windows" ? WindowsLayout : UbuntuLayout;

  return (
    <Layout sidebar={sidebar}>
      {content}
    </Layout>
  );
}
