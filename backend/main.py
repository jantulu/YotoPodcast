from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, upload, playlists
from config import settings

app = FastAPI(title="YotoPodcast API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(playlists.router, prefix="/api/playlists", tags=["Playlists"])

@app.get("/")
async def root():
    return {"message": "YotoPodcast API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}