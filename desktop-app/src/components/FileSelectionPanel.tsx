import type { PipelineConfig } from "@/types/pipeline";
import { selectExcelFile, selectPdfFolder, selectOutputFolder } from "@/services/pipelineService";

interface Props {
  config: PipelineConfig;
  onChange: (patch: Partial<PipelineConfig>) => void;
  disabled: boolean;
}

function PathField({
  label,
  value,
  placeholder,
  onBrowse,
  disabled,
  accept,
}: {
  label: string;
  value: string;
  placeholder: string;
  onBrowse: () => void;
  disabled: boolean;
  accept?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-gray-700">{label}</label>
      <div className="flex gap-2">
        <input
          type="text"
          className="flex-1 rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-800 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:opacity-50"
          value={value}
          placeholder={placeholder}
          readOnly
          disabled={disabled}
          title={value}
        />
        <button
          onClick={onBrowse}
          disabled={disabled}
          className="shrink-0 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-40"
        >
          Examinar
        </button>
      </div>
      {accept && (
        <p className="text-xs text-gray-400">{accept}</p>
      )}
    </div>
  );
}

export function FileSelectionPanel({ config, onChange, disabled }: Props) {
  async function handleSelectExcel() {
    const path = await selectExcelFile();
    if (path) onChange({ excel_path: path });
  }

  async function handleSelectPdfs() {
    const path = await selectPdfFolder();
    if (path) onChange({ documents_path: path });
  }

  async function handleSelectOutput() {
    const path = await selectOutputFolder();
    if (path) {
      // Construye el path de salida como carpeta/proveedores_actualizado.xlsx
      const sep = path.includes("/") ? "/" : "\\";
      onChange({ output_path: `${path}${sep}proveedores_actualizado.xlsx` });
    }
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <h2 className="mb-5 text-base font-semibold text-gray-900">
        Archivos y carpetas
      </h2>

      <div className="flex flex-col gap-5">
        <PathField
          label="Excel de proveedores"
          value={config.excel_path}
          placeholder="Selecciona el archivo .xlsx con los proveedores"
          onBrowse={handleSelectExcel}
          disabled={disabled}
          accept="Formatos: .xlsx, .xls"
        />

        <PathField
          label="Carpeta de documentos (PDFs)"
          value={config.documents_path}
          placeholder="Selecciona la carpeta con facturas, RUTs e invoices"
          onBrowse={handleSelectPdfs}
          disabled={disabled}
          accept="Se procesan todos los .pdf dentro de la carpeta"
        />

        <PathField
          label="Carpeta de salida"
          value={config.output_path}
          placeholder="Selecciona dónde guardar el Excel actualizado"
          onBrowse={handleSelectOutput}
          disabled={disabled}
          accept="Se creará proveedores_actualizado.xlsx en la carpeta elegida"
        />
      </div>
    </div>
  );
}
