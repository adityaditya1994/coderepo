"""
Configuration loader — reads config.yaml and .env, merges them
into a single config dict available to every module.
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv


_CONFIG_DIR = Path(__file__).parent
_CONFIG_FILE = _CONFIG_DIR / "config.yaml"
_ENV_FILE = _CONFIG_DIR / ".env"


def load_config() -> dict:
    """Load YAML config and inject environment variables."""
    # Load .env so os.environ picks up secrets
    load_dotenv(_ENV_FILE)

    with open(_CONFIG_FILE, "r") as f:
        config = yaml.safe_load(f)

    # Inject secrets into config dict for convenience
    config["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
    config["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")
    config["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")
    config["PINECONE_API_KEY"] = os.getenv("PINECONE_API_KEY", "")
    config["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID", "")
    config["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    config["AWS_DEFAULT_REGION"] = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    config["DATAHUB_GMS_URL"] = os.getenv("DATAHUB_GMS_URL", "")
    config["DATAHUB_TOKEN"] = os.getenv("DATAHUB_TOKEN", "")

    return config
