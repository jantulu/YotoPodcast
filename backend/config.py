from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    YOTO_CLIENT_ID: str
    YOTO_CLIENT_SECRET: str
    YOTO_REDIRECT_URI: str = "http://localhost:3000/callback"
    YOTO_API_BASE_URL: str = "https://api.yotoplay.com"
    YOTO_AUTH_URL: str = "https://api.yotoplay.com/oauth/authorize"
    YOTO_TOKEN_URL: str = "https://api.yotoplay.com/oauth/token"
    FRONTEND_URL: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()