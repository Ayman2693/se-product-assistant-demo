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
