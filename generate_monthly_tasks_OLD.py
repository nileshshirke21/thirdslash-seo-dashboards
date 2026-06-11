"""
ThirdSlash SEO Automation
Script: generate_monthly_tasks.py
Purpose: Auto-generate monthly task rows for all 17 clients in 02_Monthly Task Tracker
Run on: 1st of every month
Command: python3 generate_monthly_tasks.py
         python3 generate_monthly_tasks.py --month "Jun-2026"
         python3 generate_monthly_tasks.py --client "Public69"
"""

import gspread, pickle, os, argparse
from datetime import datetime
from google.auth.transport.requests import Request

SHEET_ID   = "1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"
TOKEN_FILE = os.path.expanduser("~/ThirdSlash_SEO_Automation/token.pickle")

# ── STANDARD TASKS — all 17 clients every month ───────────────────────────────
STANDARD_TASKS = [
    # (Task Type, Sub-Task, Week, Dependency)
    ("Blog Topic Suggestion",  "Topic generated via automation",        "W1", ""),
    ("Blog Topic Suggestion",  "Team reviewed topics",                  "W1", ""),
    ("Blog Topic Suggestion",  "Topics sent to client",                 "W1", ""),
    ("Blog Topic Suggestion",  "Client approved topics",                "W1", ""),
    ("Blog Content Writing",   "Content brief created",                 "W1", "Blog Topic Suggestion"),
    ("Blog Content Writing",   "Draft written",                         "W1", "Blog Topic Suggestion"),
    ("Blog Content Writing",   "Internal review done",                  "W1", ""),
    ("Blog Content Writing",   "Sent to client for approval",           "W1", ""),
    ("Blog Content Writing",   "Client approved content",               "W2", ""),
    ("Blog Publishing",        "URL set",                               "W2", "Blog Content Writing"),
    ("Blog Publishing",        "Meta title and description added",      "W2", ""),
    ("Blog Publishing",        "Internal links added",                  "W2", ""),
    ("Blog Publishing",        "Published to platform",                 "W2", ""),
    ("Blog Publishing",        "Link confirmed live",                   "W2", ""),
    ("Blog SEO Optimization",  "Canonical tag set",                     "W2", "Blog Publishing"),
    ("Blog SEO Optimization",  "Schema markup added",                   "W2", ""),
    ("Blog SEO Optimization",  "Image alt tags updated",                "W2", ""),
    ("Blog SEO Optimization",  "Headers optimized",                     "W2", ""),
    ("Blog Indexing",          "URL submitted to GSC",                  "W2", "Blog Publishing"),
    ("Blog Indexing",          "Indexed confirmed",                     "W3", ""),
    ("On-Page Audit",          "Page selected",                         "W2", ""),
    ("On-Page Audit",          "57-point audit run",                    "W2", ""),
    ("On-Page Audit",          "Audit doc created",                     "W2", ""),
    ("On-Page Audit",          "Sent to client",                        "W2", ""),
    ("On-Page Audit",          "Client feedback received",              "W3", ""),
    ("On-Page Audit",          "Changes completed",                     "W3", ""),
    ("Citation Link Building", "Directories identified",                "W3", ""),
    ("Citation Link Building", "Submissions done",                      "W3", ""),
    ("Citation Link Building", "Live links verified",                   "W3", ""),
    ("Citation Link Building", "Added to backlink log",                 "W3", ""),
    ("Blog Commenting",        "10-15 blogs identified",                "W2", ""),
    ("Blog Commenting",        "Comments submitted",                    "W2", ""),
    ("Blog Commenting",        "Approvals tracked",                     "W3", ""),
    ("Blog Commenting",        "Live links logged",                     "W3", ""),
    ("Reddit Posting",         "Relevant threads found",                "W2", ""),
    ("Reddit Posting",         "5 comments posted",                     "W2", ""),
    ("Reddit Posting",         "Comments status checked",               "W3", ""),
    ("Quora Posting",          "Relevant questions found",              "W2", ""),
    ("Quora Posting",          "3 answers posted",                      "W2", ""),
    ("Rank Tracking Update",   "Ubersuggest pull run on 25th",          "W4", ""),
    ("Rank Tracking Update",   "Google Sheet rank tab updated",         "W4", ""),
    ("Rank Tracking Update",   "White-label PDF report generated",      "W4", ""),
    ("New Page Research",      "Keyword research done",                 "W1", ""),
    ("New Page Research",      "Search volumes checked",                "W1", ""),
    ("New Page Research",      "Page recommendation sent",              "W1", ""),
    ("New Page Research",      "Client approved",                       "W2", ""),
    ("GEO Page Suggestion",    "One GEO page suggestion prepared",      "W3", ""),
    ("GEO Page Suggestion",    "Sent to client for decision",           "W3", ""),
    ("Monthly Report",         "GA4 data pulled",                       "W4", ""),
    ("Monthly Report",         "GSC data pulled",                       "W4", ""),
    ("Monthly Report",         "Rank data added",                       "W4", ""),
    ("Monthly Report",         "Backlinks summarised",                  "W4", ""),
    ("Monthly Report",         "Tasks summarised",                      "W4", ""),
    ("Monthly Report",         "Report drafted",                        "W4", ""),
    ("Monthly Report",         "Nilesh reviewed",                       "W4", ""),
    ("Monthly Report",         "Sent to client",                        "W4", ""),
]

