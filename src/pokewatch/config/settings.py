"""
Configuration management for PokeWatch.

Loads settings from:
1. config/settings.yaml (project configuration)
2. Environment variables (via .env file)

Usage:
    from pokewatch.config.settings import get_settings

    settings = get_settings()
    api_key = settings.pokemon_price_api_key
    base_url = settings.api.base_url
"""

import os
from pathlib import Path
from typing import Optional
from functools import lru_cache

import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv


class APIConfig(BaseModel):
    """API configuration."""

    base_url: str
    timeout_seconds: int = 10
    language: str = "japanese"


class DataConfig(BaseModel):
    """Data paths configuration."""

    raw_dir: str
    processed_dir: str


class ModelConfig(BaseModel):
    """Model and decision rules configuration."""

    default_buy_threshold_pct: float = Field(
        default=0.10,
        description="Buy threshold: market price is X% below fair value (e.g., 0.10 = -10%)",
    )
    default_sell_threshold_pct: float = Field(
        default=0.15,
        description="Sell threshold: market price is X% above fair value (e.g., 0.15 = +15%)",
    )


class Settings(BaseModel):
    """Global application settings."""

    # API configuration
    api: APIConfig

    # Data configuration
    data: DataConfig

    # Model configuration
    model: ModelConfig

    # Environment variables
    pokemon_price_api_key: str = Field(..., description="API key for Pokemon Price Tracker API")
    env: str = Field(default="dev", description="Environment: dev, test, or prod")

    # Computed paths (relative to project root)
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent.parent)
    config_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent.parent / "config"
    )

    class Config:
        arbitrary_types_allowed = True


def load_yaml_config(config_path: Optional[Path] = None) -> dict:
    """
    Load configuration from settings.yaml.

    Args:
        config_path: Path to settings.yaml. If None, uses default location.

    Returns:
        Dictionary with configuration data.

    Raises:
        FileNotFoundError: If settings.yaml doesn't exist.
    """
    if config_path is None:
        # Default path: config/settings.yaml (relative to project root)
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / "config" / "settings.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Please ensure config/settings.yaml exists in the project root."
        )

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_env_variables() -> None:
    """
    Load environment variables from .env file.

    Looks for .env in the project root directory.
    """
    project_root = Path(__file__).parent.parent.parent.parent
    env_path = project_root / ".env"

    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try to load from current directory as fallback
        load_dotenv()


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings (cached singleton).

    Loads configuration from:
    1. config/settings.yaml
    2. Environment variables (.env file)

    Returns:
        Settings object with all configuration.

    Raises:
        FileNotFoundError: If settings.yaml doesn't exist.
        ValidationError: If required environment variables are missing.

    Example:
        >>> settings = get_settings()
        >>> print(settings.api.base_url)
        https://www.pokemonpricetracker.com/api/v2
        >>> print(settings.pokemon_price_api_key)
        pokeprice_pro_...
    """
    # Load environment variables first
    load_env_variables()

    # Load YAML configuration
    yaml_config = load_yaml_config()

    # Get environment variables
    api_key = os.getenv("POKEMON_PRICE_API_KEY")
    if not api_key:
        raise ValueError(
            "POKEMON_PRICE_API_KEY environment variable is required.\n"
            "Please set it in your .env file or environment."
        )

    env = os.getenv("ENV", "dev")

    # Combine YAML and environment variables
    settings_dict = {
        "api": APIConfig(**yaml_config["api"]),
        "data": DataConfig(**yaml_config["data"]),
        "model": ModelConfig(**yaml_config["model"]),
        "pokemon_price_api_key": api_key,
        "env": env,
    }

    return Settings(**settings_dict)  # type: ignore[arg-type]


def get_data_path(subdir: str = "") -> Path:
    """
    Get absolute path to data directory.

    Args:
        subdir: Subdirectory within data/ (e.g., "raw", "processed")

    Returns:
        Absolute path to data directory.

    Example:
        >>> raw_path = get_data_path("raw")
        >>> print(raw_path)
        /path/to/pokewatch/data/raw
    """
    settings = get_settings()
    data_path = settings.project_root / "data"

    if subdir:
        data_path = data_path / subdir

    # Create directory if it doesn't exist
    data_path.mkdir(parents=True, exist_ok=True)

    return data_path


def get_models_path(subdir: str = "") -> Path:
    """
    Get absolute path to models directory.

    Args:
        subdir: Subdirectory within models/ (e.g., "baseline", "trained")

    Returns:
        Absolute path to models directory.

    Example:
        >>> baseline_path = get_models_path("baseline")
        >>> print(baseline_path)
        /path/to/pokewatch/models/baseline
    """
    settings = get_settings()
    models_path = settings.project_root / "models"

    if subdir:
        models_path = models_path / subdir

    # Create directory if it doesn't exist
    models_path.mkdir(parents=True, exist_ok=True)

    return models_path
