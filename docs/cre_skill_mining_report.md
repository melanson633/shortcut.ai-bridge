# REPO EXPLORER → CLAUDE CODE SKILL MINER REPORT

## PASS 1: STRUCTURAL SURVEY (Broad Discovery)

### Repository Relevance Snapshot
This repository is **not CRE-native**; it is a local bridge server for data ingestion, file processing, OCR, and API integration testing. That said, it contains reusable patterns directly adaptable to CRE finance/accounting workflows (document intake, tabular extraction, validation pipelines, exports, and repeatable test harnesses).

### Structural Inventory

#### Root
- `server.py` — Flask orchestration layer with file-serving, ingestion, processing, export, and test endpoints; central workflow controller for all processors.
- `requirements.txt` — Python dependency manifest (Flask, pandas, pdfplumber, PyMuPDF, pytesseract, openpyxl, httpx, dotenv).
- `config.json` — Runtime configuration schema (host/port/CORS plus processor settings; some options documented but not enforced).
- `README.md` — Setup + endpoint catalog + processor behavior + integration usage patterns.
- `CLAUDE.md` — Agent-oriented operational playbook documenting architecture, patterns, known issues, and endpoint semantics.
- `start.ps1` — Windows launcher for local server startup.
- `test_pdf_processor.py` — Lightweight validation script for PDF extraction behavior and output inspection.

#### `processors/`
- `processors/pdf.py` — Local PDF text and table extraction into structured JSON (page-level + table-level metadata).
- `processors/mistral_ocr.py` — Unified OCR engine with Mistral API integration, retry/backoff, local fallback, PDF/image routing, and standardized document JSON mapping.
- `processors/image.py` — Local Tesseract-based OCR for image files with output metadata.
- `processors/excel.py` — Excel normalization to JSON/CSV across sheets using pandas.
- `processors/__init__.py` — Package marker.

#### `scripts/`
- `scripts/generate_sample_data.py` — Synthetic dataset generator (transactions, assumptions, employee metrics, time-series); seedable testing data creation.

#### `data/samples/`
- `sales_transactions.csv` — Transaction-style tabular dataset useful for aggregation/filter testing.
- `financial_assumptions.json` — Multi-scenario assumptions data (growth, COGS, tax, discount rates).
- `employee_metrics.json` — Personnel/departmental metrics sample payload.
- `time_series_data.csv` — Daily metric stream for trend/forecast style tests.

#### `docs/`
- `docs/integration_testing.md` — End-to-end endpoint test matrix/results (10 tests) with practical implications.
- `docs/shortcut_ocr_testing_workflow.md` — Structured OCR validation workflow, schema checks, test matrix, and fetch snippets.
- `docs/mistral/OCR_USAGE.md` — Operational instructions for Mistral OCR usage.
- `docs/shortcut_context.txt` — Context handoff text for Shortcut/agent collaboration.
- `docs/shortcut_api_docs/shortcut-platform-api.yaml` — OpenAPI spec for Shortcut platform API (jobs, polling, downloads, uploads).
- `docs/archive/mistral/MISTRAL_OCR_UPGRADE_PLAN.md` — Archived migration/upgrade planning notes for OCR implementation.

#### `api/`
- `api/__init__.py` — Placeholder package for future endpoint modularization.

#### `inbox/`
- `inbox/live/.gitkeep` — Live document drop-zone placeholder.
- `inbox/ocr_tests/.gitkeep` — OCR testing drop-zone placeholder.

### Pass-1 Requirement Checklist
1. **Languages/frameworks/libs**: Python + Flask + pandas + OCR/PDF stack + httpx.
2. **Data models/schemas/config/sample data**: `config.json`, standardized document JSON output schema in OCR mapping, sample CSV/JSON datasets.
3. **Templates/prompts/instructions**: `README.md`, `CLAUDE.md`, `docs/*workflow*.md`, OpenAPI YAML.
4. **Automation/parsers/ETL**: file processors, data generation script, `/api/analyze` pipeline.
5. **Financial logic/formulas**: scenario assumptions + aggregation/group-by math in analytics endpoints.
6. **API/webhook/connectors**: Shortcut API spec + Mistral OCR HTTP integration.
7. **PDF/doc/OCR/text extraction**: `processors/pdf.py`, `processors/mistral_ocr.py`, `processors/image.py`.
8. **Reusable utilities**: boolean parsing, path validation, markdown-to-text normalization, retry/backoff, MIME/base64 helpers.

