from ga4_discovery.auth import get_credentials


def main() -> None:
    get_credentials()
    print("Authentication successful!")


if __name__ == "__main__":
    main()
