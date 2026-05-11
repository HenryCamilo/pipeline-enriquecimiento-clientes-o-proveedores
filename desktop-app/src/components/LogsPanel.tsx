import { useEffect, useRef } from "react";
import type { ProcessLog } from "@/types/pipeline";

interface Props {
  logs: ProcessLog[];
  onExport: () => void;
}

export function LogsPanel({ logs, onExport }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <div className="flex flex-col rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3">
        <h2 className="text-base font-semibold text-gray-900">
          Logs en tiempo real
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">{logs.length} líneas</span>
          <button
            onClick={onExport}
            disabled={logs.length === 0}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:border-gray-400 hover:text-gray-800 disabled:opacity-40"
          >
            Guardar logs
          </button>
        </div>
      </div>

      <div className="h-56 overflow-y-auto bg-gray-950 p-4 font-mono text-xs">
        {logs.length === 0 ? (
          <p className="text-gray-500 italic">
            Los logs del proceso Python aparecerán aquí…
          </p>
        ) : (
          logs.map((log, i) => (
            <div
              key={i}
              className={`leading-5 ${
                log.level === "error" ? "text-red-400" : "text-gray-300"
              }`}
            >
              <span className="mr-2 text-gray-600">
                {String(i + 1).padStart(4, " ")}
              </span>
              {log.message}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