---

## PASS 2: PATTERN ANALYSIS (Targeted Evaluation)

### Scoring rubric used
- **CRE applicability**: direct fit to listed finance/accounting workflows.
- **Modularity potential**: extraction feasibility into a standalone Skill.
- **Dependency load**: external services/libraries and coupling to server context.

### Component 1 — `processors/mistral_ocr.py`
- **What it does:** Multi-mode OCR for PDFs/images (force AI/force local/auto), Mistral API call with retry/backoff, payload assembly, schema-normalized output, and local fallback.
- **CRE applicability:** High for construction draws, lender packages, invoices, lease docs, CAM backup extraction.
- **Modularity potential:** **HIGH**.
- **Dependencies:** `httpx`, optional `pdfplumber`, optional `pytesseract/Pillow`, `MISTRAL_API_KEY`.
- **Embedded domain knowledge worth preserving:** Robust OCR decisioning (`_should_use_mistral_for_pdf`), schema-normalized output contract, table/image/link extraction map.

### Component 2 — `server.py` `/api/process`
- **What it does:** Unified document processing endpoint with mode controls, input sanitization, extension-based router, and consistent JSON responses.
- **CRE applicability:** High for “drop document → process → retrieve structured output” accounting ops.
- **Modularity potential:** **HIGH**.
- **Dependencies:** Processor modules + environment config.
- **Embedded value:** Path traversal guard + OCR mode parameters + deterministic output path conventions.

### Component 3 — `processors/excel.py`
- **What it does:** Converts workbooks into JSON/CSV with sheet-level metadata and record serialization.
- **CRE applicability:** High for rent rolls, budget workbooks, covenant trackers, AP/AR exports.
- **Modularity potential:** **HIGH**.
- **Dependencies:** `pandas`, `openpyxl`.
- **Embedded value:** Multi-sheet normalization pattern and null-cleaning strategy.

### Component 4 — `server.py` `/api/analyze`
- **What it does:** Receives tabular JSON and performs pandas aggregations (`sum`, `mean`, `count`, group-by region/product).
- **CRE applicability:** Medium-High as a base pattern for NOI, variance, and portfolio rollups.
- **Modularity potential:** **MEDIUM**.
- **Dependencies:** pandas and endpoint wrapper.
- **Embedded value:** Request-driven aggregation dispatch pattern and fast return schema.

### Component 5 — `processors/pdf.py`
- **What it does:** Local PDF extraction for text + tables with page/table metadata and JSON output.
- **CRE applicability:** Medium-High for backup-mode processing where API OCR unavailable.
- **Modularity potential:** **HIGH**.
- **Dependencies:** `pdfplumber`.
- **Embedded value:** Lightweight offline extraction flow and table header/rows pattern.

### Component 6 — `docs/shortcut_ocr_testing_workflow.md`
- **What it does:** Defines rigorous OCR validation phases, schema assertions, test matrix, and error tests.
- **CRE applicability:** High for controllership-quality validation and repeatable QA on document extraction.
- **Modularity potential:** **HIGH**.
- **Dependencies:** Endpoint availability and test files.
- **Embedded value:** Validation checklist that can become acceptance criteria in Skills.

### Component 7 — `server.py` `/api/export`
- **What it does:** Saves posted JSON/CSV payloads with timestamped filenames in exports directory.
- **CRE applicability:** High for report snapshots, lender package archives, period-close evidence files.
- **Modularity potential:** **HIGH**.
- **Dependencies:** pandas only for CSV path.
- **Embedded value:** Timestamped export naming convention and dual-format sink.

### Component 8 — `scripts/generate_sample_data.py`
- **What it does:** Creates synthetic transactional, scenario, HR, and time-series datasets.
- **CRE applicability:** Medium (non-CRE semantics, but useful for sandboxing finance workflows).
- **Modularity potential:** **HIGH**.
- **Dependencies:** standard library only.
- **Embedded value:** Reproducible mock-data generation pattern for demos/UAT.

### Component 9 — `data/samples/financial_assumptions.json`
- **What it does:** Structured scenario assumptions (base/upside/downside), key rates, baseline metrics.
- **CRE applicability:** Medium-High as template for budget/reforecast assumption packs.
- **Modularity potential:** **HIGH**.
- **Dependencies:** none.
- **Embedded value:** Scenario schema readily convertible to property-level underwriting assumptions.

