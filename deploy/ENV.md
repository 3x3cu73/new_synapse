# Synapse VM environment

Create `/opt/synapse/backend/.env` (never commit real secrets):

```env
PROJECT_NAME=Synapse
SECRET_KEY=generate-a-long-random-string
DATABASE_URL=postgresql+psycopg2://caic:YOUR_DB_PASSWORD@localhost:5432/synapse_app
ENVIRONMENT=production

FRONTEND_URL=https://synapse.devclub.in
PUBLIC_BASE_URL=https://synapse.devclub.in
BACKEND_CORS_ORIGINS=["https://synapse.devclub.in"]

UPLOAD_DIR=/opt/synapse/uploads

OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=https://synapse.devclub.in/api/auth/callback
OIDC_SCOPE=openid profile email kerberos entry_number hostel iitd
OIDC_DISCOVERY_URL=https://auth.devclub.in/api/oauth/.well-known/openid-configuration
OIDC_APP_NAME=Synapse

REDPAGE_API_BASE=https://superdirectory.devclub.in
REDPAGE_SERVICE_KEY=
REDPAGE_PERMISSIONS_AUDIENCE=synapse
REDPAGE_PERMISSIONS_ISSUER=https://superdirectory.devclub.in
REDPAGE_VERIFY_ASSERTION=true
REDPAGE_SYNC_ON_ME=true
```

Reuse the existing DevClub OAuth app redirect: `https://synapse.devclub.in/api/auth/callback`.

Event create/edit for club coordinators comes from Superdirectory
`GET /api/permissions/{kerberos}?audience=synapse` (`manage_events`, level ≤ 3).

## One-time VM prep

1. DNS: `synapse.devclub.in` → VM
2. Postgres: `CREATE DATABASE synapse_app OWNER caic;`
3. `bash deploy/deploy.sh`