# ── GMB TASKS — conditional by GMB type ───────────────────────────────────────
GMB_TASKS_TYPE1_AUDIT = [
    # Only in odd months
    ("GMB Audit", "Check NAP consistency (Name Address Phone)",       "W1", ""),
    ("GMB Audit", "Check categories and business description",        "W1", ""),
    ("GMB Audit", "Check photos — min 5 fresh photos",               "W1", ""),
    ("GMB Audit", "Check Q&A — answer unanswered questions",         "W1", ""),
    ("GMB Audit", "Flag Google-suggested edits to client",           "W1", ""),
]

GMB_TASKS_TYPE1_MONTHLY = [
    ("GMB Post - Offer",    "Send image/creative request to client",      "W1", ""),
    ("GMB Post - Blog",     "Blog goes live — create GMB post with link", "W2", "Blog Publishing"),
    ("GMB Post - Blog",     "Write 150-word post copy with blog link",    "W2", ""),
    ("GMB Post - Blog",     "Publish GMB post and confirm live",          "W2", ""),
    ("GMB Post - Offer",    "Write offer/general post copy",              "W3", ""),
    ("GMB Post - Offer",    "Publish offer post once image received",     "W3", ""),
    ("GMB Post - Offer",    "Confirm offer post is live",                 "W3", ""),
    ("GMB Review Tracker",  "Count current total reviews on GMB",         "W4", ""),
    ("GMB Review Tracker",  "Compare with last month count in sheet",     "W4", ""),
    ("GMB Review Tracker",  "Calculate new reviews this month",           "W4", ""),
    ("GMB Review Tracker",  "Send update to client + nudge for more",     "W4", ""),
    ("GMB Review Tracker",  "Update Last Month GMB Reviews in sheet",     "W4", ""),
]

GMB_TASKS_TYPE2 = [
    ("GMB Post - Blog",    "Blog goes live — create GMB post with link",  "W2", "Blog Publishing"),
    ("GMB Post - Blog",    "Write post copy with blog link",              "W2", ""),
    ("GMB Post - Blog",    "Publish GMB post and confirm live",           "W2", ""),
    ("GMB City Citation",  "Update GMB description with city keyword",    "W2", ""),
    ("GMB Review Tracker", "Count current total reviews on GMB",          "W4", ""),
    ("GMB Review Tracker", "Compare with last month count in sheet",      "W4", ""),
    ("GMB Review Tracker", "Send update to client + nudge for more",      "W4", ""),
    ("GMB Review Tracker", "Update Last Month GMB Reviews in sheet",      "W4", ""),
]

GMB_TASKS_TYPE3 = [
    ("GMB Review Tracker", "Count current total reviews on GMB",          "W4", ""),
    ("GMB Review Tracker", "Compare with last month count in sheet",      "W4", ""),
    ("GMB Review Tracker", "Send ORM review report to client",            "W4", ""),
    ("GMB Review Tracker", "Update Last Month GMB Reviews in sheet",      "W4", ""),
]

