import requests

from meta_discovery.auth import get_access_token


def main() -> None:
    response = requests.get(
        "https://graph.facebook.com/v25.0/act_2313037395632947/ads",
        params={
            "fields": (
                "id,name,campaign_id,adset_id,status,creative,created_time,"
                "updated_time"
            ),
            "access_token": get_access_token(),
        },
    )

    if not response.ok:
        print(f"Meta API request failed with HTTP status {response.status_code}")
        print(response.json())
        return

    for ad in response.json()["data"]:
        print("----------------------------------------")
        print(f"Ad Name: {ad['name']}")
        print(f"ID: {ad['id']}")
        print(f"Campaign ID: {ad['campaign_id']}")
        print(f"Ad Set ID: {ad['adset_id']}")
        print(f"Status: {ad['status']}")
        print(f"Creative ID: {ad['creative']['id']}")
        print(f"Created: {ad['created_time']}")
        print(f"Updated: {ad['updated_time']}")


if __name__ == "__main__":
    main()
