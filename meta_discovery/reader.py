"""Restricted Meta reads for access checks and a small July advertising sample."""

from dataclasses import dataclass, field
import hashlib
import hmac
import json
from pathlib import Path
import re
import time

from dotenv import dotenv_values
import requests

from meta_discovery.auth import CONFIG_FILE


ACCOUNT_ID = "2313037395632947"
ACCOUNT_FIELDS = "id,name,account_id,currency,timezone_name,account_status"
INSIGHT_FIELDS = "account_id,ad_id,ad_name,adset_id,adset_name,campaign_id,campaign_name,date_start,date_stop,impressions"
JULY_WINDOW = {"since": "2026-07-01", "until": "2026-07-07"}
OBJECT_FIELDS = {
    "ad": "id,account_id,name,campaign_id,adset_id,status,effective_status,creative{id},created_time,updated_time",
    "adset": "id,account_id,name,campaign_id,status,effective_status,created_time,updated_time",
    "campaign": "id,account_id,name,status,effective_status,created_time,updated_time",
}


class MetaReadError(ValueError):
    """A deliberately credential-free error suitable for the terminal/report."""


class MetaObjectUnavailable(MetaReadError):
    """A referenced object cannot be read; preserve this gap rather than omit it."""


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
        self._validated = False
        self._known_objects = {}
        self._insight_refs = {}
        self.request_count = 0

    def _get(self, endpoint: str, params: dict, bearer: str) -> dict:
        if endpoint == "debug_token":
            allowed_params, fields = {"input_token"}, None
        elif endpoint == f"act_{ACCOUNT_ID}":
            allowed_params, fields = {"fields", "appsecret_proof"}, ACCOUNT_FIELDS
        elif self._validated and endpoint == f"act_{ACCOUNT_ID}/insights":
            allowed_params = {"fields", "appsecret_proof", "level", "time_range", "limit"}
            if "after" in params:
                allowed_params.add("after")
            fields = INSIGHT_FIELDS
            if (params.get("level") != "ad" or params.get("time_range") != json.dumps(JULY_WINDOW)
                    or params.get("limit") != 100):
                raise MetaReadError("Insights parameters blocked: only the fixed July ad-level sample is allowed.")
        elif self._validated and endpoint in self._known_objects:
            allowed_params, fields = {"fields", "appsecret_proof"}, OBJECT_FIELDS[self._known_objects[endpoint]]
        else:
            raise MetaReadError("Endpoint blocked: only validated Steele access and discovered sample objects are allowed.")
        if set(params) != allowed_params or (fields is not None and params.get("fields") != fields):
            raise MetaReadError("Request parameters blocked: only approved access/sample fields are allowed.")
        try:
            self.request_count += 1
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
            error_type = MetaObjectUnavailable if endpoint in self._known_objects and code in (100, 803) else MetaReadError
            raise error_type(f"Meta rejected the read (HTTP {response.status_code}, code {safe_code}); details withheld.")
        return payload

    def scrub(self, value):
        """Remove known credentials even if they unexpectedly appear in a returned label."""
        if isinstance(value, str):
            for secret in (self.config.user_token, self.config.app_secret,
                           hmac.new(self.config.app_secret.encode(), self.config.user_token.encode(), hashlib.sha256).hexdigest()):
                value = value.replace(secret, "[REDACTED]")
            return value
        if isinstance(value, dict):
            return {key: self.scrub(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.scrub(item) for item in value]
        return value

    def _ads_get(self, endpoint, params):
        if not self._validated:
            raise MetaReadError("Validate Steele account access before sample reads.")
        proof = hmac.new(self.config.app_secret.encode(), self.config.user_token.encode(), hashlib.sha256).hexdigest()
        return self._get(endpoint, {**params, "appsecret_proof": proof}, self.config.user_token)

    def insight_pages(self):
        """Yield safe data pages; never follow Meta's supplied next-page URL."""
        params = {"fields": INSIGHT_FIELDS, "level": "ad", "time_range": json.dumps(JULY_WINDOW), "limit": 100}
        cursors = set()
        seen_ads = set()
        for _ in range(50):
            payload = self._ads_get(f"act_{ACCOUNT_ID}/insights", params)
            rows = payload.get("data")
            if not isinstance(rows, list):
                raise MetaReadError("Insights returned an invalid data page.")
            clean = []
            for row in rows:
                if not isinstance(row, dict) or str(row.get("account_id")) != ACCOUNT_ID:
                    raise MetaReadError("Insights returned an unexpected account or row structure.")
                for key in ("ad_id", "adset_id", "campaign_id"):
                    if not isinstance(row.get(key), str) or not re.fullmatch(r"[0-9]+", row[key]):
                        raise MetaReadError("Insights omitted a valid advertising identifier.")
                if row["ad_id"] in seen_ads:
                    raise MetaReadError("Insights repeated an ad; cannot treat this as a complete period-level report.")
                seen_ads.add(row["ad_id"])
                if row.get("date_start") != JULY_WINDOW["since"] or row.get("date_stop") != JULY_WINDOW["until"]:
                    raise MetaReadError("Insights returned dates outside the requested report window.")
                if not re.fullmatch(r"[0-9]+", str(row.get("impressions", ""))):
                    raise MetaReadError("Insights impressions are missing or malformed.")
                clean.append(self.scrub({key: row.get(key) for key in INSIGHT_FIELDS.split(",")}))
                self._insight_refs[row["ad_id"]] = (row["adset_id"], row["campaign_id"])
            yield clean
            paging = payload.get("paging", {})
            if not isinstance(paging, dict):
                raise MetaReadError("Insights pagination structure is invalid.")
            if not paging.get("next"):
                return
            markers = paging.get("cursors", {})
            after = markers.get("after") if isinstance(markers, dict) else None
            if not isinstance(after, str) or not after or after in cursors:
                raise MetaReadError("Insights next-page cursor is missing or repeated; collection is incomplete.")
            cursors.add(after)
            params = {**params, "after": after}
        raise MetaReadError("Insights exceeded the 50-page safety limit; collection is incomplete.")

    def register_sample(self, rows):
        if not self._validated or len(rows) > 15:
            raise MetaReadError("Sample must contain at most 15 ads after account validation.")
        self._known_objects = {}
        for row in rows:
            if str(row.get("account_id")) != ACCOUNT_ID:
                raise MetaReadError("Sample contains an unexpected account.")
            if self._insight_refs.get(row.get("ad_id")) != (row.get("adset_id"), row.get("campaign_id")):
                raise MetaReadError("Sample references were not discovered through this account's Insights read.")
            for kind, key in (("ad", "ad_id"), ("adset", "adset_id"), ("campaign", "campaign_id")):
                value = row.get(key)
                if not isinstance(value, str) or not re.fullmatch(r"[0-9]+", value):
                    raise MetaReadError("Sample contains an invalid advertising identifier.")
                self._known_objects[value] = kind

    def object(self, kind, object_id):
        if self._known_objects.get(object_id) != kind:
            raise MetaReadError("Object is not a registered reference from the selected Steele sample.")
        result = self._ads_get(object_id, {"fields": OBJECT_FIELDS[kind]})
        if str(result.get("id")) != object_id or str(result.get("account_id")) != ACCOUNT_ID:
            raise MetaReadError("Referenced object does not match its expected ID/account.")
        fields = [field for field in OBJECT_FIELDS[kind].split(",")]
        fields = ["creative" if field == "creative{id}" else field for field in fields]
        cleaned = {key: result.get(key) for key in fields}
        if kind == "ad":
            creative = result.get("creative")
            cleaned["creative"] = {"id": creative.get("id")} if isinstance(creative, dict) else None
        return self.scrub(cleaned)

    def validate(self) -> dict:
        self._validated = False
        self._known_objects = {}
        self._insight_refs = {}
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
        self._validated = True
        # Never save the raw token-debug response (which also contains user identifiers).
        return {"status": "passed", "api_version": cfg.version,
                "token": {"valid": True, "app_matches": True, "type": "USER",
                          "scopes": sorted(scopes), **expiry},
                "account": {key: account.get(key) for key in ACCOUNT_FIELDS.split(",")},
                "requests": 2, "advertising_objects_read": False}
