"""Token loading for unfinished, discovery-only Meta scripts.

Loading a token does not verify its permissions or prove object-story access.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "meta" / ".env"


def get_user_access_token() -> str:
    """Return the user token used for Meta Ads discovery requests."""
    load_dotenv(CONFIG_FILE)
    access_token = os.getenv("META_USER_ACCESS_TOKEN") or os.getenv(
        "META_ACCESS_TOKEN"
    )

    if not access_token:
        raise ValueError(
            "META_USER_ACCESS_TOKEN is missing. Run the Meta OAuth script or "
            "set META_ACCESS_TOKEN for backward compatibility."
        )

    return access_token


def get_page_access_token() -> str:
    """Return the Page token used for Facebook Page object requests."""
    load_dotenv(CONFIG_FILE)
    access_token = os.getenv("META_PAGE_ACCESS_TOKEN") or os.getenv(
        "META_ACCESS_TOKEN"
    )

    if not access_token:
        raise ValueError(
            "META_PAGE_ACCESS_TOKEN is missing. Run the Meta OAuth script or "
            "set META_ACCESS_TOKEN for backward compatibility."
        )

    return access_token


def get_access_token() -> str:
    """Return the user token for existing Meta Ads discovery scripts."""
    return get_user_access_token()
