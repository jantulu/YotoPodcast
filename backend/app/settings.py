from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    podcasts_file: str = "/data/podcasts.json"
    yoto_access_token: str | None = None
    tmp_dir: str = "/data/tmp"

settings = Settings()
