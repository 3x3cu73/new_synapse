from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Synapse"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days
    UPLOAD_FOLDER: str = "static/uploads"

    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://synapse.devclub.in",
    ]

    DATABASE_URL: str

    # Public site URL (used for redirects and absolute upload URLs)
    FRONTEND_URL: str = "http://localhost:3000"
    PUBLIC_BASE_URL: str = ""  # defaults to FRONTEND_URL when empty

    # Local uploads on the VM
    UPLOAD_DIR: str = "static/uploads"

    # DevClub / IIT Delhi OIDC
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_REDIRECT_URI: str = "http://localhost:8000/api/auth/callback"
    OIDC_SCOPE: str = "openid profile email kerberos entry_number hostel iitd"
    OIDC_DISCOVERY_URL: str = (
        "https://auth.devclub.in/api/oauth/.well-known/openid-configuration"
    )
    OIDC_APP_NAME: str = "Synapse"

    # Superdirectory universal permissions
    REDPAGE_API_BASE: str = "https://superdirectory.devclub.in"
    REDPAGE_SERVICE_KEY: str = ""
    REDPAGE_PERMISSIONS_AUDIENCE: str = "synapse"
    REDPAGE_PERMISSIONS_ISSUER: str = "https://superdirectory.devclub.in"
    REDPAGE_VERIFY_ASSERTION: bool = True
    REDPAGE_SYNC_ON_ME: bool = True

    # AWS (used by SQS service)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_REGION: str = "us-east-1"
    AWS_SQS_QUEUE_URL: str = ""

    # Environment
    ENVIRONMENT: str = "development"  # "development" or "production"

    class Config:
        env_file = ".env"

    @property
    def public_base_url(self) -> str:
        return (self.PUBLIC_BASE_URL or self.FRONTEND_URL).rstrip("/")


settings = Settings()
