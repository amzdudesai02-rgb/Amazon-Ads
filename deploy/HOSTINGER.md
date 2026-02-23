# Deploy Amazon Ads AI Agent on Hostinger VPS

Deploy the **backend** (FastAPI) and **frontend** (static files) on a Hostinger VPS. You need a **VPS plan** (not shared hosting); shared hosting does not support running a Python app with Uvicorn.

## Prerequisites

- Hostinger VPS (e.g. KVM 1 or higher)
- A domain pointed to your VPS IP (A record) — e.g. **api.amzads.amzdudes.io** for the API
- Neon (or other) PostgreSQL database already set up
- LWA app credentials and `OPENAI_API_KEY`

---

## 1. Connect to your VPS

Use SSH (Hostinger gives you the IP, username, and password in the panel):

```bash
ssh root@YOUR_VPS_IP
```

---

## 2. Install Python, Nginx, and Git

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx git
```

---

## 3. Create app directory and clone (or upload) project

```bash
sudo mkdir -p /var/www/amazon-ads
cd /var/www/amazon-ads
```

- **Option A – Git:**  
  If the project is in a Git repo:
  ```bash
  git clone https://github.com/YOUR_USER/YOUR_REPO.git .
  ```
  Or clone into a subdir and copy:
  ```bash
  git clone https://github.com/YOUR_USER/YOUR_REPO.git repo
  cp -r repo/backend . && cp -r repo/frontend . && cp -r repo/deploy .
  ```

- **Option B – Upload:**  
  Upload the project (e.g. with FileZilla or `scp`) so you have:
  - `/var/www/amazon-ads/backend/`
  - `/var/www/amazon-ads/frontend/`
  - `/var/www/amazon-ads/deploy/`

---

## 4. Python virtual environment and dependencies

```bash
cd /var/www/amazon-ads/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5. Environment variables

Create `.env` in the backend folder (do **not** commit this file):

```bash
nano /var/www/amazon-ads/backend/.env
```

Paste and fill in your values. Example for **API at api.amzads.amzdudes.io** and **frontend at amzads.amzdudes.io**:

```env
LWA_CLIENT_ID=your_lwa_client_id
LWA_CLIENT_SECRET=your_lwa_client_secret
LWA_REDIRECT_URI=https://api.amzads.amzdudes.io/auth/callback
OPENAI_API_KEY=your_openai_api_key
AMAZON_ADS_PROFILE_ID=your_ads_profile_id
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
FRONTEND_ORIGIN=https://amzads.amzdudes.io
ADS_API_BASE=https://advertising-api.amazon.com
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

## 6. Systemd service (run FastAPI with Uvicorn)

Copy the service file and enable it:

```bash
sudo cp /var/www/amazon-ads/deploy/amazon-ads-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable amazon-ads-api
sudo systemctl start amazon-ads-api
sudo systemctl status amazon-ads-api
```

The API will listen on `127.0.0.1:8000`. To restart after changes:

```bash
sudo systemctl restart amazon-ads-api
```

---

## 7. Nginx

**Option A – API only at api.amzads.amzdudes.io** (frontend hosted elsewhere, e.g. Vercel or amzads.amzdudes.io):

```bash
sudo cp /var/www/amazon-ads/deploy/nginx-api-amzads.conf /etc/nginx/sites-available/amazon-ads-api
sudo ln -sf /etc/nginx/sites-available/amazon-ads-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

**Option B – Full app on one domain** (frontend + API on same server):  
Use `nginx-amazon-ads.conf` and replace `YOUR_DOMAIN.com` with your domain, then:

```bash
sudo cp /var/www/amazon-ads/deploy/nginx-amazon-ads.conf /etc/nginx/sites-available/amazon-ads
sudo ln -sf /etc/nginx/sites-available/amazon-ads /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

---

## 8. Frontend: set backend URL

Point the frontend to your API domain so "Connect Amazon Ads" and agent calls hit your server. For **api.amzads.amzdudes.io**:

- If the frontend is deployed elsewhere (e.g. Vercel, or amzads.amzdudes.io), set `config.js` there (or in your build) to:

```js
window.APP_CONFIG = { BACKEND_URL: "https://api.amzads.amzdudes.io" };
```

- If you use the same Hostinger VPS and Option B above, use your single domain, e.g.:

```bash
echo 'window.APP_CONFIG = { BACKEND_URL: "https://YOUR_DOMAIN.com" };' | sudo tee /var/www/amazon-ads/frontend/public/config.js
```

---

## 9. SSL with Let's Encrypt (HTTPS)

For **api.amzads.amzdudes.io**:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.amzads.amzdudes.io
```

Follow the prompts. To renew:

```bash
sudo certbot renew --dry-run
```

---

## 10. Add custom domain (Hostinger / DNS)

In the **Add Custom Domain** modal:

1. **Domain name:** enter exactly  
   **`api.amzads.amzdudes.io`**
2. Click **Add Domain**, then go to the **Add DNS records** step.

At your DNS provider (where **amzdudes.io** is managed), add:

| Type | Name / Host        | Value        | TTL  |
|------|--------------------|-------------|------|
| **A** | `api.amzads`       | **YOUR_VPS_IP** | 3600 |

Use the VPS IP from your Hostinger panel. If your DNS uses full hostnames, set the A record for **api.amzads.amzdudes.io** to that IP. Wait a few minutes, then verify in the panel.

---

## 11. LWA and domain checklist

- In **Login with Amazon** (LWA) app settings, add  
  **`https://api.amzads.amzdudes.io/auth/callback`** as an allowed redirect URI.
- In **Amazon Partner Network**, ensure your LWA app is linked to the Ads API and the app is approved.

---

## Summary

| Item              | Path or value                          |
|-------------------|----------------------------------------|
| App root          | `/var/www/amazon-ads`                  |
| Backend           | `/var/www/amazon-ads/backend`          |
| Frontend static   | `/var/www/amazon-ads/frontend/public`  |
| Backend .env      | `/var/www/amazon-ads/backend/.env`     |
| Systemd service   | `amazon-ads-api` (port 8000)          |
| Nginx config      | `/etc/nginx/sites-available/amazon-ads` |

**Useful commands**

- Restart API: `sudo systemctl restart amazon-ads-api`
- API logs: `sudo journalctl -u amazon-ads-api -f`
- Nginx test: `sudo nginx -t`
- Nginx reload: `sudo systemctl reload nginx`

After deployment, open `https://YOUR_DOMAIN.com` and use “Connect Amazon Ads” to test the flow.
