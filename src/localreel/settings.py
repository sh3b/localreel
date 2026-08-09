from pathlib import Path

from pydantic_settings import BaseSettings
from sqlalchemy import URL


class Settings(BaseSettings):
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str

    downloads_dir: Path = Path("data/downloads")
    worker_poll_interval_sec: float = 5

    @property
    def db_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )
