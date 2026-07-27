import os
from pathlib import Path

from dotenv import load_dotenv


CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "meta" / ".env"


def get_access_token() -> str:
    """Return the Meta access token configured in the environment."""
    load_dotenv(CONFIG_FILE)
    access_token = os.getenv("META_ACCESS_TOKEN")

    if not access_token:
        raise ValueError(
            "META_ACCESS_TOKEN is missing. Set it to your Meta access token "
            "before running a Meta discovery script."
        )

    return access_token
