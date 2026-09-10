# SE Intelligent Product Assistant

This is the first real project scaffold for the SE product-selection assistant.

## What is included

- FastAPI backend
- SQLite zero-setup mode
- PostgreSQL-ready configuration
- Product REST API
- First deterministic matching endpoint
- React + TypeScript frontend
- Seed importer
- 106 embedded demo product / series records extracted from the current prototype

## Phase 1 goal

Prove this chain first:

Customer requirements -> structured API request -> deterministic product matching -> ranked SE products

The AI conversation layer comes later.

## 1. Start backend — easiest mode

Open a terminal:

```bash
cd backend
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install packages:

```bash
pip install -r requirements.txt
```

Seed the database:

```bash
python -m app.seed
```

Run FastAPI:

```bash
uvicorn app.main:app --reload
```

Open:

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

## 2. Test matching

In Swagger open `POST /api/match` and try:

```json
{
  "application": "asset tracking",
  "technologies": ["cellular", "gnss"],
  "cellular_class": "Cat 1bis",
  "region": "Global",
  "low_power": true
}
```

## 3. Start frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

http://localhost:5173

## 4. PostgreSQL later

The backend runs with SQLite by default so you can start immediately.

To switch to PostgreSQL:

```bash
docker compose up -d db
```

Create `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://se_user:se_password@localhost:5432/se_product_assistant
CORS_ORIGINS=http://localhost:5173
```

Then seed again:

```bash
python -m app.seed
```

## API endpoints

- `GET /api/health`
- `GET /api/products`
- `GET /api/products/{id}`
- `POST /api/match`

## Conversational frontend

The React frontend now starts with:

`How can I help you?`

It extracts obvious requirements from the customer's first message, asks adaptive follow-up questions, builds the requirement profile, and submits the structured result to `POST /api/match`.

The result cards shown in React come from the FastAPI backend — they are not hard-coded frontend recommendations.

### Run both terminals

Backend:

```powershell
cd "$env:USERPROFILE\Documents\se-product-assistant\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd "$env:USERPROFILE\Documents\se-product-assistant\frontend"
npm run dev
```

Then open:

- Frontend: http://localhost:5173
- Swagger: http://localhost:8000/docs

## Next milestone

Replace the demo seed catalog with a real server-side SE catalog importer and a structured technical-feature schema. Then the same conversational frontend can match the full current SE portfolio.


# Phase 2 — Live catalog + structured features

This upgrade adds:

- server-side crawler for the configured SE product categories
- pagination support
- current product URL, availability and documents URL import
- `product_features` database table
- deterministic feature extraction (technology, Cat class, region, GNSS, Wi-Fi, architecture, antenna, form factor, temperature, certifications)
- structured-feature-aware matching
- catalog status endpoint
- frontend display of structured/live product data

## After installing this upgrade

Update Python packages:

```powershell
cd "$env:USERPROFILE\Documents\se-product-assistant\backend"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Backfill structured features for the products already in your database:

```powershell
.\.venv\Scripts\python.exe -m app.backfill_features
```

Test one live SE catalog page first:

```powershell
.\.venv\Scripts\python.exe -m app.import_catalog --source LTE --max-pages 1
```

Then check:

```text
http://localhost:8000/api/catalog/status
```

If the test import works, import all configured categories:

```powershell
.\.venv\Scripts\python.exe -m app.import_catalog --all
```

The full import performs many HTTP requests and can take time. It is intentionally a CLI/server-side process rather than a browser scraper.

## New API

- `GET /api/catalog/status`
- `GET /api/products` now includes `features`
- `GET /api/products/{id}` now includes `features`
- `POST /api/match` uses structured features first and text fallback second

## Important production note

This importer is the correct development bridge when there is no internal SE product API available. For production, an internal webshop/ERP/PIM API or database feed is preferable to HTML scraping.


## Phase 2.1 importer fix

Fixes:
- New live products now receive `manufacturer` and `category` before the first database INSERT.
- `--source LTE` filters by catalog category name only, preventing accidental matches such as EMI filter URLs.

Recommended retry:

```powershell
.\.venv\Scripts\python.exe -m app.import_catalog --source LTE --max-pages 1
```


# Phase 2.2 — Matcher quality fixes

This patch fixes issues found during the Wi-Fi 6 / host-based gateway validation:

- Wi-Fi 5 (`802.11ac`) no longer matches a Wi-Fi 6 requirement.
- Matching no longer searches for a bare digit such as `6`.
- Bluetooth forms like `BT5.3` and `BT/BLE` are recognized.
- `no LTE filter` no longer creates a false cellular capability.
- Product codes such as `W377-10C` are no longer misread as temperature ranges.
- Unknown mandatory fields lower confidence and are shown as `Not verified`, rather than receiving full credit.

