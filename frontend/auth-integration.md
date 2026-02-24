# Frontend Auth Integration

This document defines how frontend clients should integrate with the backend auth system.

## Base URL

- Local example: `http://localhost:5000`
- Auth prefix: `/api/auth`

## Runtime Capability Check

Call this once at app startup:

- `GET /api/auth/version`

Example response:

```json
{
  "api_version": "1.0.0",
  "refresh_rotation_enabled": true,
  "rate_limit_policy": "10 per minute",
  "supported_roles": ["provider", "admin"]
}
```

Use this to decide refresh behavior and role-gate setup.

## Endpoints Used by Frontend

### Register Provider

- `POST /api/auth/register`
- Body:
```json
{
  "email": "provider@example.com",
  "password": "Pass1234!"
}
```
- Success: `201`

### Login Provider

- `POST /api/auth/login`
- Body:
```json
{
  "email": "provider@example.com",
  "password": "Pass1234!"
}
```
- Success: `200` with:
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>"
}
```

### Login Admin

- `POST /api/auth/admin/login`
- Same body shape as provider login.
- Success: `200` with token pair.

### Refresh

- `POST /api/auth/refresh`
- Header: `Authorization: Bearer <refresh_token>`
- Success: `200`
- With rotation enabled (`refresh_rotation_enabled=true`), response includes a new refresh token and old one becomes invalid.

### Logout

- `POST /api/auth/logout`
- Header: `Authorization: Bearer <access_token>`
- Success: `200`
- Current token is revoked server-side.

### Identity / Role Probes

- `GET /api/auth/me` (needs access token)
- `GET /api/auth/provider/ping` (provider-only)
- `GET /api/auth/admin/ping` (admin-only)

## Token Storage Strategy

Recommended:

- Keep `access_token` in memory (React state/store).
- Keep `refresh_token` in secure storage with shortest practical exposure.
- Overwrite stored refresh token immediately on successful refresh when rotation is enabled.

## Request Strategy

1. Attach `Authorization: Bearer <access_token>` on protected requests.
2. On `401` from protected routes:
   - Attempt one refresh call.
   - If refresh succeeds, retry the original request once.
   - If refresh fails, clear tokens and redirect to login.

Do not loop refresh attempts.

## Logout Strategy

1. Call `POST /api/auth/logout` with current access token.
2. Clear local access + refresh tokens regardless of response.
3. Redirect to login.

## Role-Based Route Guards

After login or `/me`, read role:

- `provider` can access provider UI.
- `admin` can access admin UI.

If backend returns `403`, show forbidden screen and redirect to allowed area.

## Error Handling Map

- `400`: show validation errors (email format, missing fields, weak password).
- `401`: invalid credentials or expired/revoked/missing token.
- `403`: authenticated but wrong role.
- `409`: duplicate email during register.
- `429`: login attempts throttled; show retry/wait message.

## Notes

- `/api/auth/version` should be cached per session start and refreshed on app reload.
- Keep frontend behavior aligned with server runtime flags instead of hardcoding assumptions.

## Final Contract Choices

These are the agreed frontend contract decisions:

1. Token storage
- `access_token`: in memory only.
- `refresh_token`: persistent secure storage (e.g. secure local storage mechanism available in your stack).
- Always replace stored refresh token after successful refresh rotation.

2. Refresh trigger strategy
- On `401` from a protected request, try exactly one refresh.
- If refresh succeeds, retry the original request once.
- If refresh fails, clear tokens and force login.

3. Logout UX
- Call `POST /api/auth/logout`.
- Clear local tokens even if network call fails.
- Redirect user to login screen with a short “Session ended” message.

4. Forbidden route UX
- On `403`, show a dedicated forbidden/insufficient-permissions screen.
- Provide navigation back to an allowed route (dashboard/home).

## Example Client Wrapper

Reference implementation:

- `frontend/auth-client.ts`

This wrapper includes:

- login/register/me/logout helpers
- token store abstraction
- one-retry-on-401 refresh logic
- structured error object with `status` and `requestId`
