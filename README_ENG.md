# Automatic Supplier Data Enrichment

Desktop and CLI tool that extracts data from **invoices, RUT documents, and PDF invoices**, cross-checks it against a supplier master Excel file, and automatically updates missing or outdated fields.

Designed for accounting, finance, and administrative teams that need to enrich supplier information from PDF documents, with support for arbitrary Excel structures through a visual column-mapping system.

---

## Features

- **Intelligent extraction** of NIT, company name, address, phone number, email, city, and more from PDFs using regex, OCR, and optional GPT.
- **Dual matching strategy**: exact NIT matching and supplier-name fuzzy matching using `rapidfuzz`.
- **3 processing modes**: `fast` for regex only, `balanced` for regex + OCR, and `deep` for regex + OCR + GPT across all documents.
- **GPT as fallback**: triggered only when regex and OCR fail to extract sufficient data, with a configurable usage limit.
- **Smart SHA-256 hash-based cache**: unchanged PDFs are not reprocessed.
- Configurable **parallel processing**.
- **Tauri + React desktop application** with:
  - Visual column mapping: select which Excel column corresponds to each canonical field.
  - Automatic column detection with similarity-based suggestions.
  - Real-time document-by-document progress tracking.
  - Exportable logs.
  - UI adapted to Windows Fluent Design and Ubuntu/Linux GNOME/Adwaita.
- **CLI mode** for integration into scripts and data pipelines.
- Reusable YAML/JSON **mapping profiles** by client, company, or Excel structure.

---

## Architecture

```text
┌─────────────────────────────────────────────────────┐
│                 Desktop App (Tauri)                 │
│                                                     │
│  React + TypeScript + CSS Variables (Windows/Linux) │
│          ↕ invoke / events (IPC)                    │
│              Rust (src-tauri/)                      │
│   spawn_blocking → Python subprocess → JSON events  │
└──────────────────────┬──────────────────────────────┘
                       │ stdout JSON / stderr logs
┌──────────────────────▼──────────────────────────────┐
│                Python Backend (src/)                │
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

**Main workflow:**

1. The user configures the input paths: Excel file, PDF folder, output folder, and column mapping in the desktop app.
2. The app starts the Python process and passes a temporary `config.json`.
3. Python processes each PDF, extracts fields, and emits JSON events through `stdout`.
4. Rust reads the events in real time and forwards them to the frontend as Tauri events.
5. The UI displays progress, results, and logs. Once completed, it generates the updated Excel file.

---

## Prerequisites

### Python Backend

| Dependency | Minimum Version | Purpose |
|-----------|-----------------|---------|
| Python | 3.10+ | Runtime interpreter |
| pandas | 2.0+ | DataFrame handling |
| openpyxl | 3.1+ | Excel read/write operations |
| pymupdf | 1.23+ | PDF text extraction |
| rapidfuzz | 3.0+ | Supplier-name fuzzy matching |
| pytesseract | 0.3+ | OCR for balanced/deep modes |
| openai | 1.0+ | Optional GPT client |
| pyyaml | 6.0+ | Mapping profiles |
| python-dotenv | 1.0+ | Environment variables |

### Optional Tesseract OCR

- **Ubuntu/Debian**:

```bash
sudo apt install tesseract-ocr tesseract-ocr-spa
```

- **Windows**: install it from UB Mannheim and add it to the system PATH.

### Tauri Desktop App

| Tool | Version | Notes |
|------|---------|-------|
| Node.js | 18+ | JavaScript runtime |
| npm | 9+ | Package manager |
| Rust | stable | `rustup install stable` |
| Tauri CLI | 2.x | Included in devDependencies |
| WebView2 | — | Windows only, preinstalled on Windows 10/11 |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/HenryCamilo/pipeline-enriquecimiento-clientes-o-proveedores.git
cd pipeline-enriquecimiento-clientes-o-proveedores
```

### 2. Configure the Python backend

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows PowerShell

# Install dependencies
pip install pandas openpyxl pymupdf rapidfuzz pytesseract openai pyyaml python-dotenv

# Configure environment variables only if GPT is used
cp .env.example .env
# Edit .env with your OpenAI or Azure OpenAI API key
```

### 3. Prepare the data

Place your files in the corresponding folders.

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

> Real documents, Excel files, PDFs, and sensitive data must not be committed to the repository.

### 4. Install the desktop app

```bash
cd desktop-app
npm install
```

---

## Execution

### Option A — Recommended Desktop App

```bash
cd desktop-app

