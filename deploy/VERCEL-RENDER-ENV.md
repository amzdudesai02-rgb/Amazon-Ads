# Vercel & Render – Environment Variables

Set these so the **frontend** (Vercel) talks to the **backend** (Render) and the backend allows the frontend origin.

---

## Vercel (frontend) – “backend” env

In **Vercel** → your project → **Settings** → **Environment Variables**, add:

| Name          | Value                               | Environments   |
|---------------|-------------------------------------|-----------------|
| **BACKEND_URL** | `https://YOUR-RENDER-SERVICE.onrender.com` | Production, Preview |

- Replace with your actual Render backend URL (e.g. `https://amazon-ads.onrender.com` or `https://api.amzads.amzdudes.io` if you use Hostinger for the API).
- The build runs `scripts/inject-backend-url.js`, which writes this value into `frontend/public/config.js`. The site then uses it for all API and “Connect Amazon Ads” requests.

**Example (Render):**
```env
BACKEND_URL=https://amazon-ads.onrender.com
```

**Example (your own API domain):**
```env
BACKEND_URL=https://api.amzads.amzdudes.io
```

---

## Render (backend) – “frontend” env

In **Render** → your **Web Service** (FastAPI) → **Environment** → **Environment Variables**, add (and keep any existing vars):

| Name               | Value                     | Notes |
|--------------------|---------------------------|--------|
| **FRONTEND_ORIGIN** | `https://amzads.amzdudes.io` | CORS and post-login redirect. No trailing slash. |

Also ensure these are set for the backend:

| Name                  | Value / Notes |
|-----------------------|----------------|
| **LWA_CLIENT_ID**     | From LWA app   |
| **LWA_CLIENT_SECRET** | From LWA app   |
| **LWA_REDIRECT_URI**   | `https://YOUR-RENDER-URL.onrender.com/auth/callback` (or your API domain) |
| **OPENAI_API_KEY**    | Your OpenAI key |
| **DATABASE_URL**      | Neon (or other) Postgres connection string |
| **AMAZON_ADS_PROFILE_ID** | Optional |
| **ADS_API_BASE**      | `https://advertising-api.amazon.com` |

**Example (frontend on Vercel at amzads.amzdudes.io):**
```env
FRONTEND_ORIGIN=https://amzads.amzdudes.io
```

If you use a custom API domain (e.g. api.amzads.amzdudes.io), set:

```env
LWA_REDIRECT_URI=https://api.amzads.amzdudes.io/auth/callback
FRONTEND_ORIGIN=https://amzads.amzdudes.io
```

---

## Summary

- **Vercel**: `BACKEND_URL` = your backend (Render or custom API) URL → injected into frontend at build time.
- **Render**: `FRONTEND_ORIGIN` = your frontend URL (e.g. `https://amzads.amzdudes.io`) so the backend allows CORS and redirects there.

After changing env vars, redeploy both the Vercel project and the Render service.

---

## If Vercel build fails: "Command node scripts/inject-backend-url.js exited with 1"

1. **Set Root Directory to `frontend`**  
   Vercel → Project → **Settings** → **General** → **Root Directory** → set to **`frontend`** and Save.  
   The build will then run from `frontend/`, use `frontend/vercel.json`, and find `frontend/scripts/inject-backend-url.js`.

2. **Add `BACKEND_URL`**  
   **Settings** → **Environment Variables** → add **`BACKEND_URL`** (e.g. `https://amazon-ads.onrender.com`) for Production.

3. **Redeploy**  
   Trigger a new deployment (push to main or **Redeploy** in the Deployments tab).

---

## Vercel build failed: "Command node scripts/inject-backend-url.js exited with 1"

1. **Set Root Directory to `frontend`**  
   Vercel → Project → **Settings** → **General** → **Root Directory** → set to **`frontend`** and Save.  
   That way the build runs from `frontend/`, uses `frontend/vercel.json`, and finds `frontend/scripts/inject-backend-url.js`.

2. **Add `BACKEND_URL`**  
   Vercel → **Settings** → **Environment Variables** → add **`BACKEND_URL`** (e.g. `https://amazon-ads.onrender.com`) for Production (and Preview if you use it).

3. **Redeploy**  
   Trigger a new deployment (e.g. push to main or **Redeploy** in the Deployments tab).
