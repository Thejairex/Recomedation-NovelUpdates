from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Base de datos
    database_url: str

    # NovelUpdates
    nu_session_cookie: str
    nu_base_url: str = "https://www.novelupdates.com"
    nu_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # Scraping
    scrape_delay_seconds: float = 1.0
    scrape_max_retries: int = 3
    candidate_pages: int = 10

    # Recomendador
    top_n_recommendations: int = 20
    cache_ttl_hours: int = 24

    # Pesos por lista
    weight_best_the_best: int = 3
    weight_default: int = 1

    # Listas a ignorar (separadas por coma en .env)
    ignored_lists: list[str] = ["Plan to Read", "Dropped"]

    # Logging
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings(database_url="sqlite+aiosqlite:///novels.db", nu_session_cookie="")
