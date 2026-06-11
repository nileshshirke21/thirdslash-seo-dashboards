import pickle
import gspread
from google.auth.transport.requests import Request

SHEET_ID = "1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"

def get_credentials():
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def add_active_column():
    creds = get_credentials()
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.worksheet("01_Client Profile")

    # Insert new column A (shifts everything right)
    ws.insert_cols([["Active"], ["Yes"], ["Yes"], ["Yes"], ["Yes"],
        ["Yes"], ["Yes"], ["Yes"], ["Yes"], ["Yes"], ["Yes"],
        ["Yes"], ["Yes"], ["Yes"], ["Yes"], ["Yes"], ["Yes"]], col=1)

    # Update header row 3 col 1
    ws.update_cell(3, 1, "Active")

    print("Done. Active column added. All 16 clients set to Yes.")

add_active_column()