After installing, rebuild the structured feature table:

```powershell
cd "$env:USERPROFILE\Documents\se-product-assistant\backend"
.\.venv\Scripts\python.exe -m app.backfill_features
```

Then restart FastAPI and repeat the same `POST /api/match` test.


# Phase 2.3 — Product-role filtering

Fixes found during the second Wi-Fi 6 validation:

- BLE version strings such as `BLE5.3` are detected as Bluetooth.
- Products with both PCB antenna and antenna pin are represented as `antenna = "both"`.
- Evaluation kits are excluded from normal module recommendations.
- Standalone antenna categories are excluded from normal module recommendations.
- Accessories are excluded from connectivity-module searches.
- An antenna requirement can match a product whose antenna capability is `both`.

After installing:

```powershell
cd "$env:USERPROFILE\Documents\se-product-assistant\backend"
.\.venv\Scripts\python.exe -m app.backfill_features
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Repeat the same Wi-Fi 6 host-based match request. The primary results should now remain modules/cards, without EVKs or standalone antennas.


# Phase 2.4 — Final matcher quality patch

This is the final matcher patch before the natural-language phase.

Fixes:
- standalone `WW` token in the part number is normalized to `region = "Global"`
- `antenna-pin` is normalized to `antenna = "external"`
- explicit low-power evidence is distinguished from unknown low-power data
- phrases such as `w/o low-power XTAL` become negative low-power evidence
- low-power unknown remains `Not verified` rather than being guessed
- equal technical scores are tie-broken by structured evidence completeness and live-catalog evidence

No database schema migration is required.

After installing, regenerate structured features:

```powershell
cd "$env:USERPROFILE\Documents\se-product-assistant\backend"
.\.venv\Scripts\python.exe -m app.backfill_features
```

Then restart FastAPI and repeat Scenario 1 and Scenario 2.


# Phase 2.5 — Preference penalty cleanup

Final cleanup before Phase 3:

- Explicit negative evidence on a preferred requirement now scores lower than unknown evidence.
- Example: `w/o low-power XTAL` is ranked below a product whose low-power behavior is merely unverified.
- `int.antenna` is normalized to `antenna = "internal"`.

After installing:

```powershell
cd "$env:USERPROFILE\Documents\se-product-assistant\backend"
.\.venv\Scripts\python.exe -m app.backfill_features
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```
\n\n# Phase 3.1 — Natural Language on top of final Phase 2.5 matcher\n\nThis package preserves all Phase 2.1–2.5 catalog/extractor/matcher fixes and adds the natural-language requirement engine.\n\nNew endpoints:\n\n- `POST /api/requirements/interpret`\n- `POST /api/requirements/recommend`\n\nExample request:\n\n```json\n{\n  "text": "I need a Wi-Fi 6 host-based module for an industrial gateway with external antennas.",\n  "current": null\n}\n```\n\nAfter installing, rebuild structured features once and restart FastAPI. No live-catalog re-import is required.\n

# Phase 3.2 — FAE-style recommendation UX

Frontend-only refinement on top of Phase 3.1:

- the first acknowledgement confirms all extracted technical facts, not only application/technology
- tied top scores are reported honestly instead of declaring an arbitrary single winner
- engineering differentiators are suggested when several products are equally valid
- low-power verification gaps are explicitly called out before design-in
- the recommendation panel shows the top 3 by default, with a Show all control

No catalog re-import and no feature backfill are required for this patch.


# Phase 3.3 — Technical tie-breaker qualification

The assistant now converts tied recommendations into real follow-up engineering questions.

New match criteria:
- host interface: SDIO / PCIe
- external antenna connector: U.FL / antenna pin
- antenna connection count
- minimum Bluetooth version
- maximum module footprint
- mechanical form factor
- dual-band GNSS (L1 + L5)

Behavior:
1. run the normal technical/commercial qualification
2. match against the SE catalog
3. if several products share the top score, ask one useful technical discriminator
4. re-run the matcher after the customer's answer
5. continue only while the catalog evidence can meaningfully distinguish the tied products

No database migration, catalog re-import, or feature backfill is required. The new tie-breakers are evaluated from the already imported product description and existing structured fields.


# Phase 3.4 — Agriculture + GNSS qualification

Fixes discovered in the GNSS agriculture scenario:

- recognizes agriculture / agricultural / precision farming, including the observed typo `argecltural`
- adds Agriculture / Precision Farming to application choices
- GNSS-only RTK ties now ask useful catalog-verifiable questions:
  - L1 versus L1 + L5
  - maximum module footprint when small size was requested
  - mechanical form factor when candidates differ

No database migration, catalog re-import, or feature backfill is required.


# Phase 3.5 — Readable UI + multi-select + editable answers

Frontend improvements:

- normal readable text at 100% browser zoom (`html` 100%, body 16 px)
- larger chat messages, product details, buttons, requirement values and status text
- multi-select questions for:
  - technologies
  - special requirements
  - project partners
- multi-select options stay selected until `Confirm choices`
- exclusive options such as `No special requirements` and `None yet` clear conflicting choices
- every displayed requirement has an `Edit` action
- Edit reopens the appropriate question and existing multi-select answers are preselected
- technical matching is refreshed after edited answers where appropriate
- technology edits remove incompatible dependent requirements to avoid stale filters

No database migration, catalog import, or feature backfill is required.
# Phase 4.1 — Product Evidence Foundation

This phase creates the evidence layer required before RAG / datasheet QA.

New database tables (created automatically by SQLAlchemy on backend startup):

- `product_documents`
  - discovered datasheets, integration manuals, user guides and other product documents
- `product_evidence`
  - one source-backed evidence record per product field/value

Evidence states:

- `verified`
- `inferred`
- `not_verified`
- `conflicting`

Important rule:

Catalog regex extraction is stored as `inferred`, not `verified`.
A later phase will promote fields to `verified` only when a datasheet/manual explicitly supports them.

New API endpoints:

- `GET /api/evidence/status`
- `GET /api/products/{product_id}/evidence`
- `GET /api/products/{product_id}/documents`

Build the initial evidence index:

```powershell
cd "$env:USERPROFILE\Documents\se-product-assistant\backend"
.\.venv\Scripts\python.exe -m app.sync_evidence --catalog
```

Test document discovery on only 10 product pages first:

```powershell
.\.venv\Scripts\python.exe -m app.sync_evidence --discover-documents --limit 10
```

Discover documents for one known product:

```powershell
.\.venv\Scripts\python.exe -m app.sync_evidence --discover-documents --product-id 9
```

This phase does NOT download or parse PDF contents yet. That is intentionally Phase 4.2.
# Phase 4.2 — PDF ingestion & verified evidence

This phase reads the discovered PDF documents and creates source-backed verified evidence.

New tables:

- `product_document_chunks`
  - extracted PDF text, page by page and chunk by chunk
- `product_evidence_locations`
  - links each verified evidence record to the exact PDF page/chunk and supporting quote

Important safety rule:

Phase 4.2 is intentionally conservative. It verifies only specifications that are explicitly present in the PDF text.

It currently recognizes:

- technology: Wi-Fi, Bluetooth, GNSS, cellular
- Wi-Fi generation
- Bluetooth version
- host/open/u-connect architecture
- interfaces such as SDIO, PCIe, USB, UART, SPI, I2C
- cellular class (Cat 1bis, Cat 4, LTE-M, NB-IoT, 5G RedCap)
- RTK / centimeter GNSS
- L1 + L5 dual-band GNSS
- explicit form-factor terms
- explicit operating-temperature ranges

It intentionally does NOT verify antenna variant or exact mechanical dimensions from a family Product Summary yet, because those may vary by SKU and require table-aware extraction.

The `ProductSummary` filename classifier is also fixed in this phase.

## Install dependency

After installing the patch:

```powershell
cd "$env:USERPROFILE\Documents\se-product-assistant\backend"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Restart FastAPI once so SQLAlchemy creates the two new tables.

