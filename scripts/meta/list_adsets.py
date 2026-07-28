import requests

from meta_discovery.auth import get_access_token


def main() -> None:
    response = requests.get(
        "https://graph.facebook.com/v25.0/act_2313037395632947/adsets",
        params={
            "fields": (
                "id,name,campaign_id,status,optimization_goal,billing_event,"
                "created_time,updated_time"
            ),
            "access_token": get_access_token(),
        },
    )

    if not response.ok:
        print(f"Meta API request failed with HTTP status {response.status_code}")
        print(response.json())
        return

    for ad_set in response.json()["data"]:
        print("----------------------------------------")
        print(f"Ad Set Name: {ad_set['name']}")
        print(f"ID: {ad_set['id']}")
        print(f"Campaign ID: {ad_set['campaign_id']}")
        print(f"Status: {ad_set['status']}")
        print(f"Optimization Goal: {ad_set['optimization_goal']}")
        print(f"Billing Event: {ad_set['billing_event']}")
        print(f"Created: {ad_set['created_time']}")
        print(f"Updated: {ad_set['updated_time']}")


if __name__ == "__main__":
    main()
