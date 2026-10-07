"""Safety and evidence-integrity checks; all Meta responses are fake."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

from meta_discovery.foundation import EvidenceError, FILES, audit_foundation
from meta_discovery.reader import ACCOUNT_ID, MetaReadError, MetaReader, ReaderConfig
from scripts.meta.discover_connections import REPO_ROOT, main


def response(payload, status=200):
    result = Mock(status_code=status)
    result.json.return_value = payload
    return result


def debug(**changes):
    return {"data": {"is_valid": True, "app_id": "123", "type": "USER",
                     "scopes": ["ads_read", "public_profile"],
                     "expires_at": 2000, "data_access_expires_at": 2000, **changes}}


def account(**changes):
    return {"id": f"act_{ACCOUNT_ID}", "account_id": ACCOUNT_ID,
            "name": "Test account", "currency": "AUD", "timezone_name": "Australia/Sydney",
            "account_status": 1, **changes}


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.config = ReaderConfig("123", "fake-secret", "fake-token")
        self.session = Mock()
        self.reader = MetaReader(self.config, self.session)

    @patch("meta_discovery.reader.time.time", return_value=1000)
    def test_valid_token_checks_account_and_returns_only_safe_metadata(self, _):
        self.session.get.side_effect = [response(debug(user_id="private-user")), response(account())]
        result = self.reader.validate()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(self.session.get.call_count, 2)
        for call in self.session.get.call_args_list:
            self.assertFalse(call.kwargs["allow_redirects"])
            self.assertEqual(call.kwargs["timeout"], 30)
            self.assertNotIn("access_token", call.kwargs["params"])
        self.assertEqual(self.session.get.call_args.args[0], f"https://graph.facebook.com/v26.0/act_{ACCOUNT_ID}")
        for sensitive in ("fake-token", "fake-secret", "private-user", "appsecret_proof"):
            self.assertNotIn(sensitive, json.dumps(result))
        self.assertNotIn("fake-secret", repr(self.config))
        self.assertNotIn("fake-token", repr(self.config))

    @patch("meta_discovery.reader.time.time", return_value=1000)
    def test_bad_token_stops_before_account_read(self, _):
        for changes in ({"is_valid": False}, {"app_id": "456"}, {"type": "PAGE"},
                        {"scopes": []}, {"scopes": ["ads_read", "ads_management"]},
                        {"scopes": ["ads_read", "business_management"]},
                        {"expires_at": 999}, {"data_access_expires_at": 999},
                        {"expires_at": None}, {"scopes": None}):
            with self.subTest(changes=changes):
                self.session.reset_mock()
                self.session.get.return_value = response(debug(**changes))
                with self.assertRaises(MetaReadError):
                    self.reader.validate()
                self.session.get.assert_called_once()

    @patch("meta_discovery.reader.time.time", return_value=1000)
    def test_zero_expiry_is_recorded_without_inventing_an_expiry_date(self, _):
        self.session.get.side_effect = [response(debug(expires_at=0, data_access_expires_at=0)), response(account())]
        self.assertEqual(self.reader.validate()["token"]["expires_at"], 0)

    @patch("meta_discovery.reader.time.time", return_value=1000)
    def test_wrong_account_or_missing_context_fails(self, _):
        for changes in ({"account_id": "999"}, {"id": "act_999"}, {"currency": None}, {"timezone_name": None}):
            with self.subTest(changes=changes):
                self.session.get.side_effect = [response(debug()), response(account(**changes))]
                with self.assertRaises(MetaReadError):
                    self.reader.validate()

    def test_other_endpoints_are_blocked_before_network(self):
        for endpoint in (f"act_{ACCOUNT_ID}/ads", f"act_{ACCOUNT_ID}/insights", "999", "me/accounts"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(MetaReadError):
                    self.reader._get(endpoint, {}, "fake-token")
        self.session.get.assert_not_called()
        with self.assertRaises(MetaReadError):
            self.reader._get(f"act_{ACCOUNT_ID}", {"fields": "ads", "appsecret_proof": "fake"}, "fake-token")
        self.session.get.assert_not_called()

    def test_network_and_api_errors_do_not_echo_secrets(self):
        self.session.get.side_effect = requests.ConnectionError("URL?access_token=fake-token&secret=fake-secret")
        with self.assertRaises(MetaReadError) as caught:
            self.reader.validate()
        self.assertNotIn("fake-token", str(caught.exception))
        self.session.get.side_effect = None
        self.session.get.return_value = response({"error": {"code": 190, "message": "fake-token fake-secret"}}, 400)
        with self.assertRaises(MetaReadError) as caught:
            self.reader.validate()
        self.assertIn("code 190", str(caught.exception))
        self.assertNotIn("fake-secret", str(caught.exception))

    def test_redirect_and_invalid_json_are_failures(self):
        self.session.get.return_value = response({}, 302)
        with self.assertRaises(MetaReadError):
            self.reader.validate()
        self.session.get.return_value.json.side_effect = ValueError("fake-token")
        with self.assertRaises(MetaReadError) as caught:
            self.reader.validate()
        self.assertNotIn("fake-token", str(caught.exception))

    def test_file_configuration_does_not_use_environment_tokens(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.env"
            path.write_text(f"META_AD_ACCOUNT_ID=act_{ACCOUNT_ID}\nMETA_APP_ID=123\nMETA_APP_SECRET=fake-secret\nMETA_USER_ACCESS_TOKEN=file-token\n")
            with patch.dict("os.environ", {"META_USER_ACCESS_TOKEN": "old-terminal-token"}):
                self.assertEqual(ReaderConfig.from_file(path).user_token, "file-token")
            path.write_text("META_AD_ACCOUNT_ID=999\n")
            with self.assertRaisesRegex(MetaReadError, "must select Steele"):
                ReaderConfig.from_file(path)


class FoundationAndCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in FILES.values():
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / "evidence" / name, dest)

    def test_saved_evidence_reproduces_identifier_and_coverage_findings(self):
        result = audit_foundation(self.root)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["counts"]["matched_transactions"], 207)
        self.assertEqual(result["counts"]["matched_item_rows"], 326)
        self.assertEqual(result["counts"]["absent_online_store_orders"], 25)
        self.assertTrue(all(result["checks"].values()))

    def test_unmatched_item_is_reported_as_failed_not_silently_skipped(self):
        path = self.root / FILES["items"]
        original = path.read_text()
        path.write_text(original.replace("shopify_AU_7957185003659_44384278216843", "shopify_AU_999_999", 1))
        result = audit_foundation(self.root)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["counts"]["matched_item_rows"], 325)

    def test_malformed_item_and_missing_file_fail_clearly(self):
        path = self.root / FILES["items"]
        path.write_text(path.read_text().replace("shopify_AU_", "invalid_", 1))
        with self.assertRaisesRegex(EvidenceError, "Malformed dated row"):
            audit_foundation(self.root)
        path.unlink()
        with self.assertRaisesRegex(EvidenceError, "missing, unreadable"):
            audit_foundation(self.root)

    def test_truncated_event_export_does_not_pass(self):
        path = self.root / FILES["events"]
        text = path.read_text()
        path.write_text("\n".join(line for line in text.splitlines() if not line.startswith("2026-07-07   6617729564811")))
        self.assertFalse(audit_foundation(self.root)["checks"]["ga4_events_match_recorded_row_count"])

    def test_offline_never_loads_credentials_and_does_not_overwrite_reports(self):
        out = self.root / "runs"
        with patch("scripts.meta.discover_connections.ReaderConfig.from_file") as config, redirect_stdout(io.StringIO()):
            for _ in range(2):
                self.assertEqual(main(["--offline", "--evidence-root", str(self.root), "--output-dir", str(out)]), 0)
            config.assert_not_called()
        reports = list(out.glob("*/summary.json"))
        self.assertEqual(len(reports), 2)
        self.assertEqual(json.loads(reports[0].read_text())["meta"]["status"], "not_requested")

    def test_invalid_config_saves_failure_and_returns_nonzero_without_network(self):
        config = self.root / "wrong.env"
        config.write_text("META_AD_ACCOUNT_ID=999\n")
        out = self.root / "runs"
        with patch("meta_discovery.reader.requests.Session") as session, redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--config", str(config), "--evidence-root", str(self.root), "--output-dir", str(out)]), 1)
            session.assert_not_called()
        report = json.loads(next(out.glob("*/summary.json")).read_text())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["meta"]["status"], "failed")

    def test_later_stages_are_not_available(self):
        with patch("scripts.meta.discover_connections.audit_foundation") as audit, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main(["--stage", "creatives"])
            self.assertEqual(caught.exception.code, 2)
            audit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
