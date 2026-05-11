import type { DocumentResult } from "@/types/pipeline";

interface Props {
  results: DocumentResult[];
}

const STATUS_LABEL: Record<DocumentResult["status"], string> = {
  updated: "Actualizado",
  no_match: "Sin coincidencia",
  no_data: "Sin datos",
  error: "Error",
  processing: "Procesando…",
  pending: "En espera",
};

const STATUS_CLASSES: Record<DocumentResult["status"], string> = {
  updated:
    "bg-emerald-100 text-emerald-800",
  no_match:
    "bg-amber-100 text-amber-800",
  no_data:
    "bg-gray-100 text-gray-600",
  error:
    "bg-red-100 text-red-800",
  processing:
    "bg-brand-100 text-brand-700 animate-pulse",
  pending:
    "bg-gray-50 text-gray-400",
};

export function ResultsTable({ results }: Props) {
  if (results.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm text-gray-400">
          Los resultados por documento aparecerán aquí al procesar.
        </p>
      </div>
    );
  }

  const counts: Record<string, number> = { updated: 0, no_match: 0, no_data: 0, error: 0 };
  results.forEach((r) => {
    if (r.status in counts) counts[r.status]++;
  });

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3">
        <h2 className="text-base font-semibold text-gray-900">
          Resultados por documento
        </h2>
        <div className="flex gap-3 text-xs">
          <span className="text-emerald-700">
            ✓ {counts.updated} actualizados
          </span>
          <span className="text-amber-700">
            ⚠ {counts.no_match} sin match
          </span>
          {counts.error > 0 && (
            <span className="text-red-700">✕ {counts.error} errores</span>
          )}
        </div>
      </div>

      <div className="max-h-72 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-gray-50">
            <tr>
              <th className="px-5 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                Archivo
              </th>
              <th className="px-5 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                Estado
              </th>
              <th className="px-5 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                Fila
              </th>
              <th className="px-5 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                GPT
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {results.map((r, i) => (
              <tr key={i} className="hover:bg-gray-50/60">
                <td
                  className="max-w-xs truncate px-5 py-2.5 text-gray-700"
                  title={r.file}
                >
                  {r.file}
                </td>
                <td className="px-5 py-2.5">
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_CLASSES[r.status]}`}
                  >
                    {STATUS_LABEL[r.status]}
                  </span>
                  {r.error && (
                    <p className="mt-0.5 text-xs text-red-500" title={r.error}>
                      {r.error.slice(0, 60)}…
                    </p>
                  )}
                </td>
                <td className="px-5 py-2.5 tabular-nums text-gray-500">
                  {r.row != null ? r.row : "—"}
                </td>
                <td className="px-5 py-2.5 text-gray-500">
                  {r.gpt_used ? (
                    <span className="text-brand-600">✦</span>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
