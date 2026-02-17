import json
import os
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Optional
import secrets

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import httpx
from openai import OpenAI

import db


load_dotenv()

LWA_AUTH_URL = "https://www.amazon.com/ap/oa"
LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
ADS_API_BASE = os.getenv("ADS_API_BASE", "https://advertising-api.amazon.com")

LWA_CLIENT_ID = os.getenv("LWA_CLIENT_ID", "")
LWA_CLIENT_SECRET = os.getenv("LWA_CLIENT_SECRET", "")
LWA_REDIRECT_URI = os.getenv("LWA_REDIRECT_URI", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AMAZON_ADS_PROFILE_ID = os.getenv("AMAZON_ADS_PROFILE_ID", "")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Amazon Ads AI Agent")

# CORS: allow local dev plus deployed frontend.
frontend_origin = os.getenv("FRONTEND_ORIGIN")
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if frontend_origin:
    allowed_origins.append(frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Redirect root to frontend or return API info."""
    if frontend_origin:
        return RedirectResponse(url=frontend_origin, status_code=302)
    return {"service": "Amazon Ads AI Agent API", "docs": "/docs", "health": "/health"}


# Initialise database and load any stored tokens into memory.
db.init_db()
TOKENS: Dict[str, str] = {}
stored = db.get_tokens()
if stored is not None:
    if stored.access_token:
        TOKENS["access_token"] = stored.access_token
    if stored.refresh_token:
        TOKENS["refresh_token"] = stored.refresh_token
    if stored.expires_at:
        TOKENS["expires_at"] = str(stored.expires_at.replace(tzinfo=timezone.utc).timestamp())


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/auth/login")
def auth_login() -> RedirectResponse:
    """
    Start Login with Amazon (LWA) OAuth2 authorization code flow.
    """
    if not (LWA_CLIENT_ID and LWA_REDIRECT_URI):
        raise HTTPException(
            status_code=500,
            detail="LWA_CLIENT_ID and LWA_REDIRECT_URI must be configured.",
        )

    # Generate a per-login state value and keep it in memory for validation.
    state_value = secrets.token_urlsafe(16)
    TOKENS["oauth_state"] = state_value

    params = {
        "client_id": LWA_CLIENT_ID,
        "scope": "advertising::campaign_management",
        "response_type": "code",
        "redirect_uri": LWA_REDIRECT_URI,
        "state": state_value,
    }
    url = f"{LWA_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@app.get("/auth/callback")
async def auth_callback(code: str, state: Optional[str] = None) -> dict:
    """
    Handle OAuth2 callback and exchange code for tokens.
    """
    # Validate state to protect against CSRF.
    expected_state = TOKENS.get("oauth_state")
    if expected_state and state != expected_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")

    if not (LWA_CLIENT_ID and LWA_CLIENT_SECRET and LWA_REDIRECT_URI):
        raise HTTPException(
            status_code=500,
            detail="LWA_CLIENT_ID, LWA_CLIENT_SECRET and LWA_REDIRECT_URI must be configured.",
        )

    async with httpx.AsyncClient() as http_client:
        resp = await http_client.post(
            LWA_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": LWA_REDIRECT_URI,
                "client_id": LWA_CLIENT_ID,
                "client_secret": LWA_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=resp.text)

    data = resp.json()
    TOKENS["refresh_token"] = data.get("refresh_token", "")
    TOKENS["access_token"] = data.get("access_token", "")
    # Store an absolute expiry time (seconds since epoch).
    expires_in = data.get("expires_in") or 0
    expires_at_ts = time.time() + int(expires_in) - 60  # refresh 1 min early
    TOKENS["expires_at"] = str(expires_at_ts)

    # Persist tokens to PostgreSQL
    db.save_tokens(
        access_token=TOKENS["access_token"],
        refresh_token=TOKENS["refresh_token"],
        expires_at=datetime.fromtimestamp(expires_at_ts, tz=timezone.utc),
    )
    # Clear state once used.
    TOKENS.pop("oauth_state", None)

    # After successful auth, redirect to frontend if configured.
    if frontend_origin:
        return RedirectResponse(url=f"{frontend_origin}/connected?status=ok", status_code=302)

    return {"status": "ok"}


async def refresh_access_token() -> None:
    """
    Use the stored refresh token to obtain a new access token.
    """
    refresh_token = TOKENS.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token; re-authenticate.")

    if not (LWA_CLIENT_ID and LWA_CLIENT_SECRET):
        raise HTTPException(
            status_code=500,
            detail="LWA_CLIENT_ID and LWA_CLIENT_SECRET must be configured.",
        )

    async with httpx.AsyncClient() as http_client:
        resp = await http_client.post(
            LWA_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": LWA_CLIENT_ID,
                "client_secret": LWA_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail=f"Failed to refresh token: {resp.text}")

    data = resp.json()
    TOKENS["access_token"] = data.get("access_token", "")
    expires_in = data.get("expires_in") or 0
    expires_at_ts = time.time() + int(expires_in) - 60
    TOKENS["expires_at"] = str(expires_at_ts)

    db.save_tokens(
        access_token=TOKENS["access_token"],
        refresh_token=refresh_token,
        expires_at=datetime.fromtimestamp(expires_at_ts, tz=timezone.utc),
    )


async def get_access_token() -> str:
    """
    Return a valid access token, refreshing it when necessary.
    """
    token = TOKENS.get("access_token")
    expires_at_str = TOKENS.get("expires_at")

    needs_refresh = False
    if not token:
        needs_refresh = True
    elif expires_at_str:
        try:
            expires_at = float(expires_at_str)
            if time.time() >= expires_at:
                needs_refresh = True
        except ValueError:
            needs_refresh = True

    if needs_refresh:
        await refresh_access_token()
        token = TOKENS.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated with Amazon Ads.")

    return token


async def list_campaigns(profile_id: str):
    """
    Example Amazon Ads API wrapper: list campaigns.
    """
    access_token = await get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": LWA_CLIENT_ID,
        "Amazon-Advertising-API-Scope": profile_id,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient() as http_client:
        resp = await http_client.get(f"{ADS_API_BASE}/v2/campaigns", headers=headers)
    resp.raise_for_status()
    return resp.json()


async def get_profiles():
    """
    Fetch available Amazon Ads profiles for the authenticated account.
    """
    access_token = await get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": LWA_CLIENT_ID,
        "Accept": "application/json",
    }
    async with httpx.AsyncClient() as http_client:
        resp = await http_client.get(f"{ADS_API_BASE}/v2/profiles", headers=headers)
    resp.raise_for_status()
    return resp.json()


@app.get("/ads/profiles")
async def ads_profiles():
    """
    Convenience endpoint to inspect Ads profiles and copy profileId values.
    """
    return await get_profiles()


class ChatRequest(BaseModel):
    message: str
    profile_id: Optional[str] = None
    intent: Optional[str] = None  # optional hint from frontend later
    media_plan: Optional[str] = None  # optional: pasted/uploaded media plan for campaign creation


class ChatResponse(BaseModel):
    reply: str


# --- Campaign targeting / audience suggestions ---

class AudienceSuggestion(BaseModel):
    name: str
    description: str
    reason: str
    category: Optional[str] = None   # e.g. In-market, Sporting Goods
    fee: Optional[str] = None        # e.g. $1.00
    audience_id: Optional[str] = None  # optional segment ID for display


class AudienceSuggestionsRequest(BaseModel):
    goal: str
    product_or_category: Optional[str] = None
    budget_note: Optional[str] = None


class AudienceSuggestionsResponse(BaseModel):
    suggestions: list[AudienceSuggestion]
    summary: Optional[str] = None


@app.post("/agent/chat", response_model=ChatResponse)
async def agent_chat(body: ChatRequest) -> ChatResponse:
    """
    Simple AI agent endpoint powered by OpenAI.

    For demo purposes:
    - If the message mentions 'campaign', we fetch campaigns from Amazon Ads.
    - We pass the data and the original question to the LLM to generate a reply.
    """
    # Basic persistence: one default user and a new session per request.
    user_id = db.get_or_create_default_user_id()
    session_id = db.create_chat_session(user_id=user_id, title=body.message[:80])
    db.log_chat_message(session_id, "user", body.message)

    profile_id = body.profile_id or AMAZON_ADS_PROFILE_ID
    campaigns_data = None

    if "campaign" in body.message.lower():
        if not profile_id:
            raise HTTPException(
                status_code=400,
                detail="profile_id is required to work with campaigns.",
            )
        try:
            campaigns_data = await list_campaigns(profile_id)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Error calling Amazon Ads API: {exc}",
            )

    system_prompt = (
        "You are an AI agent for Amazon Ads. You help with media planning and campaign creation. "
        "When campaign data is provided, use it to answer questions in a concise, clear way. "
        "When a media plan is provided, help translate it into campaign structures (campaigns, ad groups, budgets, goals) and suggest next steps."
    )

    context_snippet = ""
    if campaigns_data is not None:
        context_snippet = f"Here is JSON campaign data:\n{str(campaigns_data)[:5000]}"
    if body.media_plan:
        context_snippet += f"\n\nAdvertiser's media plan (use this to create or suggest campaign structures):\n{body.media_plan[:8000]}"

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"{body.message}\n\n{context_snippet}".strip(),
        },
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2,
    )

    reply_text = completion.choices[0].message.content

    # Persist assistant reply and (optionally) a campaign snapshot.
    db.log_chat_message(session_id, "assistant", reply_text)

    if campaigns_data is not None and profile_id:
        try:
            raw_json = json.dumps(campaigns_data)
            db.save_campaign_snapshot(
                profile_id=profile_id,
                raw_json=raw_json,
                note=f"From message: {body.message[:80]}",
            )
        except TypeError:
            # If campaigns_data is not JSON-serializable, skip snapshot.
            pass

    return ChatResponse(reply=reply_text)


@app.post("/agent/audience-suggestions", response_model=AudienceSuggestionsResponse)
async def agent_audience_suggestions(body: AudienceSuggestionsRequest) -> AudienceSuggestionsResponse:
    """
    AI-driven campaign targeting: suggest high-value audiences from a campaign brief.
    Review and approve suggestions in the UI before using them in campaigns.
    """
    brief = f"Campaign goal: {body.goal}"
    if body.product_or_category:
        brief += f". Product/category: {body.product_or_category}"
    if body.budget_note:
        brief += f". Budget: {body.budget_note}"

    system_prompt = """You are an Amazon Ads expert. Given a short campaign brief, suggest 3 to 5 high-value audience segments that would work well for Amazon Advertising.
Return a JSON object with a key "suggestions" (array of objects). Each object must have:
- "name": short audience segment name (e.g. "WM - Women's Road Running Shoes")
- "description": one sentence describing who is in this audience
- "reason": one sentence on why this audience fits the brief
- "category": optional, e.g. "In-market", "Sporting Goods", "Fashion"
- "fee": optional, e.g. "$1.00"
- "audience_id": optional, a numeric or string ID for the segment (e.g. "467536256750790986")
Also include a key "summary" (string): one short paragraph summarizing the targeting strategy.
Return only valid JSON, no markdown or extra text."""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": brief},
        ],
        temperature=0.3,
    )

    raw = completion.choices[0].message.content.strip()
    # Strip markdown code block if present
    if "```" in raw:
        for start in ("```json", "```"):
            if raw.startswith(start):
                raw = raw[len(start):].strip()
        raw = raw.rsplit("```", 1)[0].strip()
    data = json.loads(raw)
    suggestions = []
    for s in data.get("suggestions", []):
        if isinstance(s, dict):
            suggestions.append(AudienceSuggestion(
                name=s.get("name", "Audience"),
                description=s.get("description", ""),
                reason=s.get("reason", ""),
                category=s.get("category"),
                fee=s.get("fee"),
                audience_id=s.get("audience_id"),
            ))
    summary = data.get("summary") if isinstance(data.get("summary"), str) else None
    return AudienceSuggestionsResponse(suggestions=suggestions, summary=summary)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
