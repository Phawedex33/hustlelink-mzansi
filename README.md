# hustlelink-mzansi

Backend auth API and runtime configuration for `hustlelink-mzansi`.

## Auth API Contract

Base prefix: `/api/auth`

Machine-readable contract:

- OpenAPI: `backend/docs/openapi.yaml`
- Postman collection: `backend/docs/postman/auth.collection.json`

### Register Provider

- Method: `POST`
- Path: `/register`
- Body (JSON):
```json
{
  "email": "provider@example.com",
  "password": "Pass1234!"
}
```
- Success (`201`):
```json
{
  "msg": "Provider registered successfully"
}
```
- Common errors:
  - `400` invalid JSON / missing fields / weak password / bad email format
  - `409` duplicate email

### Login Provider

- Method: `POST`
- Path: `/login`
- Body (JSON):
```json
{
  "email": "provider@example.com",
  "password": "Pass1234!"
}
```
- Success (`200`):
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>"
}
```
- Common errors:
  - `400` bad email format or invalid body
  - `401` invalid credentials
  - `429` rate limit exceeded

### Login Admin

- Method: `POST`
- Path: `/admin/login`
- Body (JSON):
```json
{
  "email": "admin@example.com",
  "password": "AdminPass123!"
}
```
- Success (`200`):
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>"
}
```
- Common errors:
  - `400` bad email format or invalid body
  - `401` invalid credentials
  - `429` rate limit exceeded

### Refresh Token (Rotation Enabled)

- Method: `POST`
- Path: `/refresh`
- Header: `Authorization: Bearer <refresh_token>`
- Success (`200`):
```json
{
  "access_token": "<new_jwt>",
  "refresh_token": "<new_jwt>"
}
```
- Behavior:
  - Old refresh token is revoked on use.
  - Reusing the old refresh token returns `401`.

### Logout

- Method: `POST`
- Path: `/logout`
- Header: `Authorization: Bearer <access_token>`
- Success (`200`):
```json
{
  "msg": "Logged out successfully"
}
```
- Behavior:
  - Current token is revoked persistently.
  - Using the same token again returns `401` (`Token has been revoked`).

### Get Current Identity

- Method: `GET`
- Path: `/me`
- Header: `Authorization: Bearer <access_token>`
- Success (`200`):
```json
{
  "provider_id": "1",
  "role": "provider"
}
```
- Common errors:
  - `401` missing/invalid/revoked token

### Role-Protected Health Endpoints

- `GET /admin/ping` requires role `admin`
- `GET /provider/ping` requires role `provider`
- Forbidden role returns:
```json
{
  "msg": "Forbidden"
}
```
with status `403`.

## Auth Headers

Use bearer auth for protected routes:

```http
Authorization: Bearer <token>
```

Request tracing:

- Optional request header: `X-Request-ID`
- Response always includes `X-Request-ID` (echoed or generated)
- Error payloads include `error.request_id` for correlation

## Environment Setup

1. Copy `backend/.env.example` to `backend/.env`
2. Set strong secrets (especially `JWT_SECRET_KEY`)
3. Run backend with your virtualenv active

## API Tooling

### OpenAPI

- File: `backend/docs/openapi.yaml`
- Contains request/response schemas, auth requirements, and error response mapping.

### Postman Collection

- File: `backend/docs/postman/auth.collection.json`
- Contains runnable flows for:
  - register -> login -> me
  - refresh rotation + old refresh token reuse check
  - logout revoked access token check
  - provider/admin role checks

Notes:

- Set `base_url` collection variable to your backend URL.
- Admin flow requires an existing admin account (bootstrap via CLI):
```powershell
cd backend
.\venv\Scripts\flask.exe --app run.py create-admin --email admin@example.com --password AdminPass123! --full-name "Platform Admin"
```

Frontend handoff guide:

- `frontend/auth-integration.md`

## Error Code Summary

- `400`: invalid request data
- `401`: invalid/missing/revoked token or invalid credentials
- `403`: authenticated but not authorized for route
- `409`: duplicate email on register
- `429`: login rate limit exceeded

Normalized error shape:

```json
{
  "msg": "Unauthorized",
  "error": {
    "code": "unauthorized",
    "message": "Unauthorized",
    "request_id": "..."
  }
}
```

## Local Commands

### Local Run + Test Checklist

1. Open terminal in project root:
```powershell
cd backend
```
2. Activate virtual environment:
```powershell
.\venv\Scripts\Activate.ps1
```
3. Install/update dependencies:
```powershell
pip install -r requirements.txt
```
4. Apply migrations:
```powershell
flask --app run.py db upgrade
```
5. Run API:
```powershell
python run.py
```
6. In a second terminal, run tests:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m pytest -q
```
7. Quick local checks:
```text
GET http://localhost:5000/health
GET http://localhost:5000/docs
GET http://localhost:5000/openapi.yaml
```

Run API locally:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python run.py
```

Run tests:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m pytest -q
```

Run migrations locally:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
flask --app run.py db upgrade
```

Create admin locally:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
flask --app run.py create-admin --email admin@example.com --password AdminPass123! --full-name "Platform Admin"
```