## First test — parse only the discovered MAYA-W2 document

Your current document id is 9:

```powershell
.\.venv\Scripts\python.exe -m app.sync_evidence --parse-documents --document-id 9
```

Or use Swagger:

```text
POST /api/documents/9/parse
```

Then inspect:

```text
GET /api/evidence/status
GET /api/products/9/evidence?status=verified
GET /api/documents/9/chunks
```

Do not parse all documents yet. Validate the single MAYA-W2 Product Summary first.
# Phase 4.2.1 — Evidence quality fix

This patch must be applied before evidence-aware matching.

Fixes:

- `Bluetooth 4-wire UART` is no longer interpreted as Bluetooth version 4.
- Unicode PDF minus signs such as `−40 °C` are normalized correctly to `-40 °C`.
- Re-parsing a document explicitly removes old evidence locations/chunks first,
  preventing duplicate provenance records.
- `antenna` is no longer emitted as a `technology` catalog evidence value.

After installing:

1. rebuild the catalog-derived evidence layer once:
```powershell
.\.venv\Scripts\python.exe -m app.sync_evidence --catalog
```

2. re-parse MAYA-W2 document id 9:
```powershell
.\.venv\Scripts\python.exe -m app.sync_evidence --parse-documents --document-id 9
```

Then verify:

