"""GET-only, account-locked Meta advertising discovery (no Page access)."""

from dataclasses import dataclass, field
from datetime import date
import hashlib
import hmac
import json
import re
import time

from dotenv import dotenv_values
import requests

from meta_discovery.auth import CONFIG_FILE


ACCOUNT_ID = "2313037395632947"
APP_ID = "2262542241238863"
ACCOUNT_FIELDS = ("id", "name", "account_status", "currency", "timezone_name")
OBJECT_FIELDS = {
    "campaigns": ("id", "name", "status", "objective", "created_time", "updated_time"),
    "adsets": ("id", "name", "campaign_id", "status", "optimization_goal",
               "billing_event", "attribution_spec", "created_time", "updated_time"),
    "ads": ("id", "name", "campaign_id", "adset_id", "status", "creative",
            "created_time", "updated_time"),
    "adcreatives": ("id", "name", "title", "body", "object_type", "object_url",
                    "link_url", "url_tags", "template_url", "object_story_spec",
                    "asset_feed_spec", "effective_object_story_id"),
}
INSIGHT_FIELDS = (
    "account_id", "account_name", "account_currency", "campaign_id", "campaign_name",
    "adset_id", "adset_name", "ad_id", "ad_name", "date_start", "date_stop",
    "spend", "impressions", "reach", "clicks", "inline_link_clicks",
    "actions", "action_values", "website_purchase_roas",
)


class MetaReadError(RuntimeError):
    """Safe error: never include URLs, response text, tokens, or request objects."""

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ReaderConfig:
    token: str = field(repr=False)
    app_secret: str = field(repr=False)
    account_id: str = ACCOUNT_ID
    app_id: str = APP_ID
    version: str = "v26.0"

    def __post_init__(self):
        if self.account_id != ACCOUNT_ID or self.app_id != APP_ID:
            raise MetaReadError("Configuration must match the approved Steele account and app.")
        if not self.token or not self.app_secret:
            raise MetaReadError("A fresh user token and App Secret are required.")
        if self.version not in {"v25.0", "v26.0"}:
            raise MetaReadError("This reader supports v25.0 and v26.0; review before changing versions.")

    @classmethod
    def from_file(cls, path=CONFIG_FILE):
        # Deliberately use the ignored file, without silently taking shell overrides
        # or the legacy token used by older Page experiments.
        values = dotenv_values(path)
        names = ("META_USER_ACCESS_TOKEN", "META_APP_SECRET", "META_AD_ACCOUNT_ID", "META_APP_ID")
        missing = [name for name in names if not values.get(name)]
        if missing:
            raise MetaReadError("Missing settings in config/meta/.env: " + ", ".join(missing))
        return cls(values[names[0]], values[names[1]],
                   values[names[2]].removeprefix("act_"), values[names[3]],
                   values.get("META_GRAPH_API_VERSION") or "v26.0")


