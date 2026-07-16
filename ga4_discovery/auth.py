from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config" / "ga4"
CLIENT_FILE = CONFIG_DIR / "ga4_oauth_client.json"
TOKEN_FILE = CONFIG_DIR / "ga4_token.json"


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
