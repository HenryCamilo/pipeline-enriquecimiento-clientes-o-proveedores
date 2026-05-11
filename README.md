# Actualización Automática de Proveedores

Herramienta de escritorio y CLI que extrae datos de **facturas, RUTs e invoices en PDF**, los cruza contra un Excel maestro de proveedores y actualiza automáticamente los campos faltantes o desactualizados.

Diseñada para equipos contables, financieros y administrativos que necesitan enriquecer información de proveedores a partir de documentos PDF, con soporte para estructuras de Excel arbitrarias mediante un sistema de mapeo visual de columnas.

---

## Características

- **Extracción inteligente** de NIT, nombre, dirección, teléfono, correo, ciudad y más desde PDFs mediante regex, OCR y GPT opcional.
- **Matching dual**: por NIT exacto y por nombre con fuzzy matching usando `rapidfuzz`.
- **3 modos de procesamiento**: `fast` solo regex, `balanced` regex + OCR, `deep` regex + OCR + GPT para todos los documentos.
- **GPT como fallback**: se activa únicamente cuando regex y OCR no encuentran datos suficientes, con límite configurable de uso.
- **Caché inteligente** por hash SHA-256: los PDFs que no cambian no se reprocesan.
- **Procesamiento paralelo** configurable.
- **App de escritorio** Tauri + React con:
  - Mapeo visual de columnas: selecciona qué columna del Excel corresponde a cada campo canónico.
  - Detección automática de columnas con sugerencias por similitud.
  - Progreso en tiempo real documento por documento.
  - Logs exportables.
  - UI adaptada a Windows Fluent Design y Ubuntu/Linux GNOME/Adwaita.
- **Modo CLI** para integración en scripts y pipelines.
- **Perfiles de mapeo** reutilizables YAML/JSON por cliente, empresa o estructura de Excel.

---

## Arquitectura

```text
┌─────────────────────────────────────────────────────┐
│              App de Escritorio (Tauri)              │
│                                                     │
│  React + TypeScript + CSS Variables (Windows/Linux) │
│          ↕ invoke / events (IPC)                    │
│              Rust (src-tauri/)                      │
│   spawn_blocking → Python subprocess → JSON events  │
└──────────────────────┬──────────────────────────────┘
                       │ stdout JSON / stderr logs
┌──────────────────────▼──────────────────────────────┐
│              Backend Python (src/)                  │
│                                                     │
│  main.py ──► mini_agent.py ──► ProcessPoolExecutor  │
│                │                                    │
│         ┌──────┴──────┐                             │
│         ▼             ▼                             │
│   pdf_reader      ocr_reader                        │
│   factura_parser  rut_parser  gpt_client            │
│         │                                           │
│   proveedor_matcher ──► excel_updater               │
│         │                                           │
│   column_mapper (canonical ↔ Excel columns)         │
└─────────────────────────────────────────────────────┘
```

**Flujo principal:**

1. El usuario configura rutas: Excel, carpeta de PDFs, carpeta de salida y mapeo de columnas en la app.
2. La app lanza el proceso Python pasando un `config.json` temporal.
3. Python procesa cada PDF, extrae campos y emite eventos JSON por `stdout`.
4. Rust lee los eventos en tiempo real y los reenvía al frontend como eventos Tauri.
5. La UI muestra progreso, resultados y logs. Al finalizar, genera el Excel actualizado.

---

## Requisitos previos

### Python backend

| Dependencia | Versión mínima | Uso |
|-------------|---------------|-----|
| Python | 3.10+ | Intérprete |
| pandas | 2.0+ | Manejo de DataFrames |
| openpyxl | 3.1+ | Lectura/escritura Excel |
| pymupdf | 1.23+ | Extracción de texto en PDFs |
| rapidfuzz | 3.0+ | Fuzzy matching de nombres |
| pytesseract | 0.3+ | OCR, modo balanced/deep |
| openai | 1.0+ | Cliente GPT opcional |
| pyyaml | 6.0+ | Perfiles de mapeo |
| python-dotenv | 1.0+ | Variables de entorno |

