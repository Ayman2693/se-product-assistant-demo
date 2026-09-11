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


# Phase 4.5.2 — Website root fix

Production routing fix:

- `/` now belongs to the React/Vite frontend.
- API metadata moved from `/` to `/api`.
- `/api/*` and `/docs` continue to work normally.

This fixes the case where the public Render URL showed JSON instead of the website.


# Phase 4.6 — Full SE Catalog Coverage

The live importer now understands SE category landing pages.

Previous behavior:
- `/en/sbc/` -> no direct product cards -> 0 imported SBC products
- `/en/passivecap/` -> no direct product cards -> 0 imported capacitor products

New behavior:
- crawl the configured SE category
- discover child category/listing pages recursively
- stay inside the configured category URL prefix
- follow pagination on every discovered listing
- deduplicate by part number
- preserve the broad SE category for deterministic matching
- preserve the leaf listing title as an additional product tag

Examples:
- `/en/sbc/` -> `/en/sbc-picoitx/`, other SBC subcategories
- `/en/com/` -> SMARC, COM Express, Qseven, etc.
- `/en/passivecap/` -> capacitor subcategories such as tantalum listings

The 51 configured catalog roots still map the public SE product navigation, but
each root can now contain any number of child listing pages.

## Render Free catalog refresh

New protected endpoints:

- POST `/api/catalog/sync`
- GET `/api/catalog/sync-status`

`POST /api/catalog/sync` starts the full recursive catalog refresh in the
background and returns immediately. This avoids requiring Render Shell, which
is not available on Free web services.

After sync completes, catalog evidence is rebuilt automatically.

## Language/domain routing improvements

Directly understands, among others:

- capacitor / capacitors / Kondensator
- component / components / Bauteil / Komponente
- computing / computer / Rechner
- SBC / PicoITX
- SMARC / COM Express / Qseven
- embedded peripherals

No database migration is required.


# Phase 4.6.1 — Faster, visible catalog sync

The first recursive full-catalog implementation was intentionally broad but
proved too slow on Render Free.

Optimizations:

- child-category discovery is limited to one level below each configured SE root
- pagination is still followed for each root/child listing
- three catalog sources are fetched concurrently
- concurrency is capped at four even if a larger value is requested
- database writes remain sequential and transactional
- `/api/catalog/sync-status` now reports live progress:
  - `sources_requested`
  - `sources_completed`
  - `sources_succeeded`
  - `products_seen`
  - `current_source`
- evidence rebuild has its own `rebuilding_evidence` status
- new `POST /api/catalog/sync-cancel` endpoint

This design is substantially faster while keeping outbound load modest:
production uses at most three concurrent source crawls.

A redeploy safely stops any old in-memory background sync. Catalog imports are
upserts, so already committed products are not corrupted by interruption.


# Phase 4.7 — Capacitor engineering qualification

Capacitors now have their own technical qualification flow instead of being
treated as a category-only product.

Core interactive questions:

1. capacitance
2. minimum voltage rating
3. capacitor technology
4. mounting style
5. capacitance tolerance

The parser also accepts these directly in natural language, for example:

`47 uF 25 V tantalum SMD capacitor ±10%`

Advanced optional requirements are parsed and used when supplied:

- case size (0402, 0603, 0805, 1206, ...)
- maximum ESR
- minimum ripple current
- minimum lifetime
- operating temperature range
- explicit minimum stored energy

Catalog feature extraction now captures the corresponding fields from SE
product text when they are present. Unknown fields remain unknown; the matcher
does not invent missing specifications.

Engineering comparison rules:

- capacitance: nominal value must match
- rated voltage: product rating must be >= requested minimum
- tolerance: tighter is acceptable
- ESR: lower/equal is acceptable
- ripple current: higher/equal is acceptable
- lifetime: higher/equal is acceptable
- temperature: product range must cover the requested range
- stored energy: compares ideal 0.5*C*V^2 only when the customer explicitly
  asks for an energy requirement; it is labelled theoretical and is not a
  usable-energy guarantee

No database migration is required. Existing ProductFeature.raw_features_json is
used for capacitor-specific structured values. On Render, the production
bootstrap re-extracts structured features for the existing catalog on deploy,
so a second full catalog web crawl is not required for Phase 4.7.


# Phase 4.7.1 — Matching progress UX

While the product matcher is running, the customer UI now shows an animated
waiting indicator with:

