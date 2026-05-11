interface Props {
  current: number;
  total: number;
  currentFile: string | null;
  runState: "idle" | "running" | "finished" | "error";
}

export function ProgressPanel({
  current,
  total,
  currentFile,
  runState,
}: Props) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;

  const stateLabel: Record<string, string> = {
    idle: "En espera",
    running: "Procesando…",
    finished: "Completado",
    error: "Error",
  };

  const stateColor: Record<string, string> = {
    idle: "text-gray-500",
    running: "text-brand-600",
    finished: "text-emerald-600",
    error: "text-red-600",
  };

  const barColor: Record<string, string> = {
    idle: "bg-gray-300",
    running: "bg-brand-500",
    finished: "bg-emerald-500",
    error: "bg-red-500",
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">Progreso</h2>
        <span className={`text-sm font-medium ${stateColor[runState]}`}>
          {stateLabel[runState]}
        </span>
      </div>

      {/* Barra de progreso */}
      <div className="mb-2 h-3 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className={`h-full rounded-full transition-all duration-300 ${barColor[runState]}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-500">
          {runState === "idle"
            ? "—"
            : currentFile
              ? `📄 ${currentFile}`
              : runState === "finished"
                ? "Todos los documentos procesados"
                : "Inicializando…"}
        </span>
        <span className="font-semibold tabular-nums text-gray-700">
          {total > 0 ? `${current} / ${total}` : "—"}{" "}
          <span className="font-normal text-gray-400">({pct}%)</span>
        </span>
      </div>

      {/* Spinner animado mientras corre */}
      {runState === "running" && (
        <div className="mt-3 flex items-center gap-2 text-xs text-gray-400">
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-brand-300 border-t-brand-600" />
          Procesando documentos en segundo plano…
        </div>
      )}
    </div>
  );
}