- no `bluetooth_version = 4`
- `temperature_min = -40`
- one location for each evidence/page/chunk
- no `technology = antenna`

No catalog re-import or feature backfill is required.
# Phase 4.2.2 — Catalog technology taxonomy correction

The Phase 4.2.1 evidence cleanup was too strict: it kept only Wi-Fi,
Bluetooth, GNSS and cellular as technologies.

This patch changes the rule to exclude only `antenna`, while preserving
other valid catalog technology labels such as:

- sensor
- storage
- display
- timing

After installing, rebuild catalog evidence once:

```powershell
.\.venv\Scripts\python.exe -m app.sync_evidence --catalog
```

No product import, feature backfill, or PDF re-parse is required for this patch.
# Phase 4.3 — Evidence-aware matching

Phase 4.3 connects the evidence layer to product recommendations.

Core safety principle:

`match_percent` remains the technical-fit score.

The new `evidence_score` is a separate documentation-confidence score. It
does not make a technically worse product become a better technical match.

Ranking order is now:

1. technical `match_percent`
2. evidence score
3. number of verified requested criteria
4. fewer conflicting evidence records
5. structured catalog completeness
6. live catalog status

This means evidence quality is only a tie-breaker between products with the
same technical score.

Each match response now contains:

- `evidence_score`
- `evidence_summary`
  - verified
  - inferred
  - not_verified
  - conflicting
- `criterion_evidence`
  - requested criterion
  - evidence status
  - evidence value
  - source type
  - source title
  - source URL
  - PDF page
  - confidence

Frontend product cards display:

- technical match %
- evidence coverage %
- Verified / Inferred / Not verified / Conflicting counts
- source links and page numbers for each requested criterion

No database migration, catalog import, evidence rebuild, or PDF re-parse is
required for Phase 4.3.

Recommended first validation request:

```json
{
  "application": "industrial gateway",
  "technologies": ["wifi"],
  "architecture": "host",
  "antenna": "external",
  "wifi_generation": "6",
  "host_interface": "sdio",
  "mandatory": []
}
```

For MAYA-W266, the currently parsed MAYA-W2 Product Summary should show
verified evidence for Wi-Fi capability, Wi-Fi 6, host architecture and SDIO.
Antenna remains inferred because Phase 4.2 intentionally avoids treating
family-summary antenna tables as variant-specific verified evidence.
# Phase 4.3.1 — Customer-friendly evidence UX

The evidence engine remains active in the backend and still participates as a
tie-breaker between technically equal products.

Customer-facing changes:

- removes the visible `Evidence %`
- removes visible evidence counters from the product card
- removes `Verified / Inferred / Not verified` wording from the main view
- keeps only the technical match percentage in the primary recommendation UI
- shows a calm trust badge:
  - `Based on manufacturer documentation`
  - or `Based on SE product data`
- moves sources and specification checks into a collapsed `Technical details`
  section
- replaces internal terminology with customer-friendly wording:
  - `Confirmed in technical documentation`
  - `Available in SE product data`
  - `Specification confirmation recommended`
  - `Technical review recommended`
- critical gaps are phrased as a design-in confirmation step rather than as
  uncertainty in the product itself

Backend evidence data is intentionally unchanged. This is a presentation-only
update.

No database migration, catalog import, evidence rebuild, or PDF parsing is
required.
# Phase 4.4 — Product Domain Router & Smarter Qualification

This phase removes the assumption that every customer request is a
connectivity request.

The assistant now detects the SE product area before asking technical
questions.

Supported routing areas:

- Connectivity / wireless
- GNSS / positioning
- Sensors
- Antennas / RF
- Displays / HMI
- Storage
- Timing
- Embedded computing
- Components / EMC
- Audio / haptics

Examples:

`I need a pressure sensor with I2C for an industrial pump`

routes to:

- product domain: Sensors
- product type: Pressure Sensors
- technology: sensor
- interface: I2C

It does not ask Wi-Fi, Bluetooth, cellular, antenna-module, or GNSS questions.

Current domain-specific catalog type qualification includes all eight sensor
categories in the SE catalog, plus antenna, display, storage, timing,
computing, component/EMC and audio/haptic category groups.

