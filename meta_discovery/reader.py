"""Step 1 only: validate an ads-only token and read the approved account."""

from dataclasses import dataclass, field
import hashlib
import hmac
from pathlib import Path
import re
import time

from dotenv import dotenv_values
import requests

from meta_discovery.auth import CONFIG_FILE


ACCOUNT_ID = "2313037395632947"
ACCOUNT_FIELDS = "id,name,account_id,currency,timezone_name,account_status"


class MetaReadError(ValueError):
    """A deliberately credential-free error suitable for the terminal/report."""


@dataclass(frozen=True)
class ReaderConfig:
    app_id: str
    app_secret: str = field(repr=False)
    user_token: str = field(repr=False)
    version: str = "v26.0"

    @classmethod
    def from_file(cls, path: Path = CONFIG_FILE):
        # Explicit file values prevent an old terminal token silently taking priority.
        try:
            values = dotenv_values(path, interpolate=False)
        except OSError:
            raise MetaReadError("Cannot read the selected Meta configuration file.") from None
        account = (values.get("META_AD_ACCOUNT_ID") or "").removeprefix("act_")
        if account != ACCOUNT_ID:
            raise MetaReadError("META_AD_ACCOUNT_ID must select Steele account 2313037395632947.")
        required = ("META_APP_ID", "META_APP_SECRET", "META_USER_ACCESS_TOKEN")
        if any(not values.get(key) for key in required):
            raise MetaReadError("Configuration requires META_APP_ID, META_APP_SECRET and META_USER_ACCESS_TOKEN.")
        version = values.get("META_GRAPH_API_VERSION") or "v26.0"
        if not re.fullmatch(r"v\d+\.\d+", version) or not values["META_APP_ID"].isdigit():
            raise MetaReadError("Invalid Meta app ID or Graph API version format.")
        return cls(values["META_APP_ID"], values["META_APP_SECRET"],
                   values["META_USER_ACCESS_TOKEN"], version)


class MetaReader:
    def __init__(self, config: ReaderConfig, session=None):
        self.config = config
        self.session = session if session is not None else requests.Session()

    def _get(self, endpoint: str, params: dict, bearer: str) -> dict:
        if endpoint not in {"debug_token", f"act_{ACCOUNT_ID}"}:
            raise MetaReadError("Endpoint blocked: Step 1 allows token and Steele account checks only.")
        allowed_params = {"input_token"} if endpoint == "debug_token" else {"fields", "appsecret_proof"}
        if set(params) != allowed_params or (endpoint != "debug_token" and params.get("fields") != ACCOUNT_FIELDS):
            raise MetaReadError("Request parameters blocked: only the Step 1 access fields are allowed.")
        try:
            response = self.session.get(
                f"https://graph.facebook.com/{self.config.version}/{endpoint}",
                params=params, headers={"Authorization": f"Bearer {bearer}"},
                timeout=30, allow_redirects=False,
            )
        except requests.RequestException:
            # Exceptions can include credential-bearing request URLs; never echo them.
            raise MetaReadError("Meta request failed at the network layer; request details withheld.") from None
        try:
            payload = response.json()
        except ValueError:
            raise MetaReadError("Meta returned an unreadable response; response details withheld.") from None
        if not isinstance(payload, dict):
            raise MetaReadError("Meta returned an unexpected response structure.")
        if response.status_code != 200 or "error" in payload:
            code = payload.get("error", {}).get("code") if isinstance(payload.get("error"), dict) else None
            safe_code = str(code) if isinstance(code, int) else "unavailable"
            raise MetaReadError(f"Meta rejected the read (HTTP {response.status_code}, code {safe_code}); details withheld.")
        return payload

    def validate(self) -> dict:
        cfg = self.config
        debug = self._get("debug_token", {"input_token": cfg.user_token},
                          f"{cfg.app_id}|{cfg.app_secret}").get("data")
        if not isinstance(debug, dict) or debug.get("is_valid") is not True:
            raise MetaReadError("Meta reports an invalid token.")
        if str(debug.get("app_id")) != cfg.app_id or debug.get("type") != "USER":
            raise MetaReadError("Token does not belong to the configured app or is not a User token.")
        scopes = debug.get("scopes")
        if not isinstance(scopes, list) or any(not isinstance(s, str) for s in scopes):
            raise MetaReadError("Token permissions are unavailable.")
        if "ads_read" not in scopes or set(scopes) - {"ads_read", "public_profile"}:
            raise MetaReadError("Use an ads-only User token with ads_read and optional public_profile.")
        expiry = {}
        for key in ("expires_at", "data_access_expires_at"):
            value = debug.get(key)
            if type(value) is not int or value < 0:
                raise MetaReadError("Token expiry information is unavailable or malformed.")
            if value and value <= time.time():
                raise MetaReadError("Token or its data access has expired.")
            expiry[key] = value  # Zero means Meta supplied no scheduled expiry.
        proof = hmac.new(cfg.app_secret.encode(), cfg.user_token.encode(), hashlib.sha256).hexdigest()
        account = self._get(f"act_{ACCOUNT_ID}",
                            {"fields": ACCOUNT_FIELDS, "appsecret_proof": proof}, cfg.user_token)
        if account.get("id") != f"act_{ACCOUNT_ID}" or str(account.get("account_id")) != ACCOUNT_ID:
            raise MetaReadError("Returned account does not match the approved Steele account.")
        if any(not account.get(key) for key in ("currency", "timezone_name")):
            raise MetaReadError("Account currency or time zone is unavailable.")
        # Never save the raw token-debug response (which also contains user identifiers).
        return {"status": "passed", "api_version": cfg.version,
                "token": {"valid": True, "app_matches": True, "type": "USER",
                          "scopes": sorted(scopes), **expiry},
                "account": {key: account.get(key) for key in ACCOUNT_FIELDS.split(",")},
                "requests": 2, "advertising_objects_read": False}