- EN: `Searching for new results…`
- DE: `Suche nach neuen Ergebnissen…`

The panel also explains that the requirements are being compared with the SE
product database. During a refinement, existing results remain visible but are
dimmed until the refreshed ranking arrives.

The loading state uses `role="status"` / `aria-live="polite"` for accessibility.


# Phase 4.7.2 — Wi-Fi 5 + multi-select generations

Wi-Fi qualification now offers:

- Wi-Fi 4
- Wi-Fi 5
- Wi-Fi 6
- Wi-Fi 6E

The Wi-Fi generation question is multi-select. Selected generations are treated
as acceptable alternatives (OR), not as a requirement that one product somehow
belong to multiple generations simultaneously.

Example:

`Wi-Fi 5 + Wi-Fi 6`

matches products whose catalog generation is either Wi-Fi 5 or Wi-Fi 6.

Natural-language parsing also understands multiple generations in one request,
for example:

`I need Wi-Fi 5 or Wi-Fi 6`

No catalog resync or database migration is required.


# Phase 4.7.3 — Improved Bluetooth + GNSS qualification

Bluetooth LE is now asked during the main technical qualification, with:
- version open / not sure
- Bluetooth LE 5.0+
- Bluetooth LE 5.1+
- Bluetooth LE 5.2+
- Bluetooth LE 5.3+
- Bluetooth LE 5.4+
- Bluetooth LE 6.0+

Bluetooth remains single-select because this is a minimum-version threshold.

GNSS is now split into two technical questions:
1. Positioning performance:
   - standard meter-level
   - high precision / centimeter-level RTK
   - no fixed accuracy / not sure
2. Frequency-band capability:
   - L1 sufficient
   - dual-band L1 + L5 required
   - no preference / not sure

These questions happen before the first recommendation, not only as tie-breakers.
English and German wording are included.

No catalog sync or database migration is required.


# Phase 4.7.4 — Smarter question flow + prominent search UX

Qualification:
- removed the generic mandatory question
  `Are there any important design constraints or special requirements?`
- technical qualification now relies on product/domain-specific questions
- volunteered special requirements can still be captured, but they no longer
  block the first product search

Waiting state:
- full-page centered waiting overlay while matching is running
- large 92 px animated search indicator with magnifying-glass icon
- clear EN/DE waiting text
- customer cannot mistake a several-second product comparison for a frozen page

Result navigation:
- after results arrive, the viewport smoothly moves to recommendation #1
- chat auto-scroll is confined to the chat pane and no longer pulls the whole
  browser page toward the bottom

No database migration and no catalog sync are required.


# Phase 4.7.5 — Fast matching path

`POST /api/match` is optimized without reducing the catalog or changing the
technical ranking rules.

Pipeline:

1. conservative SQL pre-filter by requested product category and mandatory
   connectivity technologies
2. eager-load `Product.features` with the candidate query
3. run the existing deterministic technical scorer
4. find the Top-10 technical cutoff
5. retain every product tied at that cutoff
6. load evidence only for candidates that can still enter Top 10
7. load only evidence fields relevant to the current request
8. apply the existing evidence tie-break and return Top 10

Important correctness property:

`match_percent` remains the primary key. Evidence never promotes a lower
technical score over a higher one. All products tied at the Top-10 technical
cutoff are included in evidence evaluation.

The API response `count` still reports the number of technical matches, not
just the smaller evidence pool.

Render logs now include one timing line per match, for example:

`Match completed in 84.2 ms: sql_candidates=280 technical_matches=61 evidence_candidates=12 returned=10`

This makes real production latency measurable.

No database migration and no catalog sync are required.


# Phase 4.8 — Matching Quality Guard

The optimized matcher is now separated into a reusable technical candidate
engine. It supports both:

- fast SQL-prefiltered matching
- exhaustive full-catalog matching

`compare_fast_vs_exhaustive()` checks that the fast path does not lose any
technical matches or any product at the Top-10 technical cutoff.