def is_odd_month(month_str):
    try:
        dt = datetime.strptime(month_str, "%b-%Y")
        return dt.month % 2 != 0
    except:
        return True

def get_gmb_tasks(gmb_type, month_str):
    tasks = []
    if gmb_type == "Type 1":
        if is_odd_month(month_str):
            tasks.extend(GMB_TASKS_TYPE1_AUDIT)
        tasks.extend(GMB_TASKS_TYPE1_MONTHLY)
    elif gmb_type == "Type 2":
        tasks.extend(GMB_TASKS_TYPE2)
    elif gmb_type == "Type 3":
        tasks.extend(GMB_TASKS_TYPE3)
    return tasks

def build_task_rows(client_name, team_member, month_str, gmb_type, platforms):
    rows = []
    has_reddit = "Reddit" in platforms
    has_quora  = "Quora"  in platforms
    has_medium = "Medium" in platforms

    for task_type, subtask, week, dep in STANDARD_TASKS:
        # Skip platform tasks if client doesn't use them
        if task_type == "Reddit Posting" and not has_reddit: continue
        if task_type == "Quora Posting"  and not has_quora:  continue

        rows.append([
            month_str, week, client_name, task_type, subtask,
            team_member, "Not Started", "", "", "",
            "No", "No", "", dep, "No", "No", "", ""
        ])

    # Add GMB tasks
    for task_type, subtask, week, dep in get_gmb_tasks(gmb_type, month_str):
        rows.append([
            month_str, week, client_name, task_type, subtask,
            team_member, "Not Started", "", "", "",
            "No", "No", "", dep, "No", "No", "", ""
        ])

    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month",  default=datetime.now().strftime("%b-%Y"))
    parser.add_argument("--client", default=None)
    args = parser.parse_args()

    month_str  = args.month
    odd_month  = is_odd_month(month_str)

    print("ThirdSlash — Monthly Task Generator")
    print("=" * 40)
    print(f"Month  : {month_str}")
    print(f"GMB Audit this month: {'YES (odd month)' if odd_month else 'NO (even month)'}")

    with open(TOKEN_FILE, "rb") as f: creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "wb") as f: pickle.dump(creds, f)

    gc    = gspread.authorize(creds)
    sheet = gc.open_by_key(SHEET_ID)

    # Read client profile
    ws_profile = sheet.worksheet("01_Client Profile")
    clients    = ws_profile.get_all_records(head=3)

    if args.client:
        clients = [c for c in clients if c.get("Client Name","").strip().lower() == args.client.lower()]
        if not clients:
            print(f"Client '{args.client}' not found.")
            return

    ws_tasks  = sheet.worksheet("02_Monthly Task Tracker")
    all_rows  = []
    summary   = []

    for client in clients:
        name = client.get("Client Name","").strip()
        if not name or client.get("Active","").strip() != "Yes": continue

        team      = client.get("Assigned Team Member","").strip()
        gmb_type  = client.get("GMB Type","None").strip()
        platforms = client.get("Platforms (Reddit/Quora/Medium)","").strip()

        rows = build_task_rows(name, team, month_str, gmb_type, platforms)
        all_rows.extend(rows)
        summary.append((name, len(rows), gmb_type))
        print(f"  ✓ {name:25} {len(rows):3} tasks | GMB: {gmb_type}")

    # Append to sheet
    existing   = ws_tasks.get_all_values()
    start_row  = len(existing) + 1
    ws_tasks.update(range_name=f"A{start_row}", values=all_rows)

    print(f"\n{'='*40}")
    print(f"DONE — {month_str}")
    print(f"  Total clients : {len(summary)}")
    print(f"  Total rows    : {len(all_rows)}")
    print(f"  GMB audit     : {'Yes' if odd_month else 'No (even month)'}")
    print(f"\nSheet: https://docs.google.com/spreadsheets/d/{SHEET_ID}")

if __name__ == "__main__":
    main()
