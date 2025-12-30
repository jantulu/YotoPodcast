from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    YOTO_CLIENT_ID: str
    YOTO_SCOPE: str = ""
    YOTO_API_BASE: str = "https://api.yotoplay.com"
    YOTO_LOGIN_BASE: str = "https://login.yotoplay.com"

    YOTO_TOKEN_PATH: str = "/data/yoto_token.json"
    YOTO_DEVICE_PATH: str = "/data/yoto_device.json"


settings = Settings()
