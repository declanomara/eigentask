# Eigentask API – Minimal Keycloak OIDC Example

This is a minimal yet production-aligned implementation of OpenID Connect (OIDC) with Keycloak using FastAPI. It implements Authorization Code + PKCE, OIDC discovery, JWKS-based JWT verification, and RP-initiated logout.

## Environment variables

Set these in your environment (or a `.env` file if you load it):

- `KEYCLOAK_URL`: Base Keycloak URL, e.g. `https://keycloak.example.com/auth`
- `KEYCLOAK_REALM`: Keycloak realm name, e.g. `eigentask`
- `KEYCLOAK_CLIENT_ID`: OIDC client ID in the realm
- `KEYCLOAK_CLIENT_SECRET` (optional): Required if the client is confidential
- `REDIRECT_URI`: Callback URL exposed by this API, e.g. `http://localhost:8000/callback`
- `POST_LOGOUT_REDIRECT_URI` (optional): Where to land after logout
- `SESSION_SECRET`: Secret for session cookie encryption
- `COOKIE_DOMAIN` (optional): Domain for cookies
- `COOKIE_SECURE`: `true` in HTTPS environments

## Endpoints

- `GET /login`: Starts Authorization Code + PKCE, stores `state`, `nonce`, `code_verifier` in server session, and redirects to Keycloak `authorization_endpoint`.
- `GET /callback`: Validates `state`, exchanges the code at the `token_endpoint` (with `code_verifier`), and sets `access_token`, `refresh_token`, and `id_token` as HttpOnly cookies.
- `GET /protected`: Example protected route; validates the bearer token from `Authorization: Bearer` or `access_token` cookie against Keycloak JWKS.
- `GET /logout`: Clears cookies and redirects to Keycloak end-session endpoint.
- `GET /health`: Liveness check.

## Minimal Keycloak configuration

In your Keycloak realm:

1. Create a Client:
   - **Client Type**: Public (for local dev) or Confidential (with `KEYCLOAK_CLIENT_SECRET`)
   - **Standard Flow**: On (Authorization Code)
   - **Direct Access Grants**: Off
   - **Valid Redirect URIs**: include your `REDIRECT_URI` (e.g. `http://localhost:8000/callback`)
   - **Web Origins**: include your app origin if you have a separate frontend (e.g. `http://localhost:3000`), or `+` for dev
2. Client scopes/claims:
   - Ensure `email`, `profile` standard OIDC scopes are assigned
   - Optional: add protocol mappers to include roles (`realm_access.roles`) if needed
3. Realm keys:
   - Use RSA signing keys (default). JWKS will be served at `/.well-known/openid-configuration -> jwks_uri`.

## What data is exchanged and why

- `/.well-known/openid-configuration` (GET): Discovery of endpoints and issuer. Used to locate `authorization_endpoint`, `token_endpoint`, `jwks_uri`, and optionally `end_session_endpoint`.
- `GET authorization_endpoint`: Your app sends `client_id`, `redirect_uri`, `response_type=code`, `scope=openid ...`, `state`, `nonce`, and `code_challenge`.
- `POST token_endpoint`: Your app sends the authorization `code`, `redirect_uri`, `client_id` (or client auth), and `code_verifier` to get tokens.
- `JWKS` (GET): Your API fetches public keys to verify the JWT signature locally.
- `ID Token` (JWT): Proves user authentication; contains identity claims (subject, `email`, etc.). Used here for logout hints.
- `Access Token` (JWT): Authorizes API calls; validated on `/protected`.
- `Refresh Token` (opaque/JWT): Used to renew tokens (not implemented in this minimal example).

## Run locally

```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then:

1. Visit `/login` to authenticate.
2. You should land on `/protected` after callback with a valid `access_token` cookie.

### .env for development

This API loads environment variables from a local `.env` if present (via `python-dotenv`). Create `api/.env` with values like:

```
KEYCLOAK_URL=https://eigentask.com/auth
KEYCLOAK_REALM=eigentask
KEYCLOAK_CLIENT_ID=eigentask
# KEYCLOAK_CLIENT_SECRET=
REDIRECT_URI=http://localhost:8000/callback
POST_LOGOUT_REDIRECT_URI=http://localhost:8000/
SESSION_SECRET=change-me-dev-secret-32bytes-min
COOKIE_SECURE=false
FRONTEND_ORIGIN=http://localhost:5173
```

Note: `.env` is ignored by git; copy values from the example above.

## Notes

- The minimal example sets tokens in HttpOnly cookies to keep the sample simple. In production, prefer splitting frontend and backend concerns and use secure cookie settings with HTTPS.
- If you configure a confidential client, set `KEYCLOAK_CLIENT_SECRET` and ensure the client uses client secret basic or post as appropriate.

