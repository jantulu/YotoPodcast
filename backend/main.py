from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, upload, playlists, rss
from config import settings

app = FastAPI(title="YotoPodcast API")

# Startup check
@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print("YotoPodcast API Starting")
    print(f"Client ID configured: {settings.YOTO_CLIENT_ID[:10]}..." if settings.YOTO_CLIENT_ID else "Client ID: NOT SET!")
    print(f"Frontend URL: {settings.FRONTEND_URL}")
    print("=" * 50)
    
    if not settings.YOTO_CLIENT_ID:
        print("WARNING: YOTO_CLIENT_ID is not set in environment!")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://office.home.arpa:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(playlists.router, prefix="/api/playlists", tags=["Playlists"])
app.include_router(rss.router, prefix="/api/rss", tags=["RSS Feeds"])

@app.get("/")
async def root():
    return {"message": "YotoPodcast API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}