import requests

from meta_discovery.auth import get_access_token


def main() -> None:
    response = requests.get(
        "https://graph.facebook.com/v25.0/me/adaccounts",
        params={
            "fields": "id,name,account_status",
            "access_token": get_access_token(),
        },
    )

    if not response.ok:
        print(f"Meta API request failed with HTTP status {response.status_code}")
        print(response.json())
        return

    print("Accessible Meta Ad Accounts")

    for account in response.json()["data"]:
        print()
        print(f"Name: {account['name']}")
        print(f"ID: {account['id']}")
        print(f"Status: {account['account_status']}")


if __name__ == "__main__":
    main()