# Development mode with hot reload
npm run tauri dev

# Production build
npm run tauri build
```

The installer is generated at:

```text
desktop-app/src-tauri/target/release/bundle/
```

To force a specific theme during development:

```bash
VITE_FORCE_PLATFORM=windows npm run tauri dev
VITE_FORCE_PLATFORM=ubuntu  npm run tauri dev
```

### App Workflow

| Step | Action |
|------|--------|
| **1. Configuration** | Select the supplier Excel file, the PDF folder, and the output folder. Configure the processing mode and the Python executable path from your virtual environment. |
| **2. Columns** | The app detects the Excel columns and automatically suggests the mapping. Adjust it if necessary and save it as a reusable template. |
| **3. Processing** | Monitor real-time progress document by document. |
| **4. Results** | Review the statistical summary, the per-document results table, and export the logs. |

> **Python path in WSL**: If the backend runs in WSL, use `wsl -e python3` or the absolute path to the executable inside the Linux subsystem, for example `/home/user/project/venv/bin/python`.

---

### Option B — CLI Without Graphical Interface

```bash
# Activate virtual environment
source venv/bin/activate

# Full pipeline
python -m src.main \
  --excel   data/raw/excel/proveedores.xlsx \
  --docs    data/raw/facturas/ \
  --out     data/output/proveedores_actualizado.xlsx \
  --mode    balanced \
  --workers 4

