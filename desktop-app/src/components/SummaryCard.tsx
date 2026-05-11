import type { PipelineSummary } from "@/types/pipeline";
import { openPath, exportResultsAsCsv } from "@/services/pipelineService";
import type { DocumentResult } from "@/types/pipeline";

interface Props {
  summary: PipelineSummary;
  results: DocumentResult[];
}

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-gray-100 bg-gray-50 px-4 py-4">
      <span
        className={`text-2xl font-bold tabular-nums ${color ?? "text-gray-800"}`}
      >
        {value}
      </span>
      <span className="mt-1 text-center text-xs text-gray-500">{label}</span>
    </div>
  );
}

export function SummaryCard({ summary, results }: Props) {
  async function handleOpenExcel() {
    await openPath(summary.output_path);
  }

  async function handleOpenFolder() {
    const parts = summary.output_path.replace(/\\/g, "/").split("/");
    parts.pop();
    await openPath(parts.join("/") || summary.output_path);
  }

  function handleExportCsv() {
    exportResultsAsCsv(results, summary);
  }

  const minutes = Math.floor(summary.elapsed_seconds / 60);
  const seconds = Math.round(summary.elapsed_seconds % 60);
  const elapsed =
    minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;

  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-6 shadow-sm">
      <div className="mb-5 flex items-center gap-2">
        <span className="text-2xl">✅</span>
        <h2 className="text-base font-semibold text-emerald-900">
          Procesamiento completado en {elapsed}
        </h2>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Stat
          label="Documentos"
          value={summary.total_documents}
          color="text-gray-800"
        />
        <Stat
          label="Filas actualizadas"
          value={summary.updated_rows}
          color="text-emerald-700"
        />
        <Stat
          label="Sin coincidencia"
          value={summary.no_match}
          color="text-amber-700"
        />
        <Stat
          label="Errores"
          value={summary.errors}
          color={summary.errors > 0 ? "text-red-700" : "text-gray-400"}
        />
        <Stat
          label="Llamadas GPT"
          value={summary.gpt_calls}
          color="text-brand-700"
        />
        <Stat
          label="Desde caché"
          value={summary.cached}
          color="text-gray-600"
        />
      </div>

      <div className="mb-4 rounded-lg border border-emerald-200 bg-white px-4 py-2.5 text-sm text-gray-600">
        📁 Salida:{" "}
        <span className="font-medium text-gray-800">{summary.output_path}</span>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          onClick={handleOpenExcel}
          className="rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          📊 Abrir Excel actualizado
        </button>
        <button
          onClick={handleOpenFolder}
          className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-400"
        >
          📂 Abrir carpeta de salida
        </button>
        <button
          onClick={handleExportCsv}
          className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-400"
        >
          ⬇ Exportar reporte CSV
        </button>
      </div>
    </div>
  );
}
