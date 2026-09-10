import base64
import hmac
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import Base, engine
from app.routers.health import router as health_router
from app.routers.products import router as products_router
from app.routers.requirements import router as requirements_router
from app.routers.evidence import router as evidence_router
from app.schemas import RootResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.middleware("http")
async def optional_demo_basic_auth(request: Request, call_next):
    if request.url.path == "/api/health" or not settings.demo_password:
        return await call_next(request)

    authorization = request.headers.get("Authorization", "")
    authenticated = False

    if authorization.startswith("Basic "):
        try:
            raw = base64.b64decode(authorization[6:]).decode("utf-8")
            username, password = raw.split(":", 1)
            expected_user = settings.demo_username or "se-demo"
            authenticated = (
                hmac.compare_digest(username, expected_user)
                and hmac.compare_digest(password, settings.demo_password)
            )
        except (ValueError, UnicodeDecodeError):
            authenticated = False

    if not authenticated:
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="SE Product Assistant Demo"'},
        )

    return await call_next(request)


origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(products_router)
app.include_router(requirements_router)
app.include_router(evidence_router)

@app.get("/api", response_model=RootResponse)
def api_root():
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
