import json

import requests

from meta_discovery.auth import get_access_token


CREATIVES = [
    {
        "ad_name": "Steele_outerwear_14may26_static1",
        "creative_id": "2231962067556522",
    },
    {
        "ad_name": "Steele_NewArrivals_16april26_Video1",
        "creative_id": "1320608509934183",
    },
    {
        "ad_name": "Steele_newarrivals_ZelieJacket_motion_july26",
        "creative_id": "1438954678061258",
    },
    {
        "ad_name": "Steele_Bestsellers_ZelieJacket_Gif_july26",
        "creative_id": "1349271994059188",
    },
    {
        "ad_name": "Steele_Bestsellers_ZelieJacket_static1_july26",
        "creative_id": "2297529757684942",
    },
    {
        "ad_name": "Steele_NewArrivals_July26_gif1",
        "creative_id": "1508525333909047",
    },
    {
        "ad_name": "Steele_sets_Instapost2_july26",
        "creative_id": "2120599798496708",
    },
    {
        "ad_name": "SaleProducts_DPA",
        "creative_id": "1744300190039110",
    },
    {
        "ad_name": "Steele New arrival_catalog 2026 – Copy",
        "creative_id": "813515491814716",
    },
    {
        "ad_name": "Steele_new arrivaqsl insta post 5",
        "creative_id": "2128984187978979",
    },
    {
        "ad_name": "Steele_collection_Carousel14may26",
        "creative_id": "1325799332799642",
    },
    {
        "ad_name": "Steele_retargeting_Full Price catalogue_30april26",
        "creative_id": "2213623069380197",
    },
    {
        "ad_name": "Steele_motion1_hannecoat_30june26",
        "creative_id": "2535887650173076",
    },
    {
        "ad_name": "Steele_outerwear_Collectionad_30june26",
        "creative_id": "1761957141639803",
    },
    {
        "ad_name": "Steele_static_hannecoat_30june26",
        "creative_id": "2046040699337199",
    },
]


def main() -> None:
    access_token = get_access_token()
    results = []

    for creative_config in CREATIVES:
        response = requests.get(
            f"https://graph.facebook.com/v25.0/{creative_config['creative_id']}",
            params={
                "fields": (
                    "id,name,title,body,thumbnail_url,image_url,image_hash,"
                    "video_id,object_type,object_story_spec,asset_feed_spec,"
                    "effective_object_story_id,product_set_id,template_url,"
                    "url_tags,call_to_action_type"
                ),
                "access_token": access_token,
            },
        )

        if not response.ok:
            results.append(
                {
                    "ad_name": creative_config["ad_name"],
                    "creative_id": creative_config["creative_id"],
                    "error": {
                        "http_status": response.status_code,
                        "response": response.text,
                    },
                }
            )
            continue

        results.append(
            {
                "ad_name": creative_config["ad_name"],
                "creative_id": creative_config["creative_id"],
                "creative": response.json(),
            }
        )

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
