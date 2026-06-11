import pickle
import datetime
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension
from google.auth.transport.requests import Request
import gspread

SHEET_ID = "1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"
GA4_PROPERTY_ID = "490335292"
CLIENT_NAME = "Public69"

def get_credentials():
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def pull_and_write():
    creds = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)

    today = datetime.date.today()
    date_label = today.strftime('%d-%b-%Y')

    # ── Summary metrics ──────────────────────────────────────
    def get_summary(start, end):
        req = RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[DateRange(start_date=start, end_date=end)],
            metrics=[
                Metric(name="sessions"),
                Metric(name="activeUsers"),
                Metric(name="screenPageViews"),
                Metric(name="bounceRate"),
                Metric(name="averageSessionDuration")
            ]
        )
        r = client.run_report(req)
        row = r.rows[0].metric_values
        return {
            "sessions":   int(row[0].value),
            "users":      int(row[1].value),
            "pageviews":  int(row[2].value),
            "bounce":     round(float(row[3].value) * 100, 2),
            "duration":   round(float(row[4].value), 0)
        }

    curr = get_summary("30daysAgo", "today")
    prev = get_summary("60daysAgo", "31daysAgo")

    def change(c, p):
        return c - p

    # ── Top 20 pages ─────────────────────────────────────────
    page_req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
            Metric(name="screenPageViews")
        ],
        limit=20
    )
    page_resp = client.run_report(page_req)

    # ── Top 10 traffic sources ────────────────────────────────
    source_req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers")
        ],
        limit=10
    )
    source_resp = client.run_report(source_req)

    # ── Write to Google Sheet ─────────────────────────────────
    try:
        ws = sh.worksheet(f"{CLIENT_NAME}_GA4")
        ws.clear()
    except:
        ws = sh.add_worksheet(title=f"{CLIENT_NAME}_GA4", rows=200, cols=15)

    # Summary section
    ws.append_row(["SUMMARY METRICS", "", "Current (30 days)", "Previous (30 days)", "Change"])
    ws.append_row(["Date Pulled", "", date_label, "", ""])
    ws.append_row(["Client", "", CLIENT_NAME, "", ""])
    ws.append_row(["", "", "", "", ""])
    ws.append_row(["Sessions", "", curr["sessions"], prev["sessions"], change(curr["sessions"], prev["sessions"])])
    ws.append_row(["Users", "", curr["users"], prev["users"], change(curr["users"], prev["users"])])
    ws.append_row(["Pageviews", "", curr["pageviews"], prev["pageviews"], change(curr["pageviews"], prev["pageviews"])])
    ws.append_row(["Bounce Rate %", "", curr["bounce"], prev["bounce"], round(curr["bounce"] - prev["bounce"], 2)])
    ws.append_row(["Avg Session Duration (sec)", "", curr["duration"], prev["duration"], change(curr["duration"], prev["duration"])])
    ws.append_row(["", "", "", "", ""])

    # Top pages section
    ws.append_row(["TOP 20 PAGES (Last 30 Days)", "", "", "", ""])
    ws.append_row(["Page Path", "", "Sessions", "Users", "Pageviews"])
    for row in page_resp.rows:
        ws.append_row([
            row.dimension_values[0].value,
            "",
            int(row.metric_values[0].value),
            int(row.metric_values[1].value),
            int(row.metric_values[2].value)
        ])

    ws.append_row(["", "", "", "", ""])

    # Traffic sources section
    ws.append_row(["TRAFFIC SOURCES (Last 30 Days)", "", "", "", ""])
    ws.append_row(["Channel", "", "Sessions", "Users", ""])
    for row in source_resp.rows:
        ws.append_row([
            row.dimension_values[0].value,
            "",
            int(row.metric_values[0].value),
            int(row.metric_values[1].value),
            ""
        ])

    print(f"Done. GA4 data written to Google Sheet.")
    print(f"Tab name: {CLIENT_NAME}_GA4")
    print(f"Sessions this month: {curr['sessions']:,}")
    print(f"Users this month:    {curr['users']:,}")
    print(f"Pageviews this month: {curr['pageviews']:,}")

pull_and_write()
