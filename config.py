from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_url: str = "your_db_url_here"
    db_echo: bool = False

settings = Settings()
