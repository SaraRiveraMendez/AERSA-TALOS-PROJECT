"""
config.py
Configuración centralizada. Lee variables de .env automáticamente.
Para cambiar de MySQL a Oracle, solo cambia DATABASE_URL en .env.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "dev-secret-key"

    # Base de datos
    database_url: str = "mysql+aiomysql://root:root@localhost:3306/talos_db"

    # Scheduler
    scheduler_day_of_week: str = "sun"
    scheduler_hour: int = 23
    scheduler_minute: int = 0
    scheduler_timezone: str = "America/Mexico_City"

    # Almacenamiento
    storage_backend: str = "local"
    storage_local_path: str = "./storage/reports"

    # OCI (opcionales — solo al migrar)
    oci_namespace: str = ""
    oci_bucket: str = ""
    oci_region: str = ""

    # Notificaciones
    notifications_enabled: bool = True
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "reportes@talos.com"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_oracle(self) -> bool:
        return "oracle" in self.database_url.lower()


@lru_cache()
def get_settings() -> Settings:
    """Singleton — la configuración se carga una sola vez."""
    return Settings()
