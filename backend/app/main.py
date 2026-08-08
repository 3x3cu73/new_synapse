from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.oidc_routes import router as oidc_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.services.local_uploads import ensure_upload_dir

# -----------------------
# RATE LIMITER
# -----------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])

is_prod = settings.ENVIRONMENT == "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=None if is_prod else f"{settings.API_V1_STR}/openapi.json",
    docs_url=None if is_prod else f"{settings.API_V1_STR}/docs",
    redoc_url=None if is_prod else f"{settings.API_V1_STR}/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# -----------------------
# CORS
# -----------------------
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )

# -----------------------
# STATIC / UPLOADS
# -----------------------
upload_root = ensure_upload_dir().resolve()
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Local VM uploads (replaces Cloudinary)
app.mount(
    "/static/uploads",
    StaticFiles(directory=str(upload_root)),
    name="uploads",
)
# Other static assets (non-upload)
app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)

# -----------------------
# API ROUTES
# -----------------------
# OIDC at /api/auth/* (matches registered DevClub redirect URI)
app.include_router(oidc_router, prefix="/api")
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {"message": "Welcome to Synapse API V1"}


@app.get("/api/health")
def health():
    return {"status": "ok"}