## Technical vs commercial qualification

Commercial/project questions were moved out of the initial technical
qualification.

The chatbot now follows:

1. understand product domain
2. understand application
3. ask domain-specific technical questions
4. recommend products
5. optionally ask whether SE support is wanted
6. only then collect:
   - new design vs replacement/redesign
   - existing component / part number for replacement projects
   - annual volume
   - project phase/timeline
   - project partners

The old early question `Is this a new project?` is removed.

Its useful replacement is:

`Is this a new design, or are you replacing an existing component?`

and it is asked only when the customer requests SE follow-up/support.

## Matching

Two generic backend matching inputs are added without a database migration:

- `catalog_category`
- `generic_interface`

`catalog_category` is a mandatory product-type filter.
`generic_interface` is a conservative preference because absence of an
interface in short catalog text does not prove the product lacks it.

The existing connectivity/GNSS matcher remains intact.

No catalog import, feature backfill, evidence rebuild, or PDF re-parse is
required.
# Phase 4.4.1 — Cleaner customer-facing header

Customer UX cleanup:

- removes the initial internal-parsing acknowledgement such as:
  `Thanks — I already picked up product area...`
- after the customer's first message, the assistant now moves directly to the
  next relevant question
- removes the hero marketing copy:
  `From customer requirement to suitable SE product.`
- removes the technical implementation subtitle
- removes the visible catalog counter from the top bar
- makes `SE PRODUCT ASSISTANT` the large primary page title
- keeps backend connection status for development diagnostics

This is a frontend-only update. No backend/database/catalog operations are required.
# Phase 4.4.2 — English/German UI + Customer/Developer Mode

## Language

The website now offers:

- EN
- DE

Changing the website language resets the current conversation so all new UI
and chatbot messages use the selected language consistently.

The selected UI language and the customer's input language are independent.

Examples:

- German UI + German request -> analyzed
- German UI + English request -> analyzed
- English UI + German request -> analyzed
- mixed technical English/German terminology -> analyzed by the deterministic
  parser where supported

Canonical product requirements remain language-neutral internally.

German deterministic parsing was added for common SE product terminology,
including sensor categories, Wi-Fi/cellular/GNSS, regions, architecture,
antenna wording, low-power wording and common application terms.

Manufacturer/catalog product descriptions are not machine-translated in this
phase; the chatbot UI and qualification flow are bilingual.

## Customer / Developer Mode

Customer mode is the default.

Customer mode hides:

- backend connection diagnostics
- catalog counts
- evidence score internals
- technical-profile completion diagnostics

Developer mode shows those diagnostics for development and FAE testing.

For a production public website, Developer mode should later be protected by
authentication/role access rather than exposed as a public switch.

## Application question

`What type of application or use case is this for?` is no longer a mandatory
qualification question.

Application is now treated as context:

- if the customer naturally provides it, the parser stores and uses it
- asset-tracking context can still trigger useful positioning/low-power logic
- agriculture context can still improve GNSS interpretation
- the chatbot does not block sensor, display, storage, timing, antenna, or
  other product selection just because application is unknown

This reduces unnecessary questions and keeps the flow focused on product
selection criteria that actually differentiate candidates.
## Domain precedence correction

The bilingual router distinguishes between a product and one of its
requirements:

- `Wi-Fi module with external antenna` -> Connectivity domain; antenna is a requirement
- `Wi-Fi-Modul mit externer Antenne` -> Connectivity domain; antenna is a requirement
- `external antenna for Wi-Fi` -> Antenna domain
- `externe Antenne für Wi-Fi` -> Antenna domain

This prevents antenna wording from hijacking a wireless-module request.


# Phase 4.5 — Deployment Ready

- single Docker deployment for React + FastAPI
- same-origin production API
- Render PostgreSQL
- one-time full live catalog bootstrap
- optional password-protected demo
- Developer Mode hidden in production
- Render Blueprint
- no secrets committed
- see `DEPLOY_RENDER.md`


# Phase 4.5.1 — Render frontend build fix

Fixes the Render Docker failure:

`TS5108: Option 'moduleResolution=node10' has been removed`

Changes:
- TypeScript `moduleResolution` changed from `Node` to `Bundler` for Vite.
- Frontend package versions are pinned instead of using `latest`.
- Vite environment typings explicitly include DEV/PROD/MODE/BASE_URL/SSR.
- Removes a stray TypeScript expression in the free-text answer parser.
- Handles optional edit-question options safely under strict TypeScript.

No database, catalog, or evidence rebuild is required.
