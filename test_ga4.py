from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension
import pickle

def get_credentials():
    with open('token.pickle', 'rb') as token:
        return pickle.load(token)

def test_ga4(property_id):
    creds = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
            Metric(name="screenPageViews")
        ],
        dimensions=[Dimension(name="date")]
    )
    response = client.run_report(request)
    total_sessions = sum(int(row.metric_values[0].value) for row in response.rows)
    total_users = sum(int(row.metric_values[1].value) for row in response.rows)
    total_pageviews = sum(int(row.metric_values[2].value) for row in response.rows)
    print(f"\n--- GA4 DATA (Last 30 Days) ---")
    print(f"Total Sessions:   {total_sessions:,}")
    print(f"Total Users:      {total_users:,}")
    print(f"Total Pageviews:  {total_pageviews:,}")
    print("-------------------------------\n")

test_ga4("490335292")
