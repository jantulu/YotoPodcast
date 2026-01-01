# YotoPodcast

Web UI and API to upload podcast episodes to Yoto playlists.

## Highlights

- OAuth device flow for Yoto
- Upload episodes to new or existing playlists
- Small file-backed persistence suitable for local/dev use
- Docker Compose for easy start-up

## Quick Start (recommended: Docker)

1. Clone the repo:

```bash
git clone https://github.com/Jantulu/YotoPodcast.git
cd YotoPodcast
```

2. Copy and edit environment variables:

```bash
cp .env.example .env
# Edit .env and add YOTO_CLIENT_ID and other values
```

3. Start with Docker Compose:

```bash
docker-compose up -d
```

When using Docker Compose the services are exposed as:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000 (API docs: http://localhost:8000/docs)

## Running Locally (no Docker)

Backend (FastAPI / Uvicorn):

```bash
cd backend
python -m venv venv
# On Windows: venv\Scripts\activate
source venv/bin/activate
pip install -r requirements.txt
# Run (default port 8000)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend (Vite + React):

```bash
cd frontend
npm install
# Vite dev server (defaults to 5173)
npm run dev
```

Notes for local frontend/backend pairing:
- If the frontend dev server runs on a different port, set the frontend URL and API host accordingly. The backend's default `FRONTEND_URL` is `http://localhost:3000`; update `.env` if needed.
- The frontend may require `VITE_API_URL` or similar environment variables when running locally — set it to your backend (e.g., `http://localhost:8000`).

## Environment vars

Copy `.env.example` to `.env` and set at minimum:

- `YOTO_CLIENT_ID` — your Yoto developer client id
- `FRONTEND_URL` — URL where the frontend is served (used for CORS)

Other values (token URLs, API base) default to production endpoints and normally don't need changes.

## API (summary)

- `GET /api/auth/status` — check auth status
- `POST /api/yoto/auth/start` — start device auth flow
- `GET /api/playlists` — list playlists
- `POST /api/rss/feeds/upload-episode` — upload by `audio_url` to Yoto

For full routes, open the backend API docs at `/docs` when the backend is running.