class MetaReader:
    def __init__(self, config, session=None, sleep=time.sleep):
        self.config = config
        self.session = session or requests.Session()
        self.sleep = sleep
        self.validated = False
        self.token_info = {}
        self.request_count = 0
        self._creatives = None
        self._ad_ids = set()
        self._ad_creative_ids = {}
        self.rate_limit_info = {}
        self.creative_limitations = []
        self.proof = hmac.new(config.app_secret.encode(), config.token.encode(), hashlib.sha256).hexdigest()
        self.account_path = "act_" + config.account_id

    def scrub(self, value):
        """Keep response data, but remove credentials and credential-bearing URLs."""
        secrets = (self.config.token, self.config.app_secret, self.proof)
        credential_keys = {"access_token", "input_token", "appsecret_proof", "client_secret"}
        if isinstance(value, dict):
            return {k: self.scrub(v) for k, v in value.items() if k.lower() not in credential_keys}
        if isinstance(value, list):
            return [self.scrub(v) for v in value]
        if isinstance(value, str):
            for secret in secrets:
                value = value.replace(secret, "[REDACTED]")
            return re.sub(r"(?i)((?:access_token|input_token|appsecret_proof|client_secret)=)[^&\s#]+",
                          r"\1[REDACTED]", value)
        return value

    def _request(self, method, path, params):
        # Fixed origin, fixed paths, fixed field inventory, no redirects, no POST.
        paths = {self.account_path: ACCOUNT_FIELDS}
        paths.update({self.account_path + "/" + edge: fields for edge, fields in OBJECT_FIELDS.items()
                      if edge != "adcreatives"})
        paths[self.account_path + "/insights"] = INSIGHT_FIELDS
        paths.update({creative_id: OBJECT_FIELDS["adcreatives"]
                      for creative_id in self._ad_creative_ids.values()})
        if method != "GET" or path not in {*paths, "debug_token"}:
            raise MetaReadError("Blocked request: only approved advertising GET reads are allowed.")
        if path == "debug_token":
            if set(params) != {"input_token"} or params["input_token"] != self.config.token:
                raise MetaReadError("Blocked token validation parameters.")
            auth = self.config.app_id + "|" + self.config.app_secret
        else:
            if not self.validated:
                raise MetaReadError("Validate the token before reading advertising data.")
            allowed = {"fields", "limit", "after"}
            if path.endswith("/insights"):
                allowed |= {"level", "time_range", "time_increment", "use_unified_attribution_setting", "action_report_time"}
            requested_fields = params.get("fields", "")
            fields = requested_fields.split(",")
            if set(params) - allowed or not fields or set(fields) - set(paths[path]):
                raise MetaReadError("Blocked request parameters or fields.")
            auth = self.config.token
        query = dict(params)
        if path != "debug_token":
            query["appsecret_proof"] = self.proof
        url = f"https://graph.facebook.com/{self.config.version}/{path}"
        for attempt in range(3):
            self.request_count += 1
            try:
                response = self.session.get(url, headers={"Authorization": "Bearer " + auth},
                                            params=query, timeout=30, allow_redirects=False)
                body = response.json()
            except requests.RequestException:
                raise MetaReadError("Meta connection failed or timed out; request details withheld.") from None
            except ValueError:
                raise MetaReadError("Meta returned a non-JSON response; details withheld.") from None
            if not isinstance(body, dict):
                raise MetaReadError("Unexpected Meta response shape.")
            # Persist only numeric usage estimates, not arbitrary response headers.
            for header in ("x-ad-account-usage", "x-business-use-case-usage"):
                try:
                    usage = json.loads(response.headers.get(header, "{}"))
                except (ValueError, AttributeError):
                    continue
                def estimates(value):
                    if isinstance(value, dict):
                        for key, item in value.items():
                            if key in {"acc_id_util_pct", "reset_time_duration", "estimated_time_to_regain_access", "call_count", "total_cputime", "total_time"} and isinstance(item, (int, float)):
                                self.rate_limit_info[key] = item
                            elif isinstance(item, (dict, list)):
                                estimates(item)
                    elif isinstance(value, list):
                        for item in value:
                            estimates(item)
                estimates(usage)
            error = body.get("error") or {}
            if not isinstance(error, dict):
                raise MetaReadError("Meta returned an unexpected error shape; details withheld.")
            code = error.get("code") if isinstance(error.get("code"), int) else None
            transient = code in {4, 17, 32, 613, 80000, 80004} or response.status_code == 429 or response.status_code >= 500
            estimated_wait = self.rate_limit_info.get("estimated_time_to_regain_access", 0) * 60
            if transient and attempt < 2 and estimated_wait <= 6:
                self.sleep(2 ** (attempt + 1))
                continue
            if response.status_code != 200 or error:
                reason = {190: "invalid or expired token", 200: "permission denied", 100: "invalid fields or parameters"}.get(code, "rate limit exceeded" if transient else "request rejected")
                wait_note = f" Estimated recovery: {estimated_wait / 60:g} minutes." if transient and estimated_wait else ""
                raise MetaReadError(f"Meta {reason} (HTTP {response.status_code}, code {code}); no permissions were broadened." + wait_note, code)
            return body
        raise MetaReadError("Meta retry limit reached.")

    def validate(self):
        self.validated = False
        data = self._request("GET", "debug_token", {"input_token": self.config.token}).get("data", {})
        if not isinstance(data, dict) or not isinstance(data.get("scopes"), list) or any(not isinstance(scope, str) for scope in data["scopes"]):
            raise MetaReadError("Meta returned malformed token-validation data.")
        scopes = set(data.get("scopes", []))
        if not data.get("is_valid") or data.get("app_id") != APP_ID or data.get("type") != "USER":
            raise MetaReadError("Token is invalid, not a user token, or belongs to another app.")
        if "ads_read" not in scopes or scopes - {"ads_read", "public_profile"}:
            raise MetaReadError("Use a fresh token with only ads_read and optional public_profile.")
        for key in ("expires_at", "data_access_expires_at"):
            if data.get(key) is not None and not isinstance(data[key], (int, float)):
                raise MetaReadError("Meta returned a malformed token expiry.")
            if data.get(key) and data[key] <= time.time():
                raise MetaReadError("Token or data-access authorisation has expired.")
        self.token_info = {"app_id": APP_ID, "type": "USER", "scopes": sorted(scopes),
                           "expires_at": data.get("expires_at"),
                           "data_access_expires_at": data.get("data_access_expires_at")}
        self.validated = True
        try:
            account = self._request("GET", self.account_path, {"fields": ",".join(ACCOUNT_FIELDS)})
            if account.get("id") != self.account_path or not account.get("currency") or not account.get("timezone_name"):
                raise MetaReadError("Account response does not confirm the target, currency, and time zone.")
        except MetaReadError:
            self.validated = False
            raise
        return self.scrub(account)

    def pages(self, edge, params):
        """Ignore next URLs entirely: reuse our endpoint and only its after cursor."""
        if edge not in {"campaigns", "adsets", "ads", "insights"}:
            raise MetaReadError("Unknown advertising read edge.")
        result = []
        cursors = set()
        query = {**params, "limit": 500}
        while True:
            response = self._request("GET", self.account_path + "/" + edge, query)
            rows = response.get("data")
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise MetaReadError("Meta returned an invalid data page.")
            # Save only data: paging.next can contain a token and is never exported.
            result.append({"data": self.scrub(rows)})
            paging = response.get("paging", {})
            if not paging.get("next"):
                return result
            cursor = paging.get("cursors", {}).get("after")
            if not isinstance(cursor, str) or not cursor or cursor in cursors:
                raise MetaReadError("Pagination has no usable new cursor; results are incomplete.")
            cursors.add(cursor)
            query["after"] = cursor

    def objects(self, edge):
        if edge not in OBJECT_FIELDS:
            raise MetaReadError("Unknown advertising object edge.")
        if edge == "adcreatives":
            if self._creatives is None:
                raise MetaReadError("Read reporting creatives before using their cached results.")
            return [{"data": self._creatives}]
        fields = ",".join(OBJECT_FIELDS[edge])
        pages = self.pages(edge, {"fields": fields})
        if edge == "ads":
            for page in pages:
                for row in page["data"]:
                    if row.get("id"):
                        if not re.fullmatch(r"[0-9]+", str(row["id"])):
                            raise MetaReadError("Meta returned a malformed advertising ID.")
                        self._ad_ids.add(row["id"])
                        creative = row.get("creative")
                        if isinstance(creative, dict) and creative.get("id"):
                            if not re.fullmatch(r"[0-9]+", str(creative["id"])):
                                raise MetaReadError("Meta returned a malformed creative ID.")
                            self._ad_creative_ids[row["id"]] = creative["id"]
        return pages

    def report_creatives(self, ad_ids):
        """Read unique creatives referenced by this account's reporting ads."""
        selected = sorted({self._ad_creative_ids[ad_id] for ad_id in set(ad_ids) & self._ad_ids
                           if ad_id in self._ad_creative_ids})
        creatives = {}
        self.creative_limitations = []
        for creative_id in selected:
            try:
                creative = self._request("GET", creative_id, {"fields": ",".join(OBJECT_FIELDS["adcreatives"])})
            except MetaReadError as error:
                if error.code not in {100, 200}:
                    raise
                limitation = {"creative_id": creative_id, "code": error.code,
                              "detail": "Detailed fields unavailable; permissions were not broadened."}
                self.creative_limitations.append(limitation)
                try:
                    creative = self._request("GET", creative_id, {"fields": "id,name"})
                    limitation["basic_fields_retrieved"] = True
                except MetaReadError as basic_error:
                    if basic_error.code not in {100, 200}:
                        raise
                    limitation["basic_fields_retrieved"] = False
                    continue
            if creative.get("id") != creative_id:
                raise MetaReadError("Creative response did not match its collected ID.")
            creatives[creative_id] = self.scrub(creative)
        self._creatives = list(creatives.values())
        return [{"data": self._creatives}]

    def insights(self, since, until):
        start, end = date.fromisoformat(since), date.fromisoformat(until)
        if start > end:
            raise MetaReadError("Report start date must not be after its end date.")
        return self.pages("insights", {
            "fields": ",".join(INSIGHT_FIELDS), "level": "ad", "time_increment": 1,
            "time_range": json.dumps({"since": since, "until": until}),
            "use_unified_attribution_setting": "true", "action_report_time": "impression",
        })
