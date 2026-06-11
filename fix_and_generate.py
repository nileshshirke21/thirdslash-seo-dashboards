import pickle
import datetime
import gspread
from google.auth.transport.requests import Request

SHEET_ID = "1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"

def get_credentials():
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

creds = get_credentials()
gc = gspread.authorize(creds)
sh = gc.open_by_key(SHEET_ID)
profile_ws = sh.worksheet("01_Client Profile")

# Get actual headers from row 3
all_values = profile_ws.get_all_values()
headers = all_values[2]  # Row 3 is index 2
print("Actual headers in your sheet:")
for i, h in enumerate(headers):
    print(f"  Col {i+1}: '{h}'")