Manual real-database check:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.quality_guard
```

Optional production shadow checking is available with:

`MATCH_QUALITY_GUARD_SAMPLE_RATE=0.02`

This samples 2% of `/api/match` calls *after the customer response* and logs
PASS/FAIL. Default is `0`, so normal production has no exhaustive-scan cost.

Match performance logging now separates:

- candidate load time
- technical scoring time
- evidence time
- total time


# Phase 4.9 — Adaptive Question Engine / Information Gain

After the initial request establishes product domain/category/technology, the
frontend asks `/api/requirements/adaptive-question` which technical question
should come next.

The engine:

1. builds the current technically valid candidate set
2. measures catalog coverage for each unanswered engineering field
3. calculates Shannon information gain from the field distribution
4. asks the field that best separates the remaining candidates
5. keeps core engineering questions required even when data coverage is weak
6. falls back to the existing deterministic local flow if the adaptive API is
   unavailable

For capacitors, capacitance and voltage button values can be generated from the
actual remaining catalog values instead of relying only on hard-coded examples.

Customer UI gets a short explanation such as:

`This is the most useful next detail for narrowing 86 remaining candidates.`

Developer Mode additionally shows information-gain bits and catalog coverage.

No database migration and no catalog sync are required.


# Phase 5.0 — Product Family + SKU Knowledge Graph

Phase 5.0 adds a conservative family/SKU graph layer.

## Safety rule

The system does **not** derive a customer-facing family by truncating or
guessing from a part number.

For example, `NORA-B206-00B` is not automatically assigned to `NORA-B2`
because the names look similar.

A verified family membership is created only when the available data explicitly
states a compatible family/series, such as:

- structured `family` / `series` catalog field
- `NORA-B2 series` in catalog text/tags
- `MAYA-W2 series data sheet` in a linked document title

The explicitly stated family must also be compatible with the SKU prefix.
This blocks unrelated chipset-family text from becoming an SE product-family
relationship.

## New persisted graph tables

- `product_families`
- `product_family_members`

They store provenance, confidence, and verification status.

The existing startup `python -m app.seed` now rebuilds the automatic family
graph after structured product features are refreshed. Existing manually
curated family rows are designed to be preservable in future curation work.

Manual rebuild:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.rebuild_families
```

## New APIs

- `GET /api/families/status`
- `GET /api/families`
- `GET /api/families/{family_id}`
- `POST /api/families/rebuild`
- `GET /api/products/{product_id}/knowledge-graph`

The virtual product graph exposes nodes/edges such as:

`SKU -> member_of -> Family`  (verified explicit provenance)

`SKU -> supports -> Technology`  (catalog-derived / inferred)

`SKU -> documented_by -> Document`  (verified document link)

Document links are provenance links; they are not treated as proof that every
statement in a family document applies to every SKU.

## Recommendation UX

`/api/match` and natural recommendations now annotate returned SKUs with a
verified family when one is available.

The frontend groups sibling matching SKUs into one solution group only when:

- membership is verified
- the family contains at least two verified SKUs

The highest-ranked SKU remains the recommended variant. Sibling variants are
available under an expandable `matching SKUs` section.

This prevents Top 3 from being consumed by three variants of the same verified
family while leaving unverified products completely unchanged.

## Database deployment

This phase adds new tables. No destructive migration is required in the
current project architecture because `Base.metadata.create_all()` creates the
new tables on deployment. The normal Render startup seed then rebuilds the
derived family graph automatically.

No full web catalog sync is required solely for Phase 5.0.


# Phase 5.0.1 — Adaptive Flow & Bluetooth Ranking Fix

This patch fixes issues discovered in a real Bluetooth-only customer flow.

## Adaptive flow

Technical answers no longer bypass the adaptive engine through the legacy
`tiebreaker` shortcut.

Every technical answer now returns to `askNext()`:

`answer -> adaptive question engine -> next useful question OR match`

Selecting `Bluetooth required, version open` is treated as a completed
Bluetooth-version qualification, so the assistant does not ask the same
version question again.

## Bluetooth criterion deduplication

When `technologies=["bluetooth"]` already exists, `bluetooth_required=true`
does not add a second Bluetooth-capability scoring criterion.

A product now gets one Bluetooth capability reason, not both:

- `BLUETOOTH capability`
- `Bluetooth capability`

## Connectivity solution-scope ranking

When technical match percentage is equal, the matcher prefers a solution that
does not add unrequested connectivity technologies.

Example for a Bluetooth-only request:

- Bluetooth-only module: `solution_scope_score = 100`
- Wi-Fi + Bluetooth module: `solution_scope_score = 85`

Important: this is a tie-break only.

