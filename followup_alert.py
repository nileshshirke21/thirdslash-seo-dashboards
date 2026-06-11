import pickle
import datetime
import base64
import gspread
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SHEET_ID = "1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"
ALERT_TO = "nilesh@thirdslash.com"
ALERT_FROM = "nilesh@thirdslash.com"

def get_credentials():
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def send_email(service, to, from_email, subject, html_body):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to
    msg.attach(MIMEText(html_body, 'html'))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(
        userId='me', body={'raw': raw}).execute()

def check_followups():
    creds = get_credentials()
    gc = gspread.authorize(creds)
    gmail = build('gmail', 'v1', credentials=creds)
    sh = gc.open_by_key(SHEET_ID)

    delivery_ws = sh.worksheet("03_Delivery Log")
    all_data = delivery_ws.get_all_values()

    if len(all_data) < 4:
        print("No delivery log data found.")
        return

    headers = all_data[2]
    rows = all_data[3:]

    today = datetime.date.today()

    overdue_followups = []
    no_response_old = []
    pending_approvals = []

    for row in rows:
        if not any(row):
            continue
        padded = row + [''] * (len(headers) - len(row))
        r = dict(zip(headers, padded))

        date_sent_str = r.get("Date Sent", "").strip()
        client = r.get("Client Name", "").strip()
        deliverable = r.get("Deliverable Type", "").strip()
        response = r.get("Client Response", "").strip()
        followup_req = r.get("Follow-Up Required", "").strip()
        followup_done = r.get("Follow-Up Done", "").strip()
        followup_date_str = r.get("Follow-Up Date", "").strip()

        if not client:
            continue

        # Parse date sent
        date_sent = None
        for fmt in ['%d-%b-%Y', '%d/%m/%Y', '%Y-%m-%d']:
            try:
                date_sent = datetime.datetime.strptime(date_sent_str, fmt).date()
                break
            except:
                continue

        # Check overdue follow-ups
        if followup_req == "Yes" and followup_done == "No":
            followup_date = None
            if followup_date_str:
                for fmt in ['%d-%b-%Y', '%d/%m/%Y', '%Y-%m-%d']:
                    try:
                        followup_date = datetime.datetime.strptime(
                            followup_date_str, fmt).date()
                        break
                    except:
                        continue
            if followup_date and followup_date <= today:
                days_overdue = (today - followup_date).days
                overdue_followups.append({
                    "client": client,
                    "deliverable": deliverable,
                    "followup_date": followup_date_str,
                    "days_overdue": days_overdue
                })

        # Check no response older than 7 days
        if response == "No Response" and date_sent:
            days_waiting = (today - date_sent).days
            if days_waiting >= 7:
                no_response_old.append({
                    "client": client,
                    "deliverable": deliverable,
                    "date_sent": date_sent_str,
                    "days_waiting": days_waiting
                })

        # Check pending approvals
        if response in ["", "No Response"] and date_sent:
            days_waiting = (today - date_sent).days
            if days_waiting >= 3 and response != "Approved":
                pending_approvals.append({
                    "client": client,
                    "deliverable": deliverable,
                    "date_sent": date_sent_str,
                    "days_waiting": days_waiting
                })

    # Build email
    total_actions = len(overdue_followups) + len(no_response_old)

    if total_actions == 0:
        print("No follow-ups needed today. All clear.")
        return

    html = f"""
    <html><body style="font-family: Arial, sans-serif; color: #212529;">
    <div style="background:#1A1A2E; padding:20px; border-radius:8px; margin-bottom:20px;">
        <h1 style="color:white; margin:0; font-size:20px;">
            ThirdSlash | Weekly Follow-Up Alert
        </h1>
        <p style="color:#AAAAAA; margin:5px 0 0 0; font-size:13px;">
            {today.strftime('%A, %d %B %Y')} — {total_actions} items need your attention
        </p>
    </div>
    """

    if overdue_followups:
        html += f"""
        <h2 style="color:#E94560; font-size:16px;">
            🔴 Overdue Follow-Ups ({len(overdue_followups)})
        </h2>
        <table style="width:100%; border-collapse:collapse; margin-bottom:20px;">
            <tr style="background:#0F3460; color:white;">
                <th style="padding:8px; text-align:left;">Client</th>
                <th style="padding:8px; text-align:left;">Deliverable</th>
                <th style="padding:8px; text-align:left;">Due Date</th>
                <th style="padding:8px; text-align:left;">Days Overdue</th>
            </tr>
        """
        for i, item in enumerate(overdue_followups):
            bg = "#fff" if i % 2 == 0 else "#F0F4FF"
            html += f"""
            <tr style="background:{bg};">
                <td style="padding:8px; border-bottom:1px solid #dee2e6;">
                    <b>{item['client']}</b></td>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;">
                    {item['deliverable']}</td>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;">
                    {item['followup_date']}</td>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;
                    color:#E94560; font-weight:bold;">
                    {item['days_overdue']} days</td>
            </tr>
            """
        html += "</table>"

    if no_response_old:
        html += f"""
        <h2 style="color:#856404; font-size:16px;">
            🟡 No Response — 7+ Days ({len(no_response_old)})
        </h2>
        <table style="width:100%; border-collapse:collapse; margin-bottom:20px;">
            <tr style="background:#0F3460; color:white;">
                <th style="padding:8px; text-align:left;">Client</th>
                <th style="padding:8px; text-align:left;">Deliverable</th>
                <th style="padding:8px; text-align:left;">Sent Date</th>
                <th style="padding:8px; text-align:left;">Days Waiting</th>
            </tr>
        """
        for i, item in enumerate(no_response_old):
            bg = "#fff" if i % 2 == 0 else "#FFF3CD"
            html += f"""
            <tr style="background:{bg};">
                <td style="padding:8px; border-bottom:1px solid #dee2e6;">
                    <b>{item['client']}</b></td>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;">
                    {item['deliverable']}</td>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;">
                    {item['date_sent']}</td>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;
                    color:#856404; font-weight:bold;">
                    {item['days_waiting']} days</td>
            </tr>
            """
        html += "</table>"

    html += f"""
    <div style="background:#F0F4FF; padding:15px; border-radius:8px;
        border-left:4px solid #0F3460; margin-top:20px;">
        <p style="margin:0; font-size:13px; color:#495057;">
            <b>Open your tracker:</b>
            <a href="https://docs.google.com/spreadsheets/d/{SHEET_ID}">
                ThirdSlash SEO Operations Tracker
            </a>
        </p>
    </div>
    </body></html>
    """

    subject = f"ThirdSlash Follow-Up Alert — {total_actions} items need attention ({today.strftime('%d %b %Y')})"
    send_email(gmail, ALERT_TO, ALERT_FROM, subject, html)
    print(f"Alert email sent to {ALERT_TO}")
    print(f"Total items: {total_actions}")
    print(f"Overdue follow-ups: {len(overdue_followups)}")
    print(f"No response 7+ days: {len(no_response_old)}")

check_followups()
