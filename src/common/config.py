"""Configuration utilities for AWS-Medical.

This module loads a JSON configuration file if present. The default
search order for the config file is:

- Path from `AWS_MEDICAL_CONFIG` env var
- ./config/models.json
- ./config.json

Configuration values are cached for the process lifetime.
"""
import json
import os
from functools import lru_cache
from typing import Any, Dict, Optional


@lru_cache
def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load and return configuration dictionary from JSON file.

    Returns empty dict if no configuration file is found or parsing fails.
    """
    search_paths = []
    if path:
        search_paths.append(path)

    env_path = os.getenv("AWS_MEDICAL_CONFIG")
    if env_path:
        search_paths.append(env_path)

    # Common locations
    search_paths.extend(["config/models.json", "config.json"])

    for p in search_paths:
        try:
            with open(p, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            continue
        except Exception:
            # If parsing fails, ignore and continue
            continue

    return {}


def get_config_value(key: str, default: Optional[Any] = None) -> Any:
    cfg = load_config()
    return cfg.get(key, default)
