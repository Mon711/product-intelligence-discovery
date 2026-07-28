import requests

from meta_discovery.auth import get_access_token


def main() -> None:
    response = requests.get(
        "https://graph.facebook.com/v25.0/act_2313037395632947/campaigns",
        params={
            "fields": "id,name,status,objective,created_time,updated_time",
            "access_token": get_access_token(),
        },
    )

    if not response.ok:
        print(f"Meta API request failed with HTTP status {response.status_code}")
        print(response.json())
        return

    for campaign in response.json()["data"]:
        print("----------------------------------------")
        print(f"Campaign Name: {campaign['name']}")
        print(f"ID: {campaign['id']}")
        print(f"Status: {campaign['status']}")
        print(f"Objective: {campaign['objective']}")
        print(f"Created: {campaign['created_time']}")
        print(f"Updated: {campaign['updated_time']}")


if __name__ == "__main__":
    main()
