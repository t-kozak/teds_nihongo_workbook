"""Common utility functions for the project."""

import os
from pathlib import Path


def load_env_variable(key: str, env_path: Path | None = None) -> str:
    """Load an environment variable from .env file or environment.

    First checks the system environment variables, then falls back to reading
    from a .env file if the variable is not found in the environment.

    Args:
        key: The environment variable name to load
        env_path: Path to the .env file. If None, uses project root .env file.

    Returns:
        The value of the environment variable

    Raises:
        FileNotFoundError: If .env file is not found (when not in environment)
        ValueError: If the key is not found in either environment or .env file
    """
    # First check if it's in the system environment
    env_value = os.environ.get(key)
    if env_value is not None:
        return env_value

    # Fall back to loading from .env file
    if env_path is None:
        env_path = Path(__file__).parent.parent / ".env"

    if not env_path.exists():
        raise FileNotFoundError(
            f".env file not found at {env_path} and {key} not in environment"
        )

    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if "=" in line:
                    var_key, value = line.split("=", 1)
                    if var_key.strip() == key:
                        return value.strip()

    raise ValueError(f"{key} not found in .env file or environment")


def load_google_api_key(env_path: Path | None = None) -> str:
    """Load Google AI Studio API key from environment or .env file.

    Args:
        env_path: Path to the .env file. If None, uses project root .env file.

    Returns:
        The Google AI Studio API key

    Raises:
        FileNotFoundError: If .env file is not found (when not in environment)
        ValueError: If GOOGLE_AI_STUDIO_KEY is not found
    """
    return load_env_variable("GOOGLE_AI_STUDIO_KEY", env_path)
