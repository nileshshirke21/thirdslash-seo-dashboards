import pickle
import datetime
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import gspread

SHEET_ID = "1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"
GSC_PROPERTY = "https://public69.com/"
CLIENT_NAME = "Public69"

def get_credentials():
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def get_gsc_data(service, property_url, start_date, end_date):
    response = service.searchanalytics().query(
        siteUrl=property_url,
        body={
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['query'],
            'rowLimit': 50,
            'orderBy': [{'fieldName': 'clicks', 'sortOrder': 'DESCENDING'}]
        }
    ).execute()
    return response.get('rows', [])

def pull_and_write():
    creds = get_credentials()
    
    # GSC connection
    gsc_service = build('searchconsole', 'v1', credentials=creds)
    
    # Google Sheets connection
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    
    # Date ranges
    today = datetime.date.today()
    end_date = today.strftime('%Y-%m-%d')
    start_date = (today - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    prev_end = (today - datetime.timedelta(days=31)).strftime('%Y-%m-%d')
    prev_start = (today - datetime.timedelta(days=61)).strftime('%Y-%m-%d')
    
    print(f"Pulling GSC data for {CLIENT_NAME}...")
    print(f"Current period: {start_date} to {end_date}")
    
    # Pull current and previous period
    current_rows = get_gsc_data(gsc_service, GSC_PROPERTY, start_date, end_date)
    prev_rows = get_gsc_data(gsc_service, GSC_PROPERTY, prev_start, prev_end)
    
    # Build previous period lookup
    prev_data = {}
    for row in prev_rows:
        keyword = row['keys'][0]
        prev_data[keyword] = {
            'clicks': row.get('clicks', 0),
            'impressions': row.get('impressions', 0),
            'position': round(row.get('position', 0), 1)
        }
    
    # Try to get or create the GSC sheet tab
    try:
        worksheet = sh.worksheet(f"{CLIENT_NAME}_GSC")
        worksheet.clear()
    except:
        worksheet = sh.add_worksheet(
            title=f"{CLIENT_NAME}_GSC", rows=200, cols=12)
    
    # Headers
    headers = [
        "Date Pulled", "Client", "Keyword",
        "Clicks (Current)", "Clicks (Prev)", "Click Change",
        "Impressions (Current)", "Impressions (Prev)", "Impression Change",
        "CTR %", "Avg Position (Current)", "Position Change"
    ]
    worksheet.append_row(headers)
    
    # Data rows
    rows_to_write = []
    for row in current_rows:
        keyword = row['keys'][0]
        curr_clicks = row.get('clicks', 0)
        curr_impressions = row.get('impressions', 0)
        curr_ctr = round(row.get('ctr', 0) * 100, 2)
        curr_position = round(row.get('position', 0), 1)
        
        prev = prev_data.get(keyword, {})
        prev_clicks = prev.get('clicks', 0)
        prev_impressions = prev.get('impressions', 0)
        prev_position = prev.get('position', 0)
        
        click_change = curr_clicks - prev_clicks
        impression_change = curr_impressions - prev_impressions
        position_change = round(prev_position - curr_position, 1) if prev_position else 0
        
        rows_to_write.append([
            today.strftime('%d-%b-%Y'),
            CLIENT_NAME,
            keyword,
            curr_clicks,
            prev_clicks,
            click_change,
            curr_impressions,
            prev_impressions,
            impression_change,
            curr_ctr,
            curr_position,
            position_change
        ])
    
    if rows_to_write:
        worksheet.append_rows(rows_to_write)
    
    print(f"Done. {len(rows_to_write)} keywords written to Google Sheet.")
    print(f"Tab name: {CLIENT_NAME}_GSC")
    print(f"Open your sheet to verify: https://docs.google.com/spreadsheets/d/{SHEET_ID}")

pull_and_write()
