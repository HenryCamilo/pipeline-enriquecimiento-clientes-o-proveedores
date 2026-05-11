import { useState, useEffect } from "react";
import type {
  CanonicalKey,
  ColumnMapping,
  ColumnSuggestion,
  MappingProfile,
} from "@/types/pipeline";
import { CANONICAL_FIELD_LABELS, IDENTITY_CANONICAL_KEYS } from "@/types/pipeline";
import {
  saveMappingProfile,
  listMappingProfiles,
} from "@/services/pipelineService";

interface Props {
  excelColumns: string[];
  suggestions: ColumnSuggestion[];
  initialMapping: ColumnMapping;
  profilesDir: string;
  onConfirm: (mapping: ColumnMapping) => void;
  onBack: () => void;
}

const ALL_CANONICAL_KEYS = Object.keys(CANONICAL_FIELD_LABELS) as CanonicalKey[];

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 90 ? "bg-emerald-100 text-emerald-700"
    : pct >= 65 ? "bg-amber-100 text-amber-700"
    : "bg-red-100 text-red-700";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>
      {pct}%
    </span>
  );
}

export function ColumnMappingStep({
  excelColumns,
  suggestions,
  initialMapping,
  profilesDir,
  onConfirm,
  onBack,
}: Props) {
  const [mapping, setMapping] = useState<ColumnMapping>(initialMapping);
  const [profiles, setProfiles] = useState<MappingProfile[]>([]);
  const [saveName, setSaveName] = useState("");
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Build confidence map from suggestions
  const confidenceMap = Object.fromEntries(
    suggestions.map((s) => [s.canonical_key, s.confidence]),
  ) as Partial<Record<CanonicalKey, number>>;

  useEffect(() => {
    listMappingProfiles(profilesDir)
      .then(setProfiles)
      .catch(() => setProfiles([]));
  }, [profilesDir]);

  function handleColumnChange(canonicalKey: CanonicalKey, value: string) {
    setMapping((prev) => {
      const next = { ...prev };
      if (value === "") {
        delete next[canonicalKey];
      } else {
        next[canonicalKey] = value;
      }
      return next;
    });
    setValidationError(null);
  }

  function handleLoadProfile(profile: MappingProfile) {
    const m: ColumnMapping = {};
    for (const [k, v] of Object.entries(profile.mapping)) {
      if (typeof v === "string") m[k as CanonicalKey] = v;
    }
    setMapping(m);
    setValidationError(null);
  }

  function validate(): boolean {
    const hasIdentity = IDENTITY_CANONICAL_KEYS.some((k) => mapping[k]);
    if (!hasIdentity) {
      setValidationError(
        "Debes mapear al menos 'NIT / Documento' (tax_id) o 'Nombre del proveedor' (supplier_name).",
      );
      return false;
    }
    // Check no duplicate Excel columns
    const seen = new Map<string, CanonicalKey>();
    for (const [k, v] of Object.entries(mapping)) {
      if (!v) continue;
      if (seen.has(v)) {
        setValidationError(
          `La columna Excel '${v}' está asignada a dos campos: '${seen.get(v)}' y '${k}'.`,
        );
        return false;
      }
      seen.set(v, k as CanonicalKey);
    }
    return true;
  }

  async function handleSaveProfile() {
    if (!saveName.trim()) {
      setSaveStatus("Escribe un nombre para el perfil.");
      return;
    }
    const profile: MappingProfile = {
      name: saveName.trim(),
      description: "",
      mapping,
      sheet_name: 0,
      header_row: 0,
      export_mode: "original",
    };
    try {
      await saveMappingProfile(profile, profilesDir);
      setSaveStatus(`Perfil '${profile.name}' guardado.`);
      const updated = await listMappingProfiles(profilesDir);
      setProfiles(updated);
      setSaveName("");
    } catch (e) {
      setSaveStatus(`Error al guardar: ${e}`);
    }
  }

  function handleConfirm() {
    if (validate()) onConfirm(mapping);
  }

  const mappedCount = Object.values(mapping).filter(Boolean).length;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-gray-900">
              Mapeo de columnas
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Indica qué columna de tu Excel corresponde a cada campo del pipeline.
              Los campos marcados con{" "}
              <span className="font-semibold text-brand-600">*</span> son de
              identidad (necesitas al menos uno).
            </p>
          </div>
          <span className="shrink-0 rounded-full bg-brand-100 px-3 py-1 text-sm font-medium text-brand-700">
            {mappedCount} / {ALL_CANONICAL_KEYS.length} mapeados
          </span>
        </div>

        {/* Load profile */}
        {profiles.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-sm text-gray-500">Cargar plantilla:</span>
            {profiles.map((p) => (
              <button
                key={p.name}
                onClick={() => handleLoadProfile(p)}
                className="rounded-full border border-brand-300 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700 hover:bg-brand-100"
              >
                {p.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Mapping table */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Campo canónico
                </th>
                <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Columna Excel
                </th>
                <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Confianza
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {ALL_CANONICAL_KEYS.map((canonicalKey) => {
                const isIdentity = IDENTITY_CANONICAL_KEYS.includes(canonicalKey);
                const confidence = confidenceMap[canonicalKey];
                const selected = mapping[canonicalKey] ?? "";

                return (
                  <tr key={canonicalKey} className="hover:bg-gray-50/60">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-1.5">
                        {isIdentity && (
                          <span className="font-semibold text-brand-600">*</span>
                        )}
                        <span className="font-medium text-gray-800">
                          {CANONICAL_FIELD_LABELS[canonicalKey]}
                        </span>
                      </div>
                      <span className="font-mono text-xs text-gray-400">
                        {canonicalKey}
                      </span>
                    </td>

                    <td className="px-5 py-3">
                      <select
                        value={selected}
                        onChange={(e) =>
                          handleColumnChange(canonicalKey, e.target.value)
                        }
                        className="w-full rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                      >
                        <option value="">— sin mapear —</option>
                        {excelColumns.map((col) => (
                          <option key={col} value={col}>
                            {col}
                          </option>
                        ))}
                      </select>
                    </td>

                    <td className="px-5 py-3">
                      {confidence != null && selected ? (
                        <ConfidenceBadge value={confidence} />
                      ) : selected ? (
                        <span className="text-xs text-gray-400">manual</span>
                      ) : (
                        <span className="text-xs text-gray-300">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Save profile */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <h3 className="mb-3 text-sm font-semibold text-gray-700">
          Guardar como plantilla reutilizable
        </h3>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Nombre del perfil (ej: Cliente Acme)"
            value={saveName}
            onChange={(e) => {
              setSaveName(e.target.value);
              setSaveStatus(null);
            }}
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          <button
            onClick={handleSaveProfile}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:border-gray-400"
          >
            Guardar
          </button>
        </div>
        {saveStatus && (
          <p className="mt-2 text-xs text-gray-500">{saveStatus}</p>
        )}
      </div>

      {/* Validation error */}
      {validationError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-5 py-3 text-sm text-red-800">
          ⚠ {validationError}
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          onClick={onBack}
          className="rounded-lg border border-gray-300 px-5 py-2.5 text-sm font-medium text-gray-700 hover:border-gray-400"
        >
          ← Volver a configuración
        </button>
        <button
          onClick={handleConfirm}
          className="rounded-lg bg-brand-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          Confirmar mapeo →
        </button>
      </div>
    </div>
  );
}
