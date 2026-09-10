# SE Product Assistant — Render Deployment

## Architecture

One public HTTPS URL serves both:
- React/Vite frontend
- FastAPI `/api/*`

Catalog data is stored in Render PostgreSQL.

## Step 1 — GitHub

Create a new PRIVATE repository named:

`se-product-assistant-demo`

Do not initialize it with a README.

Then run in PowerShell:

```powershell
cd "$env:USERPROFILE\Documents\se-product-assistant"

git init
git add .
git commit -m "Prepare SE Product Assistant demo deployment"
git branch -M main
git remote add origin https://github.com/YOUR-GITHUB-USER/se-product-assistant-demo.git
git push -u origin main
```

## Step 2 — Render Blueprint

In Render:

1. New -> Blueprint
2. Connect `se-product-assistant-demo`
3. Render detects `render.yaml`
4. Enter a private value for `DEMO_PASSWORD`
5. Apply the Blueprint

Render creates:
- a Docker web service in Frankfurt
- a PostgreSQL database in Frankfurt

## Step 3 — First deployment

The web service starts quickly with the fallback seed catalog.

After the first successful deploy, Render runs:

```text
python -m app.bootstrap_production
```

That imports the full configured SE catalog and rebuilds catalog evidence in
PostgreSQL. It skips the full import on future initialization if the database
already contains a full catalog.

## Step 4 — Share the demo

Open the `onrender.com` URL from the Render dashboard.

Credentials:
- username: `se-demo`
- password: the password you entered in Render

Share the URL and credentials separately with your team leader.

## Important

The Blueprint uses Render Free instances for a DEMO.

For a real company production deployment:
- use a persistent paid PostgreSQL plan
- use company authentication / SSO instead of demo Basic Auth
- use a company-owned custom domain
- move deployment ownership to the company workspace/account

Local development remains unchanged:
- frontend: http://localhost:5173
- backend: http://localhost:8000


## Refresh the full SE catalog after Phase 4.6

After the new version is Live:

1. Open `/docs` on the deployed site.
2. Find `POST /api/catalog/sync`.
3. Click **Try it out** -> **Execute**.
4. Then use `GET /api/catalog/sync-status`.
5. Wait until `"status": "completed"`.
6. Check `GET /api/catalog/status` to see the updated product count.

The sync runs in the background and writes to Render PostgreSQL.


## Phase 4.6.1 sync progress

The status endpoint now shows live progress, for example:

```json
{
  "status": "running",
  "sources_requested": 51,
  "sources_completed": 18,
  "sources_succeeded": 18,
  "products_seen": 742,
  "current_source": "TFT Displays"
}
```

When the crawler finishes, status briefly changes to:

`rebuilding_evidence`

and then:

`completed`

If needed, use:

`POST /api/catalog/sync-cancel`
