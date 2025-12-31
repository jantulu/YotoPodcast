from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    YOTO_CLIENT_ID: str
    YOTO_CLIENT_SECRET: str  # Not used for device flow, but kept for compatibility
    YOTO_API_BASE_URL: str = "https://api.yotoplay.com"
    YOTO_AUTH_URL: str = "https://login.yotoplay.com/oauth/device/code"
    YOTO_TOKEN_URL: str = "https://login.yotoplay.com/oauth/token"
    FRONTEND_URL: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()