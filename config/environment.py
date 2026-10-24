"""Load local environment variables without overriding the process environment."""
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_environment() -> None:
    """Load variables from the repository-root .env file, if present.

    Existing OS environment variables take precedence over values in .env.
    The .env file is optional, so deployments can inject secrets through their
    runtime or CI secret manager without creating a local file.
    """
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)