- Extra technologies do not eliminate the product.
- They do not lower the technical `match_percent`.
- A higher technical match always beats a lower one.
- Scope is evaluated before evidence only when technical fit is tied.

The API returns:

- `solution_scope_score`
- `extra_technologies`

The frontend displays `Focused solution` for exact-scope products or
`Also includes WI-FI` for broader multiradio alternatives.

This prevents a Bluetooth-only request from presenting MAYA/JODY multiradio
products as indistinguishable from Bluetooth-focused ANNA/NORA solutions when
all other collected requirements are equal.

No database migration and no catalog sync are required.


# Phase 5.0.2 — Deep Tie Discrimination

The adaptive engine now has two stages.

## 1. Core qualification

Core technical questions still use the complete current candidate set and are
asked even when catalog coverage is weak.

## 2. Deep tie discrimination

After core qualification is complete, the engine inspects only the products
that share both:

- the highest technical `match_percent`
- the highest `solution_scope_score`

It then looks for useful optional discriminators such as:

- external antenna connector (`U.FL` vs antenna pin)
- host interface (`SDIO` vs `PCIe`)
- antenna connection count
- form factor
- module footprint

An optional question is asked only when:

- more than one top candidate remains
- catalog coverage for that field is at least 40%
- there are at least two known values
- information gain is at least 0.25 bits

This prevents sparse catalog metadata from causing unnecessary customer
interrogation.

Example:

`Bluetooth -> Open CPU -> External antenna`

If ten top candidates remain and five use U.FL while five use antenna pins, the
assistant continues with:

`Which external antenna connection do you prefer?`

rather than immediately declaring all ten products technically equivalent.

If the customer selects `Either is acceptable` / `No preference`, the frontend
passes the field in `answered_open_fields`, preventing the same optional
question from being repeated.

Developer Mode exposes the adaptive mode (`qualification` or `tie_break`) in
the information-gain hint.

No database migration and no catalog sync are required.


# Phase 5.0.3 — Engineering Qualification Safety

This patch separates **technical match percentage** from **recommendation
confidence** so a high score is never presented as fully confirmed when an
explicit customer requirement is still unknown.

## Host interface becomes core qualification

When `architecture = host`, the assistant now asks:

`Which host interface does your system support?`

Options remain SDIO, PCIe, SDIO or PCIe, and No preference / not sure.

This question runs in `qualification` mode. It is not merely a tie-breaker,
because an SDIO-only host cannot use a PCIe-only module.

## Recommendation confidence

Every match now returns:

- `recommendation_confidence`
- `recommendation_confidence_label`
- `verification_required`
- `verification_issues`

The three states are:

- `verified_fit` — all represented requested criteria are verified and there
  are no unresolved matcher warnings.
- `provisional_fit` — no explicit requirement is unresolved, but some fit is
  based on inferred/catalog-derived evidence or manufacturer verification is
  incomplete.
- `fae_verification_required` — at least one explicit requested requirement is
  unknown/conflicting, or the deterministic matcher emitted `Not verified:`.

Example: if the customer requires `footprint <= 100 mm²` and the catalog cannot
confirm the footprint, a product can still be returned as a candidate, but the
assistant calls it the strongest **provisional** match and explicitly states
that datasheet / SE FAE verification is required before design-in.

## Ranking safety

Technical score remains authoritative. For equal technical score and equal
solution scope only, the tie order is:

`Verified fit > Provisional fit > FAE verification required`

and then normal evidence quality is used.

No database migration and no catalog sync are required.


# Phase 5.0.4 — Evidence Safety Calibration

Live testing showed that Phase 5.0.3 could over-escalate normal catalog matches
to `FAE verification required` when the evidence table lagged behind the current
structured product features.

The safety policy is now:

- Positive deterministic structured/catalog match + missing evidence row
  → `Provisional fit`
- Explicit deterministic `Not verified:` warning
  → `FAE verification required`
- Conflicting evidence
  → `FAE verification required`
- Fully manufacturer-verified requested criteria
  → `Verified fit`

A missing evidence row by itself is no longer a hard engineering escalation.

When structured matching positively confirms a criterion, stale/missing
ProductEvidence is reconciled as `structured_catalog_fallback` with status
`inferred`. It is never promoted to `verified`.

Normal startup seeding also refreshes catalog-derived evidence after structured
feature extraction, while preserving datasheet/manual evidence.