### Tesseract OCR opcional

- **Ubuntu/Debian**:

```bash
sudo apt install tesseract-ocr tesseract-ocr-spa
```

- **Windows**: instalar desde UB Mannheim y agregar al PATH.

### App de escritorio Tauri

| Herramienta | Versión | Notas |
|-------------|---------|-------|
| Node.js | 18+ | Runtime JS |
| npm | 9+ | Gestor de paquetes |
| Rust | stable | `rustup install stable` |
| Tauri CLI | 2.x | Incluido en devDependencies |
| WebView2 | — | Solo Windows, preinstalado en Windows 10/11 |

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/HenryCamilo/pipeline-enriquecimiento-proveedores.git
cd pipeline-enriquecimiento-proveedores
```

### 2. Configurar el backend Python

```bash
# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows PowerShell

# Instalar dependencias
pip install pandas openpyxl pymupdf rapidfuzz pytesseract openai pyyaml python-dotenv

# Configurar variables de entorno solo si usas GPT
cp .env.example .env
# Edita .env con tu clave de OpenAI o Azure OpenAI
```

### 3. Preparar los datos

Coloca tus archivos en las carpetas correspondientes.

```text
data/
└── raw/
    ├── excel/
    │   └── proveedores.xlsx
    └── facturas/
        ├── factura_001.pdf
        ├── RUT empresa.pdf
        └── INVOICE xxx.pdf
```

> Los documentos reales, Excels, PDFs y datos sensibles no deben subirse al repositorio.

### 4. Instalar la app de escritorio

```bash
cd desktop-app
npm install
```

---

## Ejecución

### Opción A — App de escritorio recomendada

```bash
cd desktop-app

# Modo desarrollo con hot-reload
npm run tauri dev

# Build de producción
npm run tauri build
```

El instalador se genera en:

```text
desktop-app/src-tauri/target/release/bundle/
```

Para forzar un tema específico durante el desarrollo:

```bash
VITE_FORCE_PLATFORM=windows npm run tauri dev
VITE_FORCE_PLATFORM=ubuntu  npm run tauri dev
```

### Flujo en la app

| Paso | Acción |
|------|--------|
| **1. Configuración** | Selecciona el Excel de proveedores, la carpeta de PDFs y la carpeta de salida. Configura el modo de procesamiento y la ruta al ejecutable Python de tu entorno virtual. |
| **2. Columnas** | La app detecta las columnas del Excel y sugiere el mapeo automáticamente. Corrígelo si es necesario y guárdalo como plantilla para reutilizarlo. |
| **3. Procesando** | Sigue el progreso en tiempo real, documento por documento. |
| **4. Resultados** | Revisa el resumen estadístico, la tabla por documento y exporta los logs. |

> **Ruta Python en WSL**: Si el backend corre en WSL, usa `wsl -e python3` o la ruta absoluta al ejecutable dentro del subsistema Linux, por ejemplo `/home/usuario/proyecto/venv/bin/python`.

---

### Opción B — CLI sin interfaz gráfica

```bash
# Activar entorno virtual
source venv/bin/activate

# Pipeline completo
python -m src.main \
  --excel   data/raw/excel/proveedores.xlsx \
  --docs    data/raw/facturas/ \
  --out     data/output/proveedores_actualizado.xlsx \
  --mode    balanced \
  --workers 4

# Detectar columnas de un Excel
python -m src.schema.column_detector \
  --excel data/raw/excel/proveedores.xlsx \
  --sheet 0 \
  --header-row 0
