# Copilot / AI Agent Instructions for YotoPodcast

Quick context
- Frontend: Vite + React + TypeScript in [frontend](frontend). Dev: `npm run dev` (port 5173).
- Backend: FastAPI Python app in [backend/app](backend/app). Main app objects exposed from `backend.app.main:app`.
- No DB: state is file-backed under `/data` (podcasts.json, yoto token/device files).

How to run locally
- Backend (from repo root):

```bash
python -m pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8001
```

- Frontend (from `frontend`):

```bash
cd frontend
npm install
npm run dev
```

Key files & responsibilities
- [backend/app/main.py](backend/app/main.py): core API routes for podcasts + Yoto auth endpoints.
- [backend/app/app.py](backend/app/app.py): upload / health endpoints and upload flow.
- [backend/app/yoto.py](backend/app/yoto.py): Yoto integration (device OAuth flow, token persistence, upload/transcode polling). Inspect `YOTO_TOKEN_PATH` and `YOTO_DEVICE_PATH` defaults (`/data/*.json`).
- [backend/app/rss.py](backend/app/rss.py) and [backend/app/podcasts.py](backend/app/podcasts.py): RSS fetch/parse and podcasts list loading.
- [frontend/src/api.ts](frontend/src/api.ts) and [frontend/src/App.tsx](frontend/src/App.tsx): how the UI calls the backend and what it expects from auth endpoints.

Important project-specific notes (do not assume defaults)
- API base mismatch: `frontend/src/api.ts` defaults to `http://localhost:8000` while `frontend/src/App.tsx` assumes `:8001` — set `VITE_API_BASE` to match whichever backend port you run.
- Auth token model: the backend stores a single shared token/device flow on disk (see [backend/app/yoto.py](backend/app/yoto.py)). The code intentionally treats auth as global/shared rather than per-user.
- Persistence: settings use `settings.podcasts_file` (default `/data/podcasts.json`) — persist file I/O must be writable in the runtime environment.
- Upload workflow: to test uploads, the API expects a server-local file path (e.g. `/data/tmp/foo.bin`) — the frontend does not upload raw files directly.

Debugging & common tasks
- Check auth status: GET `/api/yoto/auth/status` (main.py) — backend will attempt a best-effort refresh (see `oauth_refresh_if_possible`).
- Start device auth: POST `/api/yoto/auth/start` → show `verification_uri`/`user_code` to user. Poll via `/api/yoto/auth/status` or `/api/yoto/auth/poll`.
- Inspect token/device files: open the files at the paths in environment or defaults `/data/yoto_token.json` and `/data/yoto_device.json` when reproducing errors.
- To reproduce upload/transcode issues: place audio at a container-accessible path and POST `/api/yoto/upload` with `{ "file_path": "/data/tmp/yourfile.mp3" }`.

Conventions & code patterns to follow
- Async-first: backend uses `async` + `httpx.AsyncClient` (follow existing style and reuse `_client` helper in `yoto.py`).
- Small helpers: prefer small, testable helper functions (see `_read_json`, `_write_json`) rather than large monolithic handlers.
- Error handling: handlers log exceptions and raise `HTTPException` with user-friendly messages (see [backend/app/app.py](backend/app/app.py)). Mirror this pattern.

Build / CI notes
- No test framework present. Building the frontend uses Vite (`npm run build`). Backend dependencies are pinned in `backend/requirements.txt`.
- There is a `docker-compose.yml` at the repo root which can be used to run the full stack with correct volume mounts for `/data`.

When editing the integration with Yoto
- Read [backend/app/yoto.py](backend/app/yoto.py) carefully: token refresh, device flow, and polling are implemented with specific timing/timeout behavior.
- Preserve the file-backed persistence semantics (or consciously migrate to another store and update environment/config accordingly).

If something is unclear or you'd like more details (examples of requests, or adding a small test harness for the Yoto flow), tell me which section to expand.
