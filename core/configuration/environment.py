"""Load optional root .env values without overriding process environment."""
from pathlib import Path
from dotenv import load_dotenv


def load_environment() -> None:
    """Load the repository-root .env file; OS environment variables take precedence."""
    repository_root = Path(__file__).resolve().parents[2]
    load_dotenv(repository_root / ".env", override=False)
