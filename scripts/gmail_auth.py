"""
One-time Gmail OAuth setup. Run this once from the project root:

    python3 scripts/gmail_auth.py

Steps:
  1. Go to console.cloud.google.com → New project
  2. APIs & Services → Enable APIs → search "Gmail API" → Enable
  3. APIs & Services → Credentials → Create Credentials → OAuth client ID
     → Application type: Desktop app → Download JSON → save as:
     src/backend/credentials.json
  4. Run this script → browser opens → sign in → approve access
  5. token.json is saved to src/backend/ — the app uses it automatically

token.json auto-refreshes so you only need to run this once.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent / "src" / "backend"
CREDS_FILE = BACKEND_DIR / "credentials.json"
TOKEN_FILE = BACKEND_DIR / "token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main():
    if not CREDS_FILE.exists():
        print(f"ERROR: {CREDS_FILE} not found.")
        print()
        print("Setup steps:")
        print("  1. Go to console.cloud.google.com → New project")
        print("  2. APIs & Services → Enable APIs → search 'Gmail API' → Enable")
        print("  3. APIs & Services → Credentials → Create Credentials")
        print("     → OAuth client ID → Desktop app → Download JSON")
        print(f"  4. Save the downloaded file as: {CREDS_FILE}")
        print("  5. Re-run this script")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: google-auth-oauthlib not installed.")
        print(f"Run: source {BACKEND_DIR}/.venv/bin/activate && pip install google-auth-oauthlib")
        sys.exit(1)

    print("Opening browser for Gmail authorization...")
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    print(f"\nAuthorization complete. Token saved to: {TOKEN_FILE}")
    print("The Email Alerts feature will now use your real Gmail.")
    print("\nTo revoke access later: myaccount.google.com → Security → Third-party access")


if __name__ == "__main__":
    main()
