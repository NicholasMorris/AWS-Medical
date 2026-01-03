import os
from typing import Dict

# Centralized model mapping for the project. Update ARNs or short ids here.
MODEL_MAP: Dict[str, str] = {
    "claude": "anthropic.claude-3-sonnet-20240229-v1:0",
    # Use full Bedrock ARN for Nova invocation
    "nova": "arn:aws:bedrock:ap-southeast-2:721285384514:inference-profile/apac.amazon.nova-lite-v1:0",
}

# Default model name; can be overridden with the DEFAULT_MODEL env var
DEFAULT_MODEL = "nova"


def get_default_model() -> str:
    """Return the configured default model name.

    Resolution order:
    1. `default_model` key in config file (see src.common.config)
    2. `DEFAULT_MODEL` environment variable
    3. package DEFAULT_MODEL constant
    """
    # Lazy import to avoid config import cycles
    try:
        from src.common.config import get_config_value

        cfg_val = get_config_value("default_model")
        if cfg_val:
            return cfg_val
    except Exception:
        pass

    return os.getenv("DEFAULT_MODEL", DEFAULT_MODEL)