# Detect columns from an Excel file
python -m src.schema.column_detector \
  --excel data/raw/excel/proveedores.xlsx \
  --sheet 0 \
  --header-row 0
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--excel` | — | Path to the supplier Excel file |
| `--docs` | — | Folder containing PDF documents |
| `--out` | — | Path for the output Excel file |
| `--mode` | `balanced` | Processing mode: `fast`, `balanced`, or `deep` |
| `--workers` | `4` | Number of parallel processes |
| `--no-cache` | false | Disable cache |
| `--no-gpt` | false | Disable GPT even if configured |
| `--max-gpt-ratio` | `0.3` | Maximum fraction of documents allowed to use GPT |
| `--sheet` | `0` | Excel sheet name or index |
| `--header-row` | `0` | Header row index, where 0 means the first row |
| `--export-mode` | `original` | `original` preserves the source columns, while `canonical` exports the standard schema |
| `--json-logs` | false | Emit JSON events through stdout for Tauri mode |

---

## Column Mapping

The pipeline uses a **canonical schema** with 12 fields that work independently of how columns are named in each Excel file.

| Canonical Field | Description | Identity Field |
|----------------|-------------|----------------|
| `supplier_name` | Supplier or legal company name | ✓ |
| `tax_id` | NIT / Identification document | ✓ |
| `address` | Address | |
| `phone` | Phone number | |
| `email` | Email address | |
| `city` | City | |
| `city_code` | City/municipality code | |
| `person_type` | Natural/legal person type | |
| `retention_type` | Withholding type | |
| `contribution_type` | Contribution type | |
| `state_enterprise_type` | State-owned enterprise type | |
| `electronic_biller` | Electronic biller yes/no | |

> At least one of the **identity fields**, `supplier_name` or `tax_id`, must be mapped so the pipeline can perform matching.

Mapping profiles are stored in:

```text
config/mappings/
```

Example generic profile:

```text
config/mappings/default_supplier_mapping.yaml
```

---

## Processing Modes

| Mode | Extraction Strategy | Speed | API Cost |
|------|---------------------|-------|----------|
| `fast` | Regex only | ★★★★★ | $0 |
| `balanced` | Regex + OCR | ★★★☆☆ | $0 |
| `deep` | Regex + OCR + GPT always | ★★☆☆☆ | High |

In `balanced` mode, GPT is triggered **only** when regex and OCR do not extract enough data, while respecting the `--max-gpt-ratio` limit.

---

## Project Structure

```text
project_act_proveedores/
│
├── src/                            # Python backend
│   ├── main.py                     # CLI entry point + Tauri mode
│   ├── agents/
│   │   ├── gpt_client.py           # OpenAI / Azure OpenAI client
│   │   └── mini_agent.py           # Pipeline orchestrator
│   ├── cache/
│   │   └── cache_manager.py        # SHA-256 file-based cache
│   ├── config/
│   │   ├── settings.py             # Global configuration
│   │   └── excel_schema.py         # Re-exports canonical_schema
│   ├── enrichment/
│   │   ├── dataframe_normalizer.py # Data normalization
│   │   ├── excel_updater.py        # Writes results to Excel
│   │   └── field_validators.py     # Extracted-field validation
│   ├── extraction/
│   │   ├── pdf_reader.py           # PyMuPDF text extraction
│   │   ├── ocr_reader.py           # OCR with Tesseract
│   │   ├── page_scorer.py          # Most-informative-page selection
│   │   └── text_cleaner.py         # Raw text cleanup
│   ├── matching/
│   │   └── proveedor_matcher.py    # Exact NIT matching + fuzzy name matching
│   ├── parsing/
│   │   ├── factura_parser.py       # Regex parser for invoices
│   │   └── rut_parser.py           # Regex parser for RUT documents
│   └── schema/
│       ├── canonical_schema.py     # Definition of the 12 canonical fields
│       ├── column_detector.py      # Automatic column detection
│       ├── column_mapper.py        # Excel ↔ canonical translation
│       ├── mapping_profile.py      # Mapping profile load/save logic
│       └── schema_aliases.yaml     # Field aliases in ES/EN
│
├── desktop-app/                    # Tauri desktop app
│   ├── src/                        # React + TypeScript frontend
│   │   ├── App.tsx                 # Root component
│   │   ├── components/             # UI panels
│   │   │   ├── ColumnMappingStep.tsx
│   │   │   ├── ConfigurationPanel.tsx
│   │   │   ├── FileSelectionPanel.tsx
│   │   │   ├── LogsPanel.tsx
│   │   │   ├── ProgressPanel.tsx
│   │   │   ├── ResultsTable.tsx
│   │   │   ├── SummaryCard.tsx
│   │   │   └── base/               # Reusable components
│   │   ├── layouts/                # WindowsLayout / UbuntuLayout
│   │   ├── platform/               # OS detection and context
│   │   ├── services/               # Tauri command invocation
│   │   ├── themes/                 # Platform-specific CSS variables
│   │   └── types/                  # Global TypeScript types
│   └── src-tauri/                  # Tauri Rust backend
│       ├── src/lib.rs              # IPC commands
│       ├── Cargo.toml              # Rust dependencies
│       ├── tauri.conf.json         # Window configuration
│       └── capabilities/           # Permissions and capabilities
│
├── config/
│   └── mappings/
│       └── default_supplier_mapping.yaml
│
├── data/
│   └── raw/
│       ├── excel/                  # Local Excel files, not committed to the repository
│       └── facturas/               # Local PDFs, not committed to the repository
│
├── .env.example                    # Environment variable template
├── .gitignore
└── README.md
```

---

## Environment Variables

Copy `.env.example` as `.env` in the project root:

```bash
cp .env.example .env
```

The Python backend automatically loads this file at startup. These variables are **optional** unless GPT mode is used.

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Only with OpenAI GPT | OpenAI API key |
| `AZURE_OPENAI_API_KEY` | Only with Azure GPT | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Only with Azure GPT | Azure endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | Only with Azure GPT | Deployment name |
| `AZURE_OPENAI_API_VERSION` | Only with Azure GPT | API version |
| `TESSERACT_CMD` | Optional | Path to Tesseract if it is not available in PATH |

---

## Troubleshooting

**`Unable to execute Python`**  
Verify that the Python executable path configured in the app matches the executable from your virtual environment. In WSL, use `wsl -e python3` or an absolute path.

**`Columns could not be detected`**  
The Excel header may be located in a row other than the first one. Adjust the "Header row" value in the app’s advanced configuration.

**PDFs returning `no_data`**  
The PDF is likely scanned and has no embedded text layer. Use `balanced` or `deep` mode to enable OCR.

**GPT does not respond / authentication error**  
Verify that `.env` contains a valid API key and that the selected model is available in your region or subscription.

**App without decorations / native title bar**  
The app uses a custom title bar with `decorations: false`. In i3, Sway, or other minimal window managers, it may look different from the GNOME design. You can set `decorations: true` in `desktop-app/src-tauri/tauri.conf.json` to use the native title bar.

---

## Author

**Henry Valencia**  
Biomedical Engineer | Python Automation | AI-assisted Document Processing

**Farid Prado**  
Nickname: faridSprado  
Multimedia Engineer  
LinkedIn: https://www.linkedin.com/in/faridprado/
