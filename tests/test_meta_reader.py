"""Offline tests of advertising restrictions, credentials, paging, and evidence."""

from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import requests

from meta_discovery.reader import ACCOUNT_ID, APP_ID, MetaReader, MetaReadError, ReaderConfig
from meta_discovery.reporting import action_rows, export_report, totals, windows


def response(body, status=200):
    return SimpleNamespace(status_code=status, json=lambda: body)


def token_data(**changes):
    data = {"is_valid": True, "app_id": APP_ID, "type": "USER",
            "scopes": ["ads_read", "public_profile"], "expires_at": 0,
            "data_access_expires_at": 0}
    return {"data": {**data, **changes}}


ACCOUNT = {"id": "act_" + ACCOUNT_ID, "name": "Steele", "currency": "AUD", "timezone_name": "Australia/Sydney"}


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.config = ReaderConfig("fresh-user-token-secret", "private-app-secret")
        self.session = Mock()
        self.reader = MetaReader(self.config, self.session, sleep=Mock())

    def validate(self):
        self.session.get.side_effect = [response(token_data()), response(ACCOUNT)]
        self.assertEqual(self.reader.validate(), ACCOUNT)
        self.session.get.reset_mock(side_effect=True)

    def test_configuration_locks_app_and_account_and_hides_secrets(self):
        with self.assertRaises(MetaReadError):
            ReaderConfig("token", "secret", account_id="999")
        with self.assertRaises(MetaReadError):
            ReaderConfig("token", "secret", app_id="999")
        with self.assertRaises(MetaReadError):
            ReaderConfig("token", "secret", version="v25.0/../../events")
        self.assertNotIn(self.config.token, repr(self.config))
        self.assertNotIn(self.config.app_secret, repr(self.config))

    def test_no_legacy_token_fallback(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / ".env"
            path.write_text(f"META_ACCESS_TOKEN=legacy\nMETA_APP_SECRET=secret\nMETA_APP_ID={APP_ID}\nMETA_AD_ACCOUNT_ID={ACCOUNT_ID}\n")
            with self.assertRaisesRegex(MetaReadError, "META_USER_ACCESS_TOKEN"):
                ReaderConfig.from_file(path)

    def test_unvalidated_account_reads_are_blocked(self):
        with self.assertRaises(MetaReadError):
            self.reader.objects("ads")
        self.session.get.assert_not_called()

    def test_expired_wrong_app_wrong_type_missing_and_broad_scopes_stop_before_ads(self):
        cases = [{"is_valid": False}, {"app_id": "999"}, {"type": "PAGE"},
                 {"scopes": ["public_profile"]}, {"expires_at": 1},
                 {"data_access_expires_at": 1}, {"scopes": ["ads_read", "ads_management"]},
                 {"scopes": ["ads_read", "business_management"]}]
        for changes in cases:
            with self.subTest(changes=changes):
                self.session.get.reset_mock()
                self.session.get.side_effect = [response(token_data(**changes))]
                with self.assertRaises(MetaReadError):
                    self.reader.validate()
                self.assertFalse(self.reader.validated)
                self.assertEqual(self.session.get.call_count, 1)

    def test_account_mismatch_locks_reader_again(self):
        self.session.get.side_effect = [response(token_data()), response({**ACCOUNT, "id": "act_999"})]
        with self.assertRaises(MetaReadError):
            self.reader.validate()
        self.assertFalse(self.reader.validated)

    def test_write_methods_foreign_paths_and_parameters_blocked(self):
        self.validate()
        for method, path, params in [
            ("POST", "act_" + ACCOUNT_ID + "/insights", {"fields": "spend"}),
            ("DELETE", "act_" + ACCOUNT_ID, {"fields": "id"}),
            ("GET", "act_999/ads", {"fields": "id"}),
            ("GET", "https://evil.test/ads", {"fields": "id"}),
            ("GET", "act_" + ACCOUNT_ID + "/events", {"fields": "id"}),
            ("GET", "act_" + ACCOUNT_ID + "/ads", {"fields": "id", "method": "POST"}),
            ("GET", "act_" + ACCOUNT_ID + "/ads", {"fields": "id,creative{access_token}"}),
        ]:
            with self.subTest(method=method, path=path):
                with self.assertRaises(MetaReadError):
                    self.reader._request(method, path, params)
        self.session.get.assert_not_called()

    def test_pagination_ignores_arbitrary_next_url_and_rebuilds_same_request(self):
        self.validate()
        self.session.get.side_effect = [
            response({"data": [{"id": "1"}], "paging": {"next": "https://evil.test/?access_token=secret", "cursors": {"after": "cursor-two"}}}),
            response({"data": [{"id": "2"}]})]
        pages = self.reader.objects("campaigns")
        self.assertEqual([r["id"] for p in pages for r in p["data"]], ["1", "2"])
        for call in self.session.get.call_args_list:
            self.assertEqual(call.args[0], "https://graph.facebook.com/" + self.config.version + "/act_" + ACCOUNT_ID + "/campaigns")
            self.assertFalse(call.kwargs["allow_redirects"])
            self.assertNotIn("access_token", call.kwargs["params"])
        self.assertEqual(self.session.get.call_args.kwargs["params"]["after"], "cursor-two")
        self.assertNotIn("paging", json.dumps(pages))

    def test_missing_and_repeated_pagination_cursor_fail(self):
        self.validate()
        for paging in [{"next": "unused"}, {"next": "unused", "cursors": {"after": "repeated"}}]:
            self.session.get.side_effect = None
            self.session.get.return_value = response({"data": [], "paging": paging})
            with self.assertRaises(MetaReadError):
                self.reader.objects("ads")

    def test_error_redaction_and_no_permission_retry(self):
        self.validate()
        self.session.get.return_value = response({"error": {"code": 200, "message": self.config.token + self.config.app_secret}}, 400)
        with self.assertRaises(MetaReadError) as caught:
            self.reader.objects("ads")
        self.assertNotIn(self.config.token, str(caught.exception))
        self.assertNotIn(self.config.app_secret, str(caught.exception))
        self.assertEqual(self.session.get.call_count, 1)

    def test_rate_limit_retries_are_bounded(self):
        self.validate()
        self.session.get.return_value = response({"error": {"code": 80004}}, 429)
        with self.assertRaises(MetaReadError):
            self.reader.objects("ads")
        self.assertEqual(self.session.get.call_count, 3)
        self.assertEqual(self.reader.sleep.call_count, 2)

    def test_long_rate_limit_estimate_stops_without_immediate_retry(self):
        self.validate()
        r = response({"error": {"code": 80004}}, 400)
        r.headers = {"x-business-use-case-usage": json.dumps({ACCOUNT_ID: [
            {"estimated_time_to_regain_access": 51, "total_cputime": 101}]})}
        self.session.get.return_value = r
        with self.assertRaisesRegex(MetaReadError, "51 minutes"):
            self.reader.objects("ads")
        self.assertEqual(self.session.get.call_count, 1)
        self.reader.sleep.assert_not_called()

    def test_transport_errors_and_redirects_do_not_leak_credentials(self):
        self.validate()
        self.session.get.side_effect = requests.ConnectionError(self.config.token)
        with self.assertRaises(MetaReadError) as caught:
            self.reader.objects("ads")
        self.assertNotIn(self.config.token, str(caught.exception))
        self.session.get.side_effect = None
        self.session.get.return_value = response({}, 302)
        with self.assertRaises(MetaReadError):
            self.reader.objects("ads")

    def test_export_scrubber_removes_nested_credentials(self):
        data = {"access_token": self.config.token, "items": [{"text": self.config.app_secret,
                "url": "https://example.test/?access_token=another-token&x=1"}]}
        text = json.dumps(self.reader.scrub(data))
        for secret in (self.config.token, self.config.app_secret, "another-token"):
            self.assertNotIn(secret, text)

    def test_creatives_are_collected_once_from_known_reporting_ads(self):
        self.validate()
        self.session.get.return_value = response({"data": [
            {"id": "1", "creative": {"id": "200"}},
            {"id": "2", "creative": {"id": "200"}}]})
        self.reader.objects("ads")
        self.session.get.return_value = response({"id": "200", "url_tags": "utm_source=facebook"})
        self.reader.report_creatives({"1", "2"})
        self.assertEqual(self.session.get.call_args.args[0], "https://graph.facebook.com/" + self.config.version + "/200")
        self.assertEqual(self.session.get.call_count, 2)
        before = self.session.get.call_count
        pages = self.reader.objects("adcreatives")
        self.assertEqual(len(pages[0]["data"]), 1)
        self.assertEqual(self.session.get.call_count, before)
        with self.assertRaises(MetaReadError):
            self.reader._request("GET", "act_" + ACCOUNT_ID + "/adcreatives", {"fields": "id"})
        with self.assertRaises(MetaReadError):
            self.reader._request("GET", "999", {"fields": "id"})

    def test_optional_creative_permission_failure_is_recorded_without_broadening(self):
        self.validate()
        self.session.get.return_value = response({"data": [{"id": "1", "creative": {"id": "200"}}]})
        self.reader.objects("ads")
        self.session.get.side_effect = [response({"error": {"code": 200}}, 400), response({"id": "200", "name": "Creative"})]
        rows = self.reader.report_creatives({"1"})[0]["data"]
        self.assertEqual(rows, [{"id": "200", "name": "Creative"}])
        self.assertTrue(self.reader.creative_limitations[0]["basic_fields_retrieved"])
        self.assertEqual(self.session.get.call_args.kwargs["params"]["fields"], "id,name")

    def test_malformed_token_response_stops_safely(self):
        self.session.get.return_value = response({"data": [self.config.token]})
        with self.assertRaises(MetaReadError) as caught:
            self.reader.validate()
        self.assertNotIn(self.config.token, str(caught.exception))

    def test_insights_request_has_explicit_dates_and_attribution(self):
        self.validate()
        self.session.get.return_value = response({"data": []})
        self.reader.insights("2026-09-01", "2026-09-01")
        params = self.session.get.call_args.kwargs["params"]
        self.assertEqual(json.loads(params["time_range"]), {"since": "2026-09-01", "until": "2026-09-01"})
        self.assertEqual(params["level"], "ad")
        self.assertEqual(params["time_increment"], 1)
        self.assertEqual(params["action_report_time"], "impression")
        self.assertEqual(params["use_unified_attribution_setting"], "true")


class ReportingTests(unittest.TestCase):
    def test_windows_cover_month_once_and_are_at_most_seven_days(self):
        dates = []
        for start, end in windows("2026-09-01", "2026-09-30"):
            s, e = date.fromisoformat(start), date.fromisoformat(end)
            self.assertLessEqual((e-s).days, 6)
            dates.extend(range(s.toordinal(), e.toordinal()+1))
        self.assertEqual(len(dates), 30)
        self.assertEqual(len(set(dates)), 30)

    def test_action_types_kept_separate_missing_is_not_zero_and_reach_not_summed(self):
        rows = [{"ad_id": "1", "date_start": "2026-09-01", "date_stop": "2026-09-01",
                 "spend": "1.10", "reach": "10", "actions": [
                     {"action_type": "purchase", "value": "2"},
                     {"action_type": "omni_purchase", "value": "2"}]}]
        self.assertEqual([r["action_type"] for r in action_rows(rows)], ["purchase", "omni_purchase"])
        summary = totals(rows)
        self.assertNotIn("reach", summary)
        self.assertEqual(summary["spend"]["sum"], "1.10")
        self.assertIsNone(summary["clicks"]["sum"])

    def fake_reader(self):
        reader = Mock()
        reader.config = ReaderConfig("fresh-user-token-secret", "private-app-secret")
        reader.token_info = {"scopes": ["ads_read"]}
        reader.request_count = 2
        reader.rate_limit_info = {}
        reader.creative_limitations = []
        reader.scrub.side_effect = lambda value: value
        reader.objects.return_value = [{"data": []}]
        reader.insights.return_value = [{"data": []}]
        reader.report_creatives.return_value = [{"data": []}]
        return reader

    def test_empty_report_is_complete_and_new_runs_do_not_overwrite(self):
        reader = self.fake_reader()
        with TemporaryDirectory() as folder:
            p1, manifest = export_report(reader, ACCOUNT, "2026-09-01", "2026-09-01", folder, progress=lambda _: None)
            p2, _ = export_report(reader, ACCOUNT, "2026-09-01", "2026-09-01", folder, progress=lambda _: None)
            self.assertNotEqual(p1, p2)
            self.assertEqual(manifest["status"], "complete")
            self.assertEqual(manifest["counts"]["ad_daily_insights"], 0)
            self.assertTrue((p1 / "ad_daily_insights.csv").read_text().startswith("account_id,"))

    def test_failure_is_recorded_without_marking_partial_results_complete(self):
        reader = self.fake_reader()
        reader.insights.side_effect = MetaReadError("permission denied", 200)
        with TemporaryDirectory() as folder:
            with self.assertRaises(MetaReadError):
                export_report(reader, ACCOUNT, "2026-09-01", "2026-09-01", folder, progress=lambda _: None)
            manifest = json.loads(next(Path(folder).glob("*/manifest.json")).read_text())
            self.assertEqual(manifest["status"], "failed")
            self.assertFalse(next(Path(folder).iterdir()).joinpath("ad_daily_insights.csv").exists())

    def test_populated_report_preserves_metrics_actions_and_missing_values(self):
        reader = self.fake_reader()
        reader.objects.side_effect = lambda edge: [{"data": [
            {"id": "1", "creative": {"id": "200"}}] if edge == "ads" else []}]
        reader.insights.return_value = [{"data": [{"account_id": ACCOUNT_ID, "account_currency": "AUD",
            "ad_id": "1", "date_start": "2026-09-01", "date_stop": "2026-09-01", "spend": "12.34",
            "actions": [{"action_type": "purchase", "value": "2"}]}]}]
        reader.report_creatives.return_value = [{"data": [{"id": "200", "name": "Creative"}]}]
        with TemporaryDirectory() as folder:
            path, manifest = export_report(reader, ACCOUNT, "2026-09-01", "2026-09-01", folder, progress=lambda _: None)
            self.assertEqual(manifest["status"], "complete")
            self.assertEqual(manifest["additive_metric_totals"]["spend"]["sum"], "12.34")
            self.assertEqual(manifest["missing_field_counts"]["clicks"], 1)
            self.assertEqual(manifest["counts"]["insight_actions"], 1)
            self.assertEqual(manifest["reporting_ad_ids_without_collected_creative_ids"], [])
            self.assertIn("purchase", (path / "insight_actions.csv").read_text())

    def test_wrong_account_outside_dates_and_duplicate_rows_stop_export(self):
        valid = {"account_id": ACCOUNT_ID, "account_currency": "AUD", "ad_id": "1",
                 "date_start": "2026-09-01", "date_stop": "2026-09-01"}
        for rows in [[{**valid, "account_id": "999"}],
                     [{**valid, "date_start": "2026-08-01", "date_stop": "2026-08-01"}],
                     [valid, valid]]:
            with self.subTest(rows=rows), TemporaryDirectory() as folder:
                reader = self.fake_reader()
                reader.insights.return_value = [{"data": rows}]
                with self.assertRaises(MetaReadError):
                    export_report(reader, ACCOUNT, "2026-09-01", "2026-09-01", folder, progress=lambda _: None)


if __name__ == "__main__":
    unittest.main()
