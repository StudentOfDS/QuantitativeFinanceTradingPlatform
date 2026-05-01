from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EQIP"
    app_env: str = "development"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    database_url: str = "sqlite:///eqip.db"
    sqlite_wal_mode: bool = True

    yfinance_default_period: str = "1y"
    yfinance_default_interval: str = "1d"

    enable_quantlib: bool = False
    enable_zipline: bool = False
    enable_skfolio: bool = False
    enable_arch: bool = False

    enable_live_trading: bool = False

    trading_mode: str = "paper"
    dry_run: bool = True
    broker_api_key: str = ""
    broker_api_secret: str = ""
    broker_endpoint: str = ""
    require_live_trading_confirmation: bool = True
    max_order_notional: float = 10000
    max_gross_exposure: float = 100000

    max_upload_mb: int = 25
    allow_trusted_pickle: bool = False

    global_random_seed: int = 42
    export_dir: str = "./exports"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