### Component 10 — `docs/shortcut_api_docs/shortcut-platform-api.yaml`
- **What it does:** OpenAPI contract for submitting jobs, polling, upload/download flows.
- **CRE applicability:** Medium for orchestration skills (automating model/report generation jobs).
- **Modularity potential:** **MEDIUM** (requires platform token/availability).
- **Dependencies:** external Shortcut API.
- **Embedded value:** End-to-end async job pattern documentation.

### Component 11 — `server.py` `/api/upload-base64`
- **What it does:** Accepts base64 payload and writes binary to inbox; browser-safe upload workaround.
- **CRE applicability:** Medium-High for automating uploads of statements/invoices when multipart is constrained.
- **Modularity potential:** **HIGH**.
- **Dependencies:** none beyond Flask/std lib.
- **Embedded value:** Reliable upload pattern with predictable JSON response.

### Component 12 — `docs/integration_testing.md`
- **What it does:** Demonstrates tested throughput, timeout behavior, and endpoint-level reliability evidence.
- **CRE applicability:** Medium as operational confidence framework before productionizing finance automations.
- **Modularity potential:** **MEDIUM**.
- **Dependencies:** local environment and endpoint availability.
- **Embedded value:** performance/robustness baselines and practical limits.

---

## PASS 3: SKILL SYNTHESIS (Ranked Recommendations)

### 1. CRE Draw Package OCR + Structured Extraction
**Value Proposition:** Construction draw reviews are document-heavy and time-sensitive. This Skill would standardize intake of PDF/image draw packages and output machine-readable JSON for downstream lender reporting and AP workflows. It reduces manual data transcription and improves consistency across properties.

**Source Components:**
- `processors/mistral_ocr.py`: OCR orchestration, schema output, retry/backoff, auto/force mode controls.
- `server.py` (`/api/process`): Routing, validation, and invocation surface.
- `docs/shortcut_ocr_testing_workflow.md`: Validation checklist and QA workflow.
- `docs/mistral/OCR_USAGE.md`: Operator setup and usage parameters.

**Replication Targets:**
- **Copy:** OCR mode selection, SDJ-like response schema, API retry strategy, page/table/image mapping.
- **Modify:** Rename schema fields for CRE draw concepts (pay app number, lien waivers, retainage lines).
- **Build new:** Post-processing rules to detect line items like contractor, amount requested, prior draws, and percent complete.

**Modularity Assessment:** Self-contained because ingestion, processing, and output schema are already encapsulated; only API key and dependency setup are external. **Overall modularity: HIGH.**

**Proposed SKILL.md Structure:**
```yaml
name: cre-draw-package-ocr
description: Extract structured data from construction draw PDFs/images for lender reporting and AP validation.
```
- Trigger conditions and supported document types
- Stepwise OCR execution (auto vs force modes)
- CRE-specific field mapping instructions
- Validation checklist (schema + content confidence)
- Output templates for downstream reporting

**Confidence Level:** HIGH

---

### 2. JV Investor Reporting Export Packager
**Value Proposition:** Investor reporting needs repeatable, timestamped outputs in multiple formats. This Skill would turn analysis payloads into audit-friendly JSON/CSV exports with consistent naming and retrieval conventions. It accelerates monthly/quarterly distribution cycles and reduces versioning confusion.

**Source Components:**
- `server.py` (`/api/export`): Timestamped JSON/CSV writer pattern.
- `server.py` (`/api/status`): File discovery/status metadata pattern.
- `README.md`: Usage and endpoint examples.
- `docs/integration_testing.md`: Proven behavior under integration tests.

**Replication Targets:**
- **Copy:** Export payload contract, timestamp naming, dual JSON/CSV output behavior.
- **Modify:** Add JV-centric naming (property, partner, period, version tags).
- **Build new:** Optional manifest file summarizing exported artifacts per reporting cycle.

**Modularity Assessment:** Endpoint behavior is isolated and minimally coupled; can be packaged as a pure “receive-and-persist” utility. **Overall modularity: HIGH.**

**Proposed SKILL.md Structure:**
```yaml
name: cre-investor-export-packager
description: Save investor reporting outputs as timestamped JSON/CSV artifacts with predictable naming.
```
- Expected input schema and naming conventions
- Export generation and storage rules
- File manifest + integrity checks
- Retrieval/verification steps
- Error handling and fallback formatting

**Confidence Level:** HIGH

---

