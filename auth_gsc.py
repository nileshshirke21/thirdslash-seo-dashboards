"""
Authenticate with connectthirdslash@gmail.com for GSC access.
Run once: python3 auth_gsc.py
This creates token_gsc.pickle for the URL Inspection API.
"""
import pickle, os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/webmasters",
]

BASE = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET = os.path.join(BASE, "client_secret.json")
TOKEN_FILE = os.path.join(BASE, "token_gsc.pickle")

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
creds = flow.run_local_server(port=8888, prompt="consent")

with open(TOKEN_FILE, "wb") as f:
    pickle.dump(creds, f)

print(f"\n✅ Token saved to {TOKEN_FILE}")
print("This token will be used for GSC URL Inspection API calls.")
