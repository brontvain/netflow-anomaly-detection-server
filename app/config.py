from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application configuration settings"""

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost/netflow"

    # Netflow Collector
    NETFLOW_HOST: str = "0.0.0.0"
    NETFLOW_PORT: int = 2055
    NETFLOW_BATCH_SIZE: int = 1000
    NETFLOW_BATCH_TIMEOUT: float = 5.0  # seconds

    # API
    API_MAX_QUERY_LIMIT: int = 1000
    API_DEFAULT_LIMIT: int = 100
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"

    # ML Model
    MODEL_CONTAMINATION: float = 0.1
    MODEL_N_ESTIMATORS: int = 100
    MODEL_TRAINING_HOURS: int = 24
    MODEL_MIN_TRAINING_SAMPLES: int = 100
    MODEL_PATH: str = "models/anomaly_detector.pkl"
    SCALER_PATH: str = "models/scaler.pkl"

    # Data Retention
    DATA_RETENTION_DAYS: int = 5

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text

    # Metrics
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
