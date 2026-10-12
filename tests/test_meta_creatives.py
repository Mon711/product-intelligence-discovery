"""Step 3 account binding, availability, bounded catalogue reads and retained failures."""

from contextlib import redirect_stderr, redirect_stdout
import csv
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

from meta_discovery.creatives import availability, collect_creatives, load_sample, read_group
from meta_discovery.reader import ACCOUNT_ID, CONNECTION_FIELDS, ITEM_FIELDS, MetaFieldUnavailable, MetaReadError, MetaReader, ReaderConfig
from scripts.meta.discover_connections import REPO_ROOT, main


def response(payload, status=200):
    result = Mock(status_code=status)
    result.json.return_value = payload
    return result


def reference(ad="11", creative="41"):
    return {"ad_id": ad, "creative_id": creative, "adset_id": "21", "campaign_id": "31", "status": "complete"}


class CreativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.session = Mock()
        self.reader = MetaReader(ReaderConfig("123", "fake-secret", "fake-token"), self.session)
        self.reader._validated = True
        self.saved = {"hierarchy": [reference()], "source": {"selected_ads": 1, "unique_creatives": 1}}
        self.destination = {"id": "41", "account_id": ACCOUNT_ID, "link_url": "https://example.com/products/test?variant=123",
                            "object_story_spec": {"link_data": {"child_attachments": [{"link": "https://example.com/one"}, {"link": "https://example.com/two"}]}},
                            "url_tags": "utm_campaign={{campaign.name}}", "asset_feed_spec": {}, "object_url": None}
        self.catalogue = {"id": "41", "account_id": ACCOUNT_ID}
        self.promoted = {"id": "21", "account_id": ACCOUNT_ID, "campaign_id": "31", "promoted_object": {"pixel_id": "51"}}
        self.session.get.side_effect = self.default_response

    def default_response(self, url, **kwargs):
        object_id, fields = url.rsplit("/", 1)[-1], kwargs["params"]["fields"]
        if object_id in ("11", "12"):
            return response({"id": object_id, "account_id": ACCOUNT_ID, "adset_id": "21", "campaign_id": "31", "creative": {"id": "41"}})
        return response(self.destination if fields == CONNECTION_FIELDS["destination"] else self.promoted if fields == CONNECTION_FIELDS["promoted"] else self.catalogue)

    def bind(self):
        self.reader.bind_connection_ad(reference())
        self.session.reset_mock()

    def test_saved_sample_provenance_validates_and_rejects_tampering(self):
        source = REPO_ROOT / "evidence/meta/samples/20261006T132743461677Z"
        for name in ("sample.json", "summary.json"):
            shutil.copyfile(source / name, self.folder / name)
        valid = load_sample(self.folder)
        self.assertEqual(valid["source"]["unique_creatives"], 15)
        self.assertEqual(len(valid["source"]["files"]["sample.json"]), 64)
        original = json.loads((self.folder / "sample.json").read_text())
        for change in ("account", "creative", "status", "dates"):
            data = json.loads(json.dumps(original))
            if change == "account":
                data["selected"][0]["account_id"] = "999"
            elif change == "creative":
                data["hierarchy"][0]["creative_id"] = "999"
            elif change == "status":
                data["status"] = "partial"
            else:
                data["dates"]["since"] = "2026-06-01"
            (self.folder / "sample.json").write_text(json.dumps(data))
            with self.subTest(change=change), self.assertRaises(MetaReadError):
                load_sample(self.folder)

    def test_unknown_creatives_product_sets_page_edges_and_fields_are_blocked(self):
        for object_id, fields in (("41", CONNECTION_FIELDS["destination"]), ("999", CONNECTION_FIELDS["catalogue"])):
            with self.assertRaises(MetaReadError):
                self.reader.connection(object_id, fields)
        with self.assertRaises(MetaReadError):
            list(self.reader.product_pages("61"))
        self.session.get.assert_not_called()
        self.bind()
        for endpoint, fields in (("41", "id,body"), ("41/posts", "id"), (f"act_{ACCOUNT_ID}/adcreatives", "id")):
            with self.assertRaises(MetaReadError):
                self.reader._ads_get(endpoint, {"fields": fields})
        self.session.get.assert_not_called()
        self.assertFalse(self.session.post.called)

    def test_current_ad_wrong_account_or_changed_reference_stops_before_creative(self):
        for changes in ({"account_id": "999"}, {"creative": {"id": "999"}}, {"adset_id": "999"}):
            self.session.reset_mock()
            self.session.get.side_effect = None
            self.session.get.return_value = response({"id": "11", "account_id": ACCOUNT_ID, "creative": {"id": "41"}, "adset_id": "21", "campaign_id": "31", **changes})
            with self.subTest(changes=changes), self.assertRaises(MetaReadError):
                self.reader.bind_connection_ad(reference())
            self.assertEqual(self.session.get.call_count, 1)

    def test_nested_values_placeholders_and_availability_are_preserved(self):
        result = collect_creatives(self.reader, self.folder, self.saved, 1)
        self.assertEqual(result["status"], "complete")
        data = json.loads((self.folder / "creatives.json").read_text())["creatives"]["41"]["destination"]["data"]
        self.assertEqual(data["object_story_spec"], self.destination["object_story_spec"])
        self.assertEqual(data["url_tags"], "utm_campaign={{campaign.name}}")
        with (self.folder / "field_dictionary.csv").open() as file:
            fields = {r["field"]: r["availability"] for r in csv.DictReader(file)}
        self.assertEqual(fields["link_url"], "populated")
        self.assertEqual(fields["asset_feed_spec"], "empty")
        self.assertEqual(fields["object_url"], "empty")
        self.assertEqual(fields["product_set_id"], "omitted")
        self.assertEqual(result["catalogue_status"], "no_references")

    def test_shared_creative_and_adset_are_read_once_per_group(self):
        self.saved["hierarchy"].append(reference("12"))
        collect_creatives(self.reader, self.folder, self.saved, 15)
        self.assertEqual(self.session.get.call_count, 5)  # two bindings, two groups, one ad set
        self.assertEqual(sum(c.kwargs["params"]["fields"] == CONNECTION_FIELDS["destination"] for c in self.session.get.call_args_list), 1)

    def test_permission_block_is_recorded_without_fallback_or_permission_expansion(self):
        self.bind()
        self.session.get.side_effect = None
        self.session.get.return_value = response({"error": {"code": 200, "message": "fake-token"}}, 403)
        result = read_group(self.reader, "41", "destination")
        self.assertEqual(result["status"], "complete_with_gaps")
        self.assertEqual(result["diagnostics"]["link_url"]["status"], "permission_blocked")
        self.assertEqual(self.session.get.call_count, 1)
        self.assertNotIn("fake-token", json.dumps(result))

    def test_unsupported_field_fallback_is_bounded_and_preserves_other_fields(self):
        self.bind()
        def fallback(url, **kwargs):
            fields = kwargs["params"]["fields"]
            if fields == CONNECTION_FIELDS["destination"] or fields.endswith(",object_url"):
                return response({"error": {"code": 100, "message": "Tried accessing nonexisting field object_url fake-secret"}}, 400)
            key = fields.split(",")[-1]
            return response({"id": "41", "account_id": ACCOUNT_ID, key: "value"})
        self.session.get.side_effect = fallback
        result = read_group(self.reader, "41", "destination")
        self.assertEqual(result["diagnostics"]["object_url"]["status"], "unsupported")
        self.assertEqual(result["data"]["link_url"], "value")
        self.assertEqual(self.session.get.call_count, 8)
        self.assertNotIn("fake-secret", json.dumps(result))

    def test_ambiguous_code_100_is_unavailable_not_unsupported_or_permission_proof(self):
        self.bind()
        self.session.get.side_effect = None
        self.session.get.return_value = response({"error": {"code": 100, "message": "Unsupported get request. Object may not exist or lack permissions"}}, 400)
        result = read_group(self.reader, "41", "catalogue")
        self.assertEqual(result["diagnostics"]["product_set_id"]["status"], "unavailable")
        self.assertEqual(self.session.get.call_count, 1)

    def test_wrong_creative_account_fails_and_does_not_register_product_set(self):
        self.bind()
        self.session.get.side_effect = None
        self.session.get.return_value = response({"id": "41", "account_id": "999", "product_set_id": "61"})
        with self.assertRaises(MetaReadError):
            self.reader.connection("41", CONNECTION_FIELDS["catalogue"])
        self.assertEqual(self.reader._product_sets, set())

    def test_rate_limit_preserves_completed_group_and_stops_without_retry(self):
        original = self.default_response
        def limited(url, **kwargs):
            if kwargs["params"]["fields"] == CONNECTION_FIELDS["catalogue"]:
                return response({"error": {"code": 80004, "message": "fake-token"}}, 400)
            return original(url, **kwargs)
        self.session.get.side_effect = limited
        result = collect_creatives(self.reader, self.folder, self.saved, 1)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(self.session.get.call_count, 3)
        data = json.loads((self.folder / "creatives.json").read_text())
        self.assertEqual(data["creatives"]["41"]["destination"]["data"]["link_url"], self.destination["link_url"])
        self.assertEqual(data["adsets"]["21"]["promoted"]["status"], "not_requested")
        self.assertNotIn("fake-token", (self.folder / "manifest.json").read_text())

    def test_network_failure_stops_without_exposing_request_url(self):
        self.session.get.side_effect = requests.ConnectionError("access_token=fake-token")
        result = collect_creatives(self.reader, self.folder, self.saved, 1)
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("fake-token", json.dumps(result))
        self.assertEqual(self.session.get.call_count, 1)

    def test_nested_secret_keys_and_known_credentials_are_scrubbed(self):
        self.destination["object_story_spec"] = {"access_token": "unknown-secret", "nested": {"fake-token": "fake-secret"}}
        self.destination["link_url"] = "https://example.com/?access_token=unrecognized-url-secret&utm_campaign={{campaign.name}}"
        collect_creatives(self.reader, self.folder, self.saved, 1)
        for path in self.folder.iterdir():
            text = path.read_text()
            for secret in ("fake-token", "fake-secret", "unknown-secret", "unrecognized-url-secret"):
                self.assertNotIn(secret, text)
        self.assertIn("{{campaign.name}}", (self.folder / "creatives.json").read_text())

    def test_fatal_fallback_retains_completed_fields_and_stops(self):
        self.bind()
        def fallback(url, **kwargs):
            fields = kwargs["params"]["fields"]
            if fields == CONNECTION_FIELDS["destination"]:
                return response({"error": {"code": 100, "message": "nonexisting field object_url"}}, 400)
            if fields.endswith(",link_url"):
                return response({"error": {"code": 80004}}, 400)
            return response({"id": "41", "account_id": ACCOUNT_ID, fields.split(",")[-1]: "value"})
        self.session.get.side_effect = fallback
        result = read_group(self.reader, "41", "destination")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["data"]["name"], "value")
        self.assertEqual(result["diagnostics"]["object_story_spec"]["status"], "not_requested")
        self.assertEqual(self.session.get.call_count, 4)

    def test_wrong_adset_campaign_stops_and_preserves_its_response(self):
        self.promoted["campaign_id"] = "999"
        result = collect_creatives(self.reader, self.folder, self.saved, 1)
        self.assertEqual(result["status"], "failed")
        data = json.loads((self.folder / "creatives.json").read_text())
        self.assertEqual(data["adsets"]["21"]["promoted"]["data"]["campaign_id"], "999")

    def test_empty_configuration_failure_does_not_network_or_load_real_credentials(self):
        source = REPO_ROOT / "evidence/meta/samples/20261006T132743461677Z"
        with patch("meta_discovery.reader.requests.Session") as session, redirect_stdout(io.StringIO()):
            code = main(["--stage", "creatives", "--sample-dir", str(source), "--config", "/dev/null", "--output-dir", str(self.folder / "runs")])
        self.assertEqual(code, 1)
        session.assert_not_called()
        summary = json.loads(next((self.folder / "runs").glob("*/summary.json")).read_text())
        self.assertEqual(summary["meta"]["status"], "failed")

    def test_catalogue_paging_caps_at_20_and_never_follows_next_urls(self):
        self.reader._product_sets.add("61")
        self.session.get.side_effect = [response({"data": [{"id": str(i)} for i in range(1, 8)], "paging": {"next": "https://evil/?access_token=fake-token", "cursors": {"after": "a"}}}),
                                        response({"data": [{"id": str(i)} for i in range(8, 21)], "paging": {"next": "ignored"}})]
        pages = list(self.reader.product_pages("61"))
        self.assertEqual(sum(len(p[0]) for p in pages), 20)
        self.assertEqual(self.session.get.call_count, 2)
        self.assertEqual(self.session.get.call_args.kwargs["params"]["limit"], 13)
        self.assertTrue(pages[-1][1])
        self.assertTrue(all(c.args[0].endswith("/61/products") for c in self.session.get.call_args_list))
        self.assertNotIn("evil", json.dumps(pages))

    def test_catalogue_invalid_pagination_duplicates_and_oversized_pages_fail(self):
        self.reader._product_sets.add("61")
        for payload in ({"data": [], "paging": {"next": "ignored"}}, {"data": [{"id": "1"}, {"id": "1"}]}, {"data": [{"id": str(i)} for i in range(21)]}):
            self.session.get.side_effect = None
            self.session.get.return_value = response(payload)
            with self.subTest(payload=payload), self.assertRaises(MetaReadError):
                list(self.reader.product_pages("61"))

    def test_first_accessible_referenced_set_and_item_fields_are_saved(self):
        self.catalogue["product_set_id"] = "61"
        self.promoted["promoted_object"] = {"product_set_id": "62"}
        def products(url, **kwargs):
            if url.endswith("/61/products"):
                return response({"error": {"code": 200}}, 403)
            if url.endswith("/62/products"):
                return response({"data": [{"id": "71", "retailer_id": "shopify_AU_123_456", "url": "https://example.com/products/a"}]})
            return self.default_response(url, **kwargs)
        self.session.get.side_effect = products
        result = collect_creatives(self.reader, self.folder, self.saved, 1)
        data = json.loads((self.folder / "catalogue.json").read_text())
        self.assertEqual(result["status"], "complete")
        self.assertEqual(data["selected_product_set_id"], "62")
        self.assertEqual(data["attempts"][0]["availability"], "permission_blocked")
        self.assertTrue(data["all_set_items_collected"])
        self.assertEqual(data["items"][0]["retailer_id"], "shopify_AU_123_456")

    def test_catalogue_failure_after_a_page_retains_items_and_failed_manifest(self):
        self.catalogue["product_set_id"] = "61"
        pages = iter([response({"data": [{"id": "71"}], "paging": {"next": "ignored", "cursors": {"after": "a"}}}), response({"error": {"code": 80004}}, 400)])
        def products(url, **kwargs):
            return next(pages) if url.endswith("/61/products") else self.default_response(url, **kwargs)
        self.session.get.side_effect = products
        result = collect_creatives(self.reader, self.folder, self.saved, 1)
        data = json.loads((self.folder / "catalogue.json").read_text())
        self.assertEqual(result["status"], "failed")
        self.assertEqual(data["items"], [{"id": "71"}])
        self.assertFalse(data["all_set_items_collected"])

    def test_all_catalogue_permissions_blocked_is_documented_success_with_gaps(self):
        self.catalogue["product_set_id"] = "61"
        def products(url, **kwargs):
            return response({"error": {"code": 200}}, 403) if url.endswith("/products") else self.default_response(url, **kwargs)
        self.session.get.side_effect = products
        result = collect_creatives(self.reader, self.folder, self.saved, 1)
        self.assertEqual(result["status"], "complete_with_gaps")
        self.assertEqual(result["catalogue_status"], "unavailable")

    def test_empty_product_set_is_accessible_and_stops_without_trying_next_set(self):
        self.catalogue["product_set_id"] = "61"
        self.promoted["promoted_object"] = {"product_set_id": "62"}
        def products(url, **kwargs):
            return response({"data": []}) if url.endswith("/products") else self.default_response(url, **kwargs)
        self.session.get.side_effect = products
        result = collect_creatives(self.reader, self.folder, self.saved, 1)
        self.assertEqual(result["catalogue_item_count"], 0)
        data = json.loads((self.folder / "catalogue.json").read_text())
        self.assertEqual(data["selected_product_set_id"], "61")
        self.assertEqual(len(data["attempts"]), 1)
        self.assertEqual(data["attempts"][0]["availability"], "empty")

    def test_cli_rejects_invalid_arguments_and_invalid_sample_before_credentials(self):
        for args in (["--stage", "creatives"], ["--stage", "creatives", "--sample-dir", str(self.folder), "--offline"], ["--stage", "creatives", "--sample-dir", str(self.folder), "--max-creatives", "16"]):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(args)
            self.assertEqual(caught.exception.code, 2)
        with patch("scripts.meta.discover_connections.ReaderConfig.from_file") as cfg, redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--stage", "creatives", "--sample-dir", str(self.folder), "--output-dir", str(self.folder / "runs")]), 1)
        cfg.assert_not_called()

    def test_cli_coordinates_creative_stage_and_writes_success_summary(self):
        safe_meta = {"status": "passed", "account": {"account_id": ACCOUNT_ID, "currency": "AUD", "timezone_name": "Australia/Sydney"}, "api_version": "v26.0", "token": {"scopes": ["ads_read"]}}
        with patch("scripts.meta.discover_connections.load_sample", return_value=self.saved), patch("scripts.meta.discover_connections.ReaderConfig.from_file", return_value=self.reader.config), patch("scripts.meta.discover_connections.MetaReader", return_value=self.reader), patch.object(self.reader, "validate", return_value=safe_meta), redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--stage", "creatives", "--sample-dir", "ignored", "--max-creatives", "1", "--output-dir", str(self.folder / "runs")]), 0)
        summary = json.loads(next((self.folder / "runs").glob("*/summary.json")).read_text())
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["creatives"]["creative_count"], 1)


if __name__ == "__main__":
    unittest.main()
