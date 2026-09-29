"""Unfinished local Meta authorization experiment for discovery only.

This saves personal User and Page tokens for exploratory scripts. It is not a
production authentication design, and obtaining these tokens did not complete
object-story access: all 15 saved object-story requests returned permission
errors. The Meta source investigation stopped at this early stage.
"""

import json
import os
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv, set_key


GRAPH_API_VERSION = "v25.0"
GRAPH_API_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
FACEBOOK_DIALOG_URL = f"https://www.facebook.com/{GRAPH_API_VERSION}/dialog/oauth"
REQUEST_TIMEOUT_SECONDS = 30
OAUTH_WAIT_SECONDS = 300
STEELE_PAGE_ID = "114421101975106"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config" / "meta" / ".env"
DEFAULT_REDIRECT_URI = "http://localhost:8765/callback"
REQUESTED_PERMISSIONS = [
    "ads_read",
    "pages_show_list",
    "pages_read_engagement",
]


def require_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} is missing from config/meta/.env")
    return value


def get_json(url: str, **params):
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    try:
        response_body = response.json()
    except ValueError:
        response_body = response.text

    if not response.ok:
        raise RuntimeError(
            f"Meta returned HTTP {response.status_code}: "
            f"{json.dumps(response_body, indent=2)}"
        )

    return response_body


def wait_for_authorization_code(redirect_uri: str, expected_state: str) -> str:
    redirect = urlparse(redirect_uri)
    if redirect.scheme != "http" or redirect.hostname not in {
        "localhost",
        "127.0.0.1",
    }:
        raise ValueError(
            "META_OAUTH_REDIRECT_URI must use http://localhost or "
            "http://127.0.0.1 for this local discovery script."
        )

    callback_result = {}

    class OAuthCallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            callback_url = urlparse(self.path)
            if callback_url.path != redirect.path:
                self.send_error(404)
                return

            query = parse_qs(callback_url.query)
            callback_result["code"] = query.get("code", [None])[0]
            callback_result["state"] = query.get("state", [None])[0]
            callback_result["error"] = query.get("error_description", [None])[0]

            if callback_result["code"]:
                message = "Meta authorization received. You can close this tab."
                status = 200
            else:
                message = "Meta authorization was not completed. Return to the terminal."
                status = 400

            response_body = message.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)

        def log_message(self, format, *args):
            return

    server = HTTPServer((redirect.hostname, redirect.port or 80), OAuthCallbackHandler)
    server.timeout = OAUTH_WAIT_SECONDS
    server.handle_request()
    server.server_close()

    if callback_result.get("error"):
        raise RuntimeError(callback_result["error"])
    if callback_result.get("state") != expected_state:
        raise RuntimeError("OAuth state did not match. The login result was rejected.")
    if not callback_result.get("code"):
        raise RuntimeError("No OAuth code was received within five minutes.")

    return callback_result["code"]


def main() -> None:
    load_dotenv(CONFIG_FILE)
    app_id = require_setting("META_APP_ID")
    app_secret = require_setting("META_APP_SECRET")
    redirect_uri = os.getenv("META_OAUTH_REDIRECT_URI", DEFAULT_REDIRECT_URI)
    state = secrets.token_urlsafe(32)

    authorization_params = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "scope": ",".join(REQUESTED_PERMISSIONS),
        "response_type": "code",
        "auth_type": "rerequest",
        "state": state,
    }
    authorization_url = (
        f"{FACEBOOK_DIALOG_URL}?{urlencode(authorization_params)}"
    )

    print("Opening Facebook login in your browser.")
    print("The local callback will wait for up to five minutes.")
    webbrowser.open(authorization_url)
    authorization_code = wait_for_authorization_code(redirect_uri, state)

    short_lived_result = get_json(
        f"{GRAPH_API_BASE_URL}/oauth/access_token",
        client_id=app_id,
        client_secret=app_secret,
        redirect_uri=redirect_uri,
        code=authorization_code,
    )
    short_lived_user_token = short_lived_result["access_token"]

    long_lived_result = get_json(
        f"{GRAPH_API_BASE_URL}/oauth/access_token",
        grant_type="fb_exchange_token",
        client_id=app_id,
        client_secret=app_secret,
        fb_exchange_token=short_lived_user_token,
    )
    long_lived_user_token = long_lived_result["access_token"]

    permission_result = get_json(
        f"{GRAPH_API_BASE_URL}/me/permissions",
        access_token=long_lived_user_token,
    )
    granted_permissions = {
        item["permission"]
        for item in permission_result.get("data", [])
        if item.get("status") == "granted"
    }
    missing_permissions = set(REQUESTED_PERMISSIONS) - granted_permissions
    if missing_permissions:
        raise RuntimeError(
            "Meta did not grant these permissions: "
            + ", ".join(sorted(missing_permissions))
        )

    page_result = get_json(
        f"{GRAPH_API_BASE_URL}/me/accounts",
        fields="id,name,access_token,tasks",
        access_token=long_lived_user_token,
    )
    steele_page = next(
        (
            page
            for page in page_result.get("data", [])
            if page.get("id") == STEELE_PAGE_ID
        ),
        None,
    )
    if not steele_page:
        available_page_ids = [
            page.get("id") for page in page_result.get("data", [])
        ]
        raise RuntimeError(
            f"Steele Page {STEELE_PAGE_ID} was not returned by /me/accounts. "
            f"Available Page IDs: {available_page_ids}"
        )

    page_access_token = steele_page.get("access_token")
    if not page_access_token:
        raise RuntimeError("Meta did not return a Page access token for Steele.")

    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    set_key(CONFIG_FILE, "META_USER_ACCESS_TOKEN", long_lived_user_token)
    set_key(CONFIG_FILE, "META_PAGE_ACCESS_TOKEN", page_access_token)
    set_key(CONFIG_FILE, "META_ACCESS_TOKEN", long_lived_user_token)

    expires_in = long_lived_result.get("expires_in")
    print("Meta authorization succeeded.")
    print(f"Granted permissions: {', '.join(sorted(granted_permissions))}")
    print(f"Steele Page tasks: {', '.join(steele_page.get('tasks', []))}")
    if expires_in:
        print(f"User token lifetime reported by Meta: {expires_in} seconds")
    print("Saved separate user and Page tokens to config/meta/.env.")
    print("No token or App Secret was printed.")


if __name__ == "__main__":
    main()
