from pathlib import Path

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
CLIENT_FILE = Path("ga4_oauth_client.json")
TOKEN_FILE = Path("ga4_token.json")
PROPERTY_ID = "268350484"


def get_credentials() -> Credentials:
    credentials = None

    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
            credentials = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(credentials.to_json())

    return credentials


def main() -> None:
    client = BetaAnalyticsDataClient(credentials=get_credentials())
    metadata = client.get_metadata(name=f"properties/{PROPERTY_ID}/metadata")

    print("====================")
    print("DIMENSIONS")
    print("====================")
    for dimension in metadata.dimensions:
        print(f"API name: {dimension.api_name}")
        print(f"Display name: {dimension.ui_name}")
        print(f"Description: {dimension.description}")
        print()

    print("====================")
    print("METRICS")
    print("====================")
    for metric in metadata.metrics:
        print(f"API name: {metric.api_name}")
        print(f"Display name: {metric.ui_name}")
        print(f"Description: {metric.description}")
        print()


if __name__ == "__main__":
    main()
