"""Unfinished Meta object-story discovery experiment.

The saved 15-example run returned permission errors for every metadata and
object-story request. This script does not establish readable story data, a
complete Meta performance extract, pagination, or a production connector.
"""

import json
from pathlib import Path

import requests

from meta_discovery.auth import get_page_access_token
from scripts.meta.inspect_creative import CREATIVES


GRAPH_API_VERSION = "v25.0"
REQUEST_TIMEOUT_SECONDS = 30
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CREATIVE_RESULTS_PATH = (
    PROJECT_ROOT / "evidence" / "meta" / "list_creatives_of_15_ads.json"
)
OUTPUT_PATH = (
    PROJECT_ROOT / "evidence" / "meta" / "object_stories_of_15_ads.json"
)
OBJECT_STORY_FIELDS = (
    "id,message,created_time,permalink_url,full_picture,link,name,description,"
    "type,status_type,object_id,properties,shares,"
    "attachments{description,media,media_type,target,title,type,url,subattachments},"
    "comments.limit(0).summary(true),reactions.limit(0).summary(true)"
)


def make_graph_request(object_story_id: str, access_token: str, **params):
    """Make one Graph API request and preserve its complete response."""
    try:
        response = requests.get(
            f"https://graph.facebook.com/{GRAPH_API_VERSION}/{object_story_id}",
            params={**params, "access_token": access_token},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        return None, {"request_error": str(error)}

    try:
        response_body = response.json()
    except ValueError:
        response_body = response.text

    if response.ok:
        return response_body, None

    return None, {
        "http_status": response.status_code,
        "response": response_body,
    }


def load_creative_examples():
    """Combine the maintained 15-Creative list with its saved raw responses."""
    with CREATIVE_RESULTS_PATH.open(encoding="utf-8") as file:
        saved_results = json.load(file)

    saved_results_by_id = {
        result["creative_id"]: result for result in saved_results
    }

    examples = []
    for creative_config in CREATIVES:
        saved_result = saved_results_by_id.get(creative_config["creative_id"], {})
        creative = saved_result.get("creative", {})

        examples.append(
            {
                "ad_name": creative_config["ad_name"],
                "creative_id": creative_config["creative_id"],
                "effective_object_story_id": creative.get(
                    "effective_object_story_id"
                ),
            }
        )

    return examples


def main() -> None:
    access_token = get_page_access_token()
    creative_examples = load_creative_examples()
    results = []

    for creative_example in creative_examples:
        result = dict(creative_example)
        object_story_id = creative_example["effective_object_story_id"]

        if not object_story_id:
            result["skipped"] = "Creative has no effective_object_story_id"
            results.append(result)
            continue

        metadata, metadata_error = make_graph_request(
            object_story_id,
            access_token,
            metadata=1,
        )
        if metadata_error:
            result["metadata_error"] = metadata_error
        else:
            result["metadata"] = metadata

        object_story, object_story_error = make_graph_request(
            object_story_id,
            access_token,
            fields=OBJECT_STORY_FIELDS,
        )
        if object_story_error:
            result["error"] = object_story_error
        else:
            result["object_story"] = object_story

        results.append(result)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(results, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
