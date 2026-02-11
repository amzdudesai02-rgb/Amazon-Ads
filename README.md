## Amazon Ads AI Agent

This project contains a minimal end-to-end example of an AI agent for Amazon Ads with:

- **Backend**: Python + FastAPI, Login with Amazon (LWA) OAuth2, OpenAI LLM, and a sample Amazon Ads API wrapper.
- **Frontend**: Node.js + Express serving a simple web UI that talks to the backend.

### Backend (Python / FastAPI)

Files are under `backend/`.

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies:

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in:

   - `LWA_CLIENT_ID`, `LWA_CLIENT_SECRET`, `LWA_REDIRECT_URI`
   - `OPENAI_API_KEY`
   - `AMAZON_ADS_PROFILE_ID` (optional, can also be sent from frontend)

4. Run the backend:

   ```bash
   uvicorn main:app --reload --port 8000
   ```

   Health check: open `http://localhost:8000/health`.

### Frontend (Node.js + Express)

Files are under `frontend/`.

1. Install dependencies:

   ```bash
   cd frontend
   npm install
   ```

2. Start the frontend:

   ```bash
   npm start
   ```

   This serves the UI at `http://localhost:3000`.

3. Click **“Connect Amazon Ads”** in the header to initiate the Login with Amazon flow via the backend, then type prompts and send them. When your prompt includes the word “campaign”, the backend will call the sample Amazon Ads `v2/campaigns` endpoint and pass that data into the OpenAI model to generate a response.

