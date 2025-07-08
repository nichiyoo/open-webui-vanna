from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    debug: bool = True
    port: int = 4321

    app_title: str = "Vanna SQL Assistant"
    app_version: str = "1.0.0"

    model_name: str
    sqlite_path: Optional[str]
    chroma_folder: Optional[str]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