No database migration and no full catalog sync are required.


# Phase 5.0.5 — Cleaner Customer UX & Actionable Handoff

## Cleaner recommendation cards

Customer cards now show only the essential hierarchy at the top:

- `100% technical match`
- `Verified` / `Catalog-supported` / `Needs verification`
- `Focused` or `Includes <technology>`

The duplicated top-level `Based on SE product data` badge and long provisional
explanation were removed. Evidence remains available under Technical details.

Evidence icons are now semantically strict:

- `✓` manufacturer/document-verified
- `~` inferred / SE catalog data
- `?` not verified
- `!` conflicting

## Bluetooth wording

The top-level connectivity selector now says `Bluetooth`, not only
`Bluetooth LE`. The detailed minimum-version question remains Bluetooth LE
because that field is specifically an LE-version requirement.

## Better post-result flow

The old generic `Yes, continue with project details` questionnaire is replaced
with an action-oriented next step:

- Technical review with an SE FAE
- Price / availability / samples
- No — the recommendation is enough

Technical follow-up asks which result should be reviewed and what the FAE
should focus on.

Commercial follow-up asks which result, quantity, and when parts are needed.

These handoff fields are explicitly separated from technical matching and the
UI states that they do not change the ranking.

## Greeting

The opening message is now:

`I am the SE Product Assistant. How can I help you?`

No database migration and no catalog sync are required.


# Phase 5.0.6 — Full SE Catalog Coverage

The catalog crawler is now coverage-first for the active SE product tree.

## Why this patch was needed

Some SE shop categories use child URLs that do not inherit the parent URL
prefix. The important example is:

- Crystals root: `/en/timxtal/`
- kHz Crystals child: `/en/timkhz/`

The former prefix-only crawler could not discover `/en/timkhz/`, even though it
is an official child category.

## Explicit nested listing seeds

The following shop listing roots are now guaranteed to be crawled under their
canonical assistant category:

### Crystals

- `/en/timxtal/`
- `/en/timxtalmhz/`
- `/en/timkhz/`

### Oscillators

- `/en/timosc/`
- `/en/timoscmhz/`
- `/en/timosckhz/`

### Timing IC

- `/en/timic/`
- `/en/timicnetsync/`
- `/en/timicjittercleaner/`
- `/en/timicbuffer/`

### Chokes

- `/en/emechchokes/`
- `/en/emechchokecurrent/`
- `/en/emechchokessuppres/`
- `/en/emechchokesatur/`

All imported products from these nested pages retain the canonical categories
`Crystals`, `Oscillators`, `Timing IC`, and `Chokes`.

## Deeper recursive discovery

The normal catalog sync now permits up to three descendant category levels
instead of only one. Safety guards remain in place:

- same SE host only
- product detail pages are excluded from category traversal
- visited-page de-duplication
- maximum 100 category/listing pages per canonical source
- maximum 100 pagination pages per listing

## Coverage visibility

`GET /api/catalog/status` now also returns:

- `category_counts`
- `zero_categories`

This makes missing/empty configured categories visible immediately after a
catalog refresh.

## Important deployment step

This code patch changes what future crawls can reach. It does not magically add
the missing products to an already-populated database.

After deployment, run one full catalog refresh:

`POST /api/catalog/sync`

and monitor:

`GET /api/catalog/sync-status`

For local development:

`python -m app.import_catalog --all`

No database migration is required.


# Phase 5.0.7 — Antenna Engineering Qualification

Standalone antenna searches are now qualified by engineering requirements
instead of assigning every product in one antenna category the same 100% fit.

The assistant asks for the target radio system, then the relevant band
capability, and for GNSS whether the antenna must be active or passive.
Physical footprint remains an adaptive tie-breaker when dimensions can
separate otherwise equivalent top candidates.

Known mismatches are hard mismatches. Missing catalog data remains
`Not verified`; absence is never invented.

The feature extractor now derives catalog-supported antenna application,
band capability and active/passive status into `raw_features_json`.
No database migration is required. Normal startup re-extraction refreshes
these raw features, and a catalog sync refreshes imported products/evidence.

When several products are still genuinely equal on technical fit and solution
scope, the customer UI says `Top technical match · tied` instead of implying
an arbitrary #1 winner.

# Phase 5.1 — Universal Engineering Qualification Engine

