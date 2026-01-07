"""Application configuration and settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_prefix="FINANCE_TRACKER_", env_file=".env")

    # Application
    app_name: str = "Finance Tracker"
    debug: bool = False

    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent
    data_dir: Path = base_dir / "data"
    imports_dir: Path = data_dir / "imports"
    static_dir: Path = base_dir / "static"
    templates_dir: Path = Path(__file__).parent / "templates"

    # Database
    database_url: str = "sqlite+aiosqlite:///data/finance.db"

    @property
    def database_path(self) -> Path:
        """Get the filesystem path to the SQLite database."""
        return self.data_dir / "finance.db"

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.imports_dir.mkdir(parents=True, exist_ok=True)
        self.static_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
