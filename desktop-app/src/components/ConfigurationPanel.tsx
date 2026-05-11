import type { PipelineConfig } from "@/types/pipeline";

interface Props {
  config: PipelineConfig;
  onChange: (patch: Partial<PipelineConfig>) => void;
  disabled: boolean;
}

function Toggle({
  label,
  description,
  checked,
  onToggle,
  disabled,
}: {
  label: string;
  description: string;
  checked: boolean;
  onToggle: () => void;
  disabled: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-gray-800">{label}</p>
        <p className="text-xs text-gray-500">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={onToggle}
        disabled={disabled}
        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-40 ${
          checked ? "bg-brand-600" : "bg-gray-200"
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition duration-200 ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );
}

export function ConfigurationPanel({ config, onChange, disabled }: Props) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <h2 className="mb-5 text-base font-semibold text-gray-900">
        Configuración de ejecución
      </h2>

      <div className="flex flex-col gap-6">
        {/* Modo de ejecución */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700">
            Modo de ejecución
          </label>
          <div className="grid grid-cols-3 gap-2">
            {(["fast", "balanced", "deep"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => onChange({ execution_mode: mode })}
                disabled={disabled}
                className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-40 ${
                  config.execution_mode === mode
                    ? "border-brand-600 bg-brand-600 text-white"
                    : "border-gray-300 bg-white text-gray-700 hover:border-brand-400"
                }`}
              >
                {mode === "fast" && "⚡ Rápido"}
                {mode === "balanced" && "⚖️ Balanceado"}
                {mode === "deep" && "🔍 Profundo"}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-400">
            {config.execution_mode === "fast" &&
              "Solo regex, sin OCR pesado ni GPT. Más rápido."}
            {config.execution_mode === "balanced" &&
              "Regex + OCR selectivo + GPT como rescate cuando falla."}
            {config.execution_mode === "deep" &&
              "OCR completo en todas las páginas + GPT agresivo. Más lento."}
          </p>
        </div>

        <div className="h-px bg-gray-100" />

        {/* Workers paralelos */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">
              Workers paralelos
            </label>
            <span className="rounded-full bg-brand-100 px-2.5 py-0.5 text-sm font-semibold text-brand-700">
              {config.parallel_workers}
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={8}
            step={1}
            value={config.parallel_workers}
            onChange={(e) =>
              onChange({ parallel_workers: Number(e.target.value) })
            }
            disabled={disabled || config.execution_mode === "deep"}
            className="h-2 w-full cursor-pointer accent-brand-600 disabled:opacity-40"
          />
          <div className="flex justify-between text-xs text-gray-400">
            <span>1</span>
            <span>8</span>
          </div>
          {config.execution_mode === "deep" && (
            <p className="text-xs text-amber-600">
              En modo profundo el paralelismo se desactiva automáticamente.
            </p>
          )}
        </div>

        <div className="h-px bg-gray-100" />

        {/* Toggles */}
        <div className="flex flex-col gap-4">
          <Toggle
            label="Caché de documentos"
            description="Evita reprocesar PDFs que no cambiaron (recomendado)"
            checked={config.cache_enabled}
            onToggle={() => onChange({ cache_enabled: !config.cache_enabled })}
            disabled={disabled}
          />

          <Toggle
            label="Usar GPT"
            description="Activa el rescate con IA cuando regex y OCR fallan"
            checked={config.use_gpt}
            onToggle={() => onChange({ use_gpt: !config.use_gpt })}
            disabled={disabled}
          />

          {config.use_gpt && (
            <div className="ml-4 flex flex-col gap-2 border-l-2 border-brand-200 pl-4">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-700">
                  Ratio máx. de llamadas GPT
                </label>
                <span className="rounded-full bg-brand-100 px-2.5 py-0.5 text-sm font-semibold text-brand-700">
                  {Math.round(config.max_gpt_doc_ratio * 100)}%
                </span>
              </div>
              <input
                type="range"
                min={0.05}
                max={1}
                step={0.05}
                value={config.max_gpt_doc_ratio}
                onChange={(e) =>
                  onChange({ max_gpt_doc_ratio: Number(e.target.value) })
                }
                disabled={disabled}
                className="h-2 w-full cursor-pointer accent-brand-600 disabled:opacity-40"
              />
              <p className="text-xs text-gray-400">
                GPT se invocará en como máximo el{" "}
                {Math.round(config.max_gpt_doc_ratio * 100)}% de los documentos.
              </p>
            </div>
          )}
        </div>

        <div className="h-px bg-gray-100" />

        {/* Ajustes avanzados de entorno */}
        <details className="group">
          <summary className="cursor-pointer text-sm font-medium text-gray-700 group-open:text-brand-600">
            ⚙ Ajustes avanzados (Python / entorno)
          </summary>
          <div className="mt-4 flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700">
                Ejecutable de Python
              </label>
              <input
                type="text"
                className="rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:opacity-50"
                value={config.python_path}
                onChange={(e) => onChange({ python_path: e.target.value })}
                disabled={disabled}
                placeholder="python"
              />
              <p className="text-xs text-gray-400">
                En Windows con WSL: <code>wsl -e python3</code> — en Linux/Mac:{" "}
                <code>python3</code>
              </p>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700">
                Carpeta raíz del backend Python
              </label>
              <input
                type="text"
                className="rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:opacity-50"
                value={config.backend_path}
                onChange={(e) => onChange({ backend_path: e.target.value })}
                disabled={disabled}
                placeholder="/ruta/al/proyecto/python"
              />
              <p className="text-xs text-gray-400">
                Carpeta que contiene <code>src/main.py</code>
              </p>
            </div>
          </div>
        </details>
      </div>
    </div>
  );
}
