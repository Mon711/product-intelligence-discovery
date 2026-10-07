"""Step 2 selection, paging, ownership, partial evidence and command checks."""

from contextlib import redirect_stderr, redirect_stdout
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from meta_discovery.reader import ACCOUNT_ID, MetaReadError, MetaReader, ReaderConfig
from meta_discovery.sampling import collect_sample, select_ads
from scripts.meta.discover_connections import main


def response(payload, status=200):
    result = Mock(status_code=status)
    result.json.return_value = payload
    return result


def insight(ad="11", name="Example", impressions="5", **changes):
    return {"account_id": ACCOUNT_ID, "ad_id": ad, "ad_name": name,
            "adset_id": "21", "adset_name": "Set", "campaign_id": "31", "campaign_name": "Campaign",
            "date_start": "2026-07-01", "date_stop": "2026-07-07", "impressions": impressions, **changes}


def obj(kind, object_id, **changes):
    result = {"id": object_id, "account_id": ACCOUNT_ID, "name": kind, **changes}
    if kind == "ad":
        result.update({"campaign_id": "31", "adset_id": "21", "creative": {"id": "41"}})
    if kind == "adset":
        result["campaign_id"] = "31"
    return result


class SampleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.examples = self.folder / "examples.json"
        self.examples.write_text(json.dumps([{"ad_name": "Preferred"}]))
        self.session = Mock()
        self.reader = MetaReader(ReaderConfig("123", "fake-secret", "fake-token"), self.session)
        self.reader._validated = True

    def test_selection_is_deterministic_name_priority_then_numeric_id_and_excludes_zero(self):
        rows = [insight("2"), insight("100", "Preferred"), insight("10"), insight("1", "Preferred", "0")]
        self.assertEqual([r["ad_id"] for r in select_ads(rows, {"Preferred"}, 2)], ["100", "2"])
        self.assertEqual(select_ads(list(reversed(rows)), {"Preferred"}, 2), select_ads(rows, {"Preferred"}, 2))

    def test_pagination_uses_cursor_on_same_endpoint_and_discards_credential_urls(self):
        self.session.get.side_effect = [response({"data": [insight()], "paging": {"next": "https://evil.example/?access_token=fake-token", "cursors": {"after": "next-marker"}}}), response({"data": [insight("12")]})]
        pages = list(self.reader.insight_pages())
        self.assertEqual(len(pages), 2)
        self.assertEqual(self.session.get.call_args.kwargs["params"]["after"], "next-marker")
        self.assertEqual(self.session.get.call_args_list[0].args[0], self.session.get.call_args_list[1].args[0])
        self.assertNotIn("evil.example", json.dumps(pages))

    def test_missing_repeated_cursor_and_duplicate_ad_fail(self):
        cases = [
            [{"data": [], "paging": {"next": "ignored"}}],
            [{"data": [], "paging": {"next": "ignored", "cursors": {"after": "same"}}}, {"data": [], "paging": {"next": "ignored", "cursors": {"after": "same"}}}],
            [{"data": [insight(), insight()]}],
        ]
        for payloads in cases:
            with self.subTest(payloads=payloads):
                self.session.get.side_effect = [response(p) for p in payloads]
                with self.assertRaises(MetaReadError):
                    list(self.reader.insight_pages())

    def test_bad_account_date_identifier_or_impressions_fails(self):
        for changes in ({"account_id": "999"}, {"date_start": "2026-06-01"}, {"ad_id": "bad"}, {"impressions": None}):
            with self.subTest(changes=changes):
                self.session.get.return_value = response({"data": [insight(**changes)]})
                with self.assertRaises(MetaReadError):
                    list(self.reader.insight_pages())

    def test_requires_access_and_discovered_object_references(self):
        self.reader._validated = False
        with self.assertRaises(MetaReadError):
            list(self.reader.insight_pages())
        self.reader._validated = True
        with self.assertRaises(MetaReadError):
            self.reader.register_sample([insight()])
        with self.assertRaises(MetaReadError):
            self.reader.object("ad", "11")
        self.session.get.assert_not_called()

    def test_complete_sample_reads_unique_parents_once_and_saves_only_creative_id(self):
        self.session.get.side_effect = [response({"data": [insight(), insight("12")]}),
                                        response(obj("ad", "11")), response(obj("adset", "21")),
                                        response(obj("campaign", "31")), response(obj("ad", "12"))]
        result = collect_sample(self.reader, self.folder, self.examples, 15)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(result["hierarchy"]), 2)
        self.assertEqual(self.session.get.call_count, 5)
        self.assertEqual(len(result["objects"]["campaign"]), 1)
        self.assertEqual(result["hierarchy"][0]["creative_id"], "41")
        self.assertFalse(any(call.args[0].endswith("/41") for call in self.session.get.call_args_list))
        with (self.folder / "hierarchy.csv").open() as file:
            self.assertEqual(len(list(csv.DictReader(file))), 2)

    def test_incomplete_insights_save_pages_without_selecting_ads(self):
        self.session.get.side_effect = [response({"data": [insight()], "paging": {"next": "ignored", "cursors": {"after": "a"}}}), response({"error": {"code": 80004}}, 400)]
        result = collect_sample(self.reader, self.folder, self.examples, 15)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["insights_complete"])
        self.assertEqual(result["selected"], [])
        self.assertEqual(len(json.loads((self.folder / "insights.json").read_text())["rows"]), 1)

    def test_unavailable_ad_is_retained_as_a_gap(self):
        self.session.get.side_effect = [response({"data": [insight()]}), response({"error": {"code": 100, "message": "fake-token"}}, 400), response(obj("adset", "21")), response(obj("campaign", "31"))]
        result = collect_sample(self.reader, self.folder, self.examples, 15)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["hierarchy"][0]["ad_read_status"], "unavailable")
        self.assertIsNone(result["hierarchy"][0]["creative_id"])
        self.assertNotIn("fake-token", (self.folder / "sample.json").read_text())

    def test_wrong_object_account_stops_run(self):
        self.session.get.side_effect = [response({"data": [insight()]}), response(obj("ad", "11", account_id="999"))]
        self.assertEqual(collect_sample(self.reader, self.folder, self.examples, 15)["status"], "failed")
        self.assertEqual(self.session.get.call_count, 2)

    def test_changed_parent_relationship_is_reported_as_gap(self):
        changed = obj("ad", "11")
        changed["adset_id"] = "999"
        self.session.get.side_effect = [response({"data": [insight()]}), response(changed), response(obj("adset", "21")), response(obj("campaign", "31"))]
        result = collect_sample(self.reader, self.folder, self.examples, 15)
        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["hierarchy"][0]["issues"])

    def test_no_delivery_is_explicit_empty_sample(self):
        self.session.get.return_value = response({"data": [insight(impressions="0")]})
        result = collect_sample(self.reader, self.folder, self.examples, 15)
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["empty_sample"])
        self.assertEqual(self.session.get.call_count, 1)

    def test_known_credentials_in_labels_are_redacted(self):
        self.session.get.return_value = response({"data": [insight(name="fake-token fake-secret")]})
        data = list(self.reader.insight_pages())
        self.assertEqual(data[0][0]["ad_name"], "[REDACTED] [REDACTED]")

    def test_sample_arguments_fail_before_work(self):
        for args in (["--stage", "sample", "--offline"], ["--stage", "sample", "--max-ads", "16"], ["--stage", "creatives"]):
            with self.subTest(args=args), patch("scripts.meta.discover_connections.audit_foundation") as audit, redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    main(args)
                self.assertEqual(caught.exception.code, 2)
                audit.assert_not_called()

    def test_live_command_coordinates_sample_and_writes_summary(self):
        cfg = ReaderConfig("123", "fake-secret", "fake-token")
        self.reader.config = cfg
        debug = {"data": {"is_valid": True, "app_id": "123", "type": "USER", "scopes": ["ads_read"], "expires_at": 0, "data_access_expires_at": 0}}
        account = {"id": f"act_{ACCOUNT_ID}", "account_id": ACCOUNT_ID, "currency": "AUD", "timezone_name": "Australia/Sydney"}
        self.session.get.side_effect = [response(debug), response(account), response({"data": [insight()]}), response(obj("ad", "11")), response(obj("adset", "21")), response(obj("campaign", "31"))]
        with patch("scripts.meta.discover_connections.ReaderConfig.from_file", return_value=cfg), patch("scripts.meta.discover_connections.MetaReader", return_value=self.reader), redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--stage", "sample", "--max-ads", "1", "--output-dir", str(self.folder / "runs")]), 0)
        report = json.loads(next((self.folder / "runs").glob("*/summary.json")).read_text())
        self.assertEqual(report["sample"]["selected_count"], 1)
        self.assertEqual(report["sample"]["request_count_including_access"], 6)


if __name__ == "__main__":
    unittest.main()