```

### Opciones CLI

| Flag | Default | Descripción |
|------|---------|-------------|
| `--excel` | — | Ruta al Excel de proveedores |
| `--docs` | — | Carpeta con PDFs |
| `--out` | — | Ruta del Excel de salida |
| `--mode` | `balanced` | `fast`, `balanced` o `deep` |
| `--workers` | `4` | Procesos paralelos |
| `--no-cache` | false | Deshabilitar caché |
| `--no-gpt` | false | Deshabilitar GPT aunque esté configurado |
| `--max-gpt-ratio` | `0.3` | Fracción máxima de documentos que pueden usar GPT |
| `--sheet` | `0` | Hoja del Excel, nombre o índice |
| `--header-row` | `0` | Fila del encabezado, 0 = primera |
| `--export-mode` | `original` | `original` preserva columnas o `canonical` exporta esquema estándar |
| `--json-logs` | false | Emitir eventos JSON por stdout, modo Tauri |

---

## Mapeo de columnas

El pipeline trabaja con un **esquema canónico** de 12 campos que funcionan independientemente de cómo se llamen las columnas en cada Excel.

| Campo canónico | Descripción | Campo de identidad |
|---------------|-------------|-------------------|
| `supplier_name` | Nombre o razón social | ✓ |
| `tax_id` | NIT / Documento de identificación | ✓ |
| `address` | Dirección | |
| `phone` | Teléfono | |
| `email` | Correo electrónico | |
| `city` | Ciudad | |
| `city_code` | Código de ciudad/municipio | |
| `person_type` | Tipo de persona natural/jurídica | |
| `retention_type` | Tipo de retención | |
| `contribution_type` | Tipo de contribución | |
| `state_enterprise_type` | Tipo de empresa estatal | |
| `electronic_biller` | Facturador electrónico sí/no | |

> Al menos uno de los **campos de identidad** `supplier_name` o `tax_id` debe estar mapeado para que el pipeline pueda hacer matching.

Los perfiles de mapeo se guardan en:

```text
config/mappings/
```

Ejemplo de perfil genérico:

```text
config/mappings/default_supplier_mapping.yaml
```

---

## Modos de procesamiento

| Modo | Extracción | Velocidad | Costo API |
|------|-----------|-----------|-----------|
| `fast` | Solo regex | ★★★★★ | $0 |
| `balanced` | Regex + OCR | ★★★☆☆ | $0 |
| `deep` | Regex + OCR + GPT siempre | ★★☆☆☆ | Alto |

En modo `balanced`, GPT se activa **solo** cuando regex y OCR no encuentran suficientes datos, respetando el límite `--max-gpt-ratio`.

---

## Estructura del proyecto

```text
project_act_proveedores/
│
├── src/                            # Backend Python
│   ├── main.py                     # Entry point CLI + modo Tauri
│   ├── agents/
│   │   ├── gpt_client.py           # Cliente OpenAI / Azure OpenAI
│   │   └── mini_agent.py           # Orquestador del pipeline
│   ├── cache/
│   │   └── cache_manager.py        # Caché SHA-256 por archivo
│   ├── config/
│   │   ├── settings.py             # Configuración global
│   │   └── excel_schema.py         # Reexporta canonical_schema
│   ├── enrichment/
│   │   ├── dataframe_normalizer.py # Normalización de datos
│   │   ├── excel_updater.py        # Escritura de resultados al Excel
│   │   └── field_validators.py     # Validación de campos extraídos
│   ├── extraction/
│   │   ├── pdf_reader.py           # Extracción de texto PyMuPDF
│   │   ├── ocr_reader.py           # OCR con Tesseract
│   │   ├── page_scorer.py          # Selección de la página más informativa
│   │   └── text_cleaner.py         # Limpieza de texto raw
│   ├── matching/
│   │   └── proveedor_matcher.py    # Matching NIT exacto + fuzzy nombre
│   ├── parsing/
│   │   ├── factura_parser.py       # Regex para facturas
│   │   └── rut_parser.py           # Regex para documentos RUT
│   └── schema/
│       ├── canonical_schema.py     # Definición de los 12 campos canónicos
│       ├── column_detector.py      # Detección automática de columnas
│       ├── column_mapper.py        # Traducción Excel ↔ canónico
│       ├── mapping_profile.py      # Carga/guarda perfiles de mapeo
│       └── schema_aliases.yaml     # Aliases por campo en ES/EN
│
├── desktop-app/                    # App de escritorio Tauri
│   ├── src/                        # Frontend React + TypeScript
│   │   ├── App.tsx                 # Componente raíz
│   │   ├── components/             # Paneles de la UI
│   │   │   ├── ColumnMappingStep.tsx
│   │   │   ├── ConfigurationPanel.tsx
│   │   │   ├── FileSelectionPanel.tsx
│   │   │   ├── LogsPanel.tsx
│   │   │   ├── ProgressPanel.tsx
│   │   │   ├── ResultsTable.tsx
│   │   │   ├── SummaryCard.tsx
│   │   │   └── base/               # Componentes reutilizables
│   │   ├── layouts/                # WindowsLayout / UbuntuLayout
│   │   ├── platform/               # Detección de SO y contexto
│   │   ├── services/               # Invocación de comandos Tauri
│   │   ├── themes/                 # CSS variables por plataforma
│   │   └── types/                  # Tipos TypeScript globales
│   └── src-tauri/                  # Backend Rust Tauri
│       ├── src/lib.rs              # Comandos IPC
│       ├── Cargo.toml              # Dependencias Rust
│       ├── tauri.conf.json         # Configuración de la ventana
│       └── capabilities/           # Permisos y capacidades Tauri
│
├── config/
│   └── mappings/
│       └── default_supplier_mapping.yaml
│
├── data/
│   └── raw/
│       ├── excel/                  # Archivos Excel locales, no se suben al repo
│       └── facturas/               # PDFs locales, no se suben al repo
│
├── .env.example                    # Plantilla de variables de entorno
├── .gitignore
└── README.md
```

---

## Variables de entorno

Copia `.env.example` como `.env` en la raíz del proyecto:

```bash
cp .env.example .env
```

El backend Python carga automáticamente este archivo al iniciar. Las variables son **opcionales** a menos que uses el modo GPT.

| Variable | Requerida | Descripción |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Solo con GPT OpenAI | Clave de API de OpenAI |
| `AZURE_OPENAI_API_KEY` | Solo con GPT Azure | Clave de Azure OpenAI |
| `AZURE_OPENAI_ENDPOINT` | Solo con GPT Azure | Endpoint de Azure |
| `AZURE_OPENAI_DEPLOYMENT` | Solo con GPT Azure | Nombre del deployment |
| `AZURE_OPENAI_API_VERSION` | Solo con GPT Azure | Versión de la API |
| `TESSERACT_CMD` | Opcional | Ruta a Tesseract si no está en PATH |

---

## Solución de problemas

**`No se pudo ejecutar Python`**  
Verifica que la ruta al ejecutable Python en la app coincida con la de tu entorno virtual. En WSL usa `wsl -e python3` o la ruta absoluta.

**`No se pudieron detectar las columnas`**  
El Excel puede tener el encabezado en una fila que no es la primera. Ajusta "Fila de encabezado" en la configuración avanzada de la app.

**PDFs con resultado `no_data`**  
El PDF está escaneado sin capa de texto. Usa el modo `balanced` o `deep` para activar OCR.

**GPT no responde / error de autenticación**  
Verifica que `.env` tenga la clave correcta y que el modelo esté disponible en tu región o suscripción.

**App sin decoraciones / titlebar nativo**  
La app usa una barra de título personalizada con `decorations: false`. En i3, Sway u otros window managers minimalistas puede verse diferente al diseño GNOME. Puedes cambiar `decorations: true` en `desktop-app/src-tauri/tauri.conf.json` para usar el titlebar nativo.

---

## Autor

**Henry Valencia**  
Biomedical Engineer | Python Automation | AI-assisted Document Processing

**Farid Prado**

Nick: faridSprado
Ingeniero Multimedia
https://www.linkedin.com/in/faridprado/ 
---
