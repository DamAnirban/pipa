"""
oauth_setup.py
Run this ONCE on the Pi to authorize Google Calendar access (read + write).
Saves credentials/token.json. Auto-refreshes forever after.

Usage:
    python3 scripts/oauth_setup.py
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

# Full access — read + write
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Computed independently of config.py so this script stays runnable on its
# own without needing src/ on sys.path.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(ROOT_DIR, "credentials", "credentials.json")
TOKEN_PATH = os.path.join(ROOT_DIR, "credentials", "token.json")


def main():
    if not os.path.exists(CREDENTIALS_FILE):
        print("ERROR: credentials.json not found.")
        print("Download it from Google Cloud Console → APIs & Services → Credentials")
        print(f"Save it here: {CREDENTIALS_FILE}")
        return

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    auth_url, _ = flow.authorization_url(prompt="consent")
    print(f"\nOpen this URL on your phone or laptop:\n{auth_url}\n")
    code = input("Paste the authorization code here: ").strip()
    flow.fetch_token(code=code)
    creds = flow.credentials

    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

    print(f"\nDone. Token saved to {TOKEN_PATH}")
    print("Read + write access granted. Claude client will auto-refresh going forward.")


if __name__ == "__main__":
    main()