### 3. Rent Roll / Budget Workbook Normalizer
**Value Proposition:** CRE accounting teams frequently ingest inconsistent Excel files from site teams, PMs, and JV partners. This Skill would normalize multi-sheet workbooks into structured JSON/CSV, preserving sheet metadata for audit and transformation. It speeds budget/reforecast consolidation and reduces cleanup labor.

**Source Components:**
- `processors/excel.py`: Multi-sheet extraction and serialization logic.
- `server.py` (`/api/process`): Extension routing and output handling.
- `config.json`: Processor defaults and sheet behavior hints.

**Replication Targets:**
- **Copy:** Workbook parsing, null handling, sheet metadata structure.
- **Modify:** Add CRE canonical column mapping (unit, tenant, lease start/end, base rent, CAM).
- **Build new:** Validation rules for required columns and data types per workbook class.

**Modularity Assessment:** Core conversion logic is already standalone; domain adaptation is mostly rule-layer additions. **Overall modularity: HIGH.**

**Proposed SKILL.md Structure:**
```yaml
name: cre-workbook-normalizer
description: Normalize rent roll and budget Excel workbooks into structured JSON/CSV for downstream finance workflows.
```
- File acceptance and sheet discovery process
- Column harmonization map for CRE schemas
- Data quality checks (missing fields, type coercion)
- Export outputs and naming conventions
- Manual review checklist for exceptions

**Confidence Level:** HIGH

---

### 4. Property Portfolio Variance Analyzer (API-Driven)
**Value Proposition:** Monthly close and reforecast workflows require rapid variance summaries across properties and categories. This Skill would operationalize request-driven aggregations and grouped summaries from posted datasets. It improves repeatability for NOI variance packs and management dashboards.

**Source Components:**
- `server.py` (`/api/analyze`): Aggregation dispatcher and grouped metrics logic.
- `data/samples/sales_transactions.csv`: Prototype transaction schema for testing.
- `scripts/generate_sample_data.py`: Mock dataset generation for acceptance tests.

**Replication Targets:**
- **Copy:** Input contract + aggregation selector pattern (`sum`, `mean`, `count`, grouped outputs).
- **Modify:** Replace region/product with property/account/period dimensions.
- **Build new:** Budget-vs-actual and prior-period variance metrics with threshold flags.

**Modularity Assessment:** Moderate coupling to Flask endpoint wrapper; core pandas transformation is extractable but needs a CRE-specific metric library layer. **Overall modularity: MEDIUM.**

**Proposed SKILL.md Structure:**
```yaml
name: cre-variance-analyzer
description: Compute portfolio-level and property-level finance variances from tabular payloads using configurable aggregations.
```
- Accepted dataset schema and required fields
- Aggregation and grouping instruction patterns
- Variance formula templates and alert thresholds
- Output interpretation for accountants/asset managers
- Validation steps against source workbooks

**Confidence Level:** MEDIUM

---

### 5. OCR QA Gate for Accounting Documents
**Value Proposition:** Teams adopting OCR in finance workflows need trust before automation can replace manual review. This Skill would enforce a rigorous quality gate on extracted outputs using schema and metadata checks plus targeted error tests. It reduces downstream reconciliation errors and builds operational confidence.

**Source Components:**
- `docs/shortcut_ocr_testing_workflow.md`: Full phased validation workflow and test matrix.
- `docs/integration_testing.md`: Reliability baseline and endpoint behavior evidence.
- `test_pdf_processor.py`: Quick local sanity check pattern.
- `processors/mistral_ocr.py`: Concrete output schema details to validate.

**Replication Targets:**
- **Copy:** Top-level/page-level assertions, test matrix structure, error-case checks.
- **Modify:** Add accounting-specific acceptance rules (invoice number presence, totals consistency, statement date parseability).
- **Build new:** Scoring rubric to auto-route documents into “auto-accept”, “review”, or “reject”.

**Modularity Assessment:** Mostly documentation/validation logic with low runtime coupling; easy to package as procedural Skill. **Overall modularity: HIGH.**

**Proposed SKILL.md Structure:**
```yaml
name: cre-ocr-quality-gate
description: Validate OCR outputs for accounting documents before data is accepted into finance workflows.
```
- Preconditions and test dataset setup
- Schema and metadata validation steps
- Domain-specific content checks
- Error-path testing and triage actions
- Pass/fail decision framework with confidence thresholds

**Confidence Level:** HIGH