Phase 5.1 replaces the pattern of adding one bespoke matcher per product type
with a schema-driven engineering layer shared by the complete configured SE
catalog.

## Core architecture

`catalog category -> engineering profile -> normalized product features -> adaptive question -> deterministic constraint -> ranking -> evidence`

The implementation introduces:

- `backend/app/services/engineering_profiles.py`
  - one reusable field library;
  - a category profile for every configured SE catalog category;
  - 51 category profiles and 63 reusable engineering fields.
- `backend/app/services/engineering_features.py`
  - conservative extraction and unit normalization;
  - deterministic comparison semantics;
  - display formatting for normalized values.
- `MatchRequest.engineering_requirements`
  - carries category-specific requirements without expanding the API schema for
    every future component family.
- `MatchRequest.answered_engineering_fields`
  - remembers `No preference / not sure` answers so the adaptive engine does
    not ask the same question repeatedly.

## Adaptive behavior

The assistant does **not** ask every field in a category profile.

For the current candidate set it evaluates catalog coverage and information
gain and asks only a field that can materially discriminate the remaining
products. Constant fields and poorly populated fields are skipped.

A selected engineering value becomes a deterministic constraint:

- known match -> positive technical fit;
- known mismatch -> product is rejected;
- missing value -> `Not verified`, never silently treated as a mismatch.

An open answer is remembered but is not used as a hard filter.

## Category coverage

Profiles exist for all 51 configured categories, including:

- Crystals: frequency, load capacitance, tolerance, stability, ESR, drive
  level, mounting, package, temperature.
- Oscillators: frequency, oscillator type, output standard, supply voltage,
  stability, phase jitter, mounting, package, temperature.
- Timing IC / RTC: timing function, frequency, interfaces, output, supply,
  package and temperature.
- Chokes: choke type, inductance, rated current, DCR, impedance, test
  frequency, mounting and temperature.
- Relays / contactors / switches / connectors: electrical ratings, contact
  configuration, coil voltage, pitch, positions and mounting where relevant.
- Sensors: category-specific measurement range, accuracy, interface, supply,
  package and operating conditions.
- Displays: diagonal, resolution, interface, touch and supply.
- Flash storage / embedded computing: capacity, storage interface, CPU
  architecture, RAM, on-board storage and Ethernet capability.
- Audio / haptics, EMC filters, antennas and wireless categories also receive
  reusable profile fields in addition to their existing specialized logic.

## Natural-language support

When the customer's first sentence already contains a category-specific value,
the same normalization layer can capture it directly. Example:

`32.768 kHz crystal, 9 pF, ±20 ppm`

becomes normalized requirements for frequency, load capacitance and tolerance.

Typed values with engineering units are normalized as well, e.g. MHz/kHz,
mA/A, mΩ/Ω/kΩ, mH/µH, TB/GB and bar/kPa.

## Evidence

Extracted engineering values are added to the catalog evidence layer using
`engineering:<field>` field names. This keeps technical fit and evidence
confidence separate and preserves the existing `Verified / Catalog-supported /
Needs verification` safety model.

## Developer audit endpoints

`GET /api/requirements/engineering-profiles`

returns the configured category/field schema.

`GET /api/requirements/engineering-coverage`

reports, for the current database, how many products in each category have
structured engineering data and the coverage percentage of every configured
field. This is the primary audit tool for deciding which category extractor
needs to be improved next.

## Data model / deployment

No database migration is required. Universal engineering features are stored
inside the existing `ProductFeature.raw_features_json` structure.

Normal application startup re-extracts structured features for every product
and refreshes catalog-derived evidence, so deploying this version is enough to
backfill the current database. A catalog sync is only needed when the website
product data itself also needs refreshing.


# Phase 5.1.2 — Catalog Recovery, Professional GNSS & Handoff Email

- Corrects the static `CMX655DQ6` category from `Audio Codec` to canonical `Audio Codecs`; the static seed previously overwrote the live category on startup.
- Bootstraps visible CML Micro codec products and keeps `/en/audocodec/` as the authoritative live source.
- Adds a minimum source coverage guard so a zero-row codec crawl is reported instead of silently accepted.
- Uses more professional GNSS accuracy and receiver-band qualification wording.
- Generates ready-to-open email drafts after technical FAE or commercial follow-up qualification.
- Adds `Hello` to the opening message.
- Moves restart below Send and removes reset controls from the hero and chat header.
