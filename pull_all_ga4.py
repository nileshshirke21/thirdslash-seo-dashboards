import pickle, os, argparse
from datetime import datetime, timedelta
import gspread
from google.auth.transport.requests import Request
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric,
    FilterExpression, Filter, FilterExpressionList
)

SHEET_ID        = "1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"
BASE            = os.path.dirname(os.path.abspath(__file__))
TOKEN_SHEETS    = os.path.join(BASE,"token.pickle")
TOKEN_CONNECT   = os.path.join(BASE,"token_ga4.pickle")
TOKEN_REPORTING = os.path.join(BASE,"token_reporting.pickle")
TAB_NAME        = "All_GA4"
TODAY           = datetime.now().strftime("%d-%b-%Y")

def get_dates():
    t=datetime.now(); fc=t.replace(day=1); lp=fc-timedelta(days=1); fp=lp.replace(day=1)
    lp2=fp-timedelta(days=1); fp2=lp2.replace(day=1)
    return fp.strftime("%Y-%m-%d"),lp.strftime("%Y-%m-%d"),fp2.strftime("%Y-%m-%d"),lp2.strftime("%Y-%m-%d"),lp.strftime("%b-%Y")

START,END,PS,PE,MONTH=get_dates()

# Client-specific form submission event names
# Add more as you confirm them per client
FORM_EVENTS = {
    "Public69":           ["form_submit"],
    "Estrela Hotels":     ["form_submit"],
    "HRM Thread":         ["Form_Submit","Contact_Form_Submission_GA4"],
    "Potential Engineering": ["Request_a_Quote_GA4","request_a_quote"],
    "Ovation Square":     ["form submission"],
    "DEFAULT":            ["form_submit","form_submission","contact_form","Form_Submit","generate_lead","submit_form"],
}

CLIENTS=[
    ("Asset Thread",         "337422347",  "reporting"),
    ("HRM Thread",           "336102064",  "connect"),
    ("Lancers CBSE",         "417031127",  "connect"),
    ("Lancers GSEB",         "417132217",  "connect"),
    ("Lancers Early Years",  "417129053",  "connect"),
    ("Lancers Army School",  "372677541",  "connect"),
    ("Potential Engineering","373268290",  "connect"),
    ("EZ Lifestyle",         "393773790",  "reporting"),
    ("Estrela Hotels",       "428312837",  "reporting"),
    ("Kelly Powers",         "372454798",  "connect"),
    ("HappyLyfe",            "289135634",  "reporting"),
    ("Public69",             "490335292",  "reporting"),
    ("Ovation Square",       "373027726",  "connect"),
    ("Piovra Group",         "373032768",  "connect"),
    ("Brickroom LA",         "352919523",  "connect"),
    ("MJ Gorgeous",          "373268535",  "connect"),
]

HEADER=["Date Pulled","Month","Client Name",
    "Sessions (Current)","Sessions (Prev)","Sessions Change",
    "Users (Current)","Users (Prev)","Users Change",
    "Pageviews (Current)","Pageviews (Prev)","Pageviews Change",
    "Bounce Rate %","Avg Session Duration (sec)",
    "Organic Sessions","Direct Sessions","Referral Sessions",
    "ChatGPT Sessions","Claude Sessions","Perplexity Sessions","Gemini Sessions",
    "Form Submissions"]

AI_SOURCES={"ChatGPT":"chatgpt.com","Claude":"claude.ai","Perplexity":"perplexity.ai","Gemini":"gemini.google.com"}

def load_creds(f):
    with open(f,"rb") as fh: creds=pickle.load(fh)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(f,"wb") as fh: pickle.dump(creds,fh)
    return creds

def pull_form_submissions(client, pid, creds, name):
    events = FORM_EVENTS.get(name, FORM_EVENTS["DEFAULT"])
    total = 0
    for event in events:
        try:
            r = client.run_report(RunReportRequest(
                property=f"properties/{pid}",
                date_ranges=[DateRange(start_date=START, end_date=END)],
                dimensions=[Dimension(name="eventName")],
                metrics=[Metric(name="eventCount")],
                dimension_filter=FilterExpression(filter=Filter(
                    field_name="eventName",
                    string_filter=Filter.StringFilter(
                        match_type=Filter.StringFilter.MatchType.EXACT,
                        value=event
                    )
                )), limit=1
            ))
            if r.rows:
                total += int(r.rows[0].metric_values[0].value or 0)
        except: pass
    return total

def pull_ga4(pid, creds, name):
    c = BetaAnalyticsDataClient(credentials=creds)
    r = c.run_report(RunReportRequest(
        property=f"properties/{pid}",
        date_ranges=[DateRange(start_date=START,end_date=END),DateRange(start_date=PS,end_date=PE)],
        metrics=[Metric(name="sessions"),Metric(name="activeUsers"),Metric(name="screenPageViews"),Metric(name="bounceRate"),Metric(name="averageSessionDuration")]
    ))
    def v(row,i): return float(row.metric_values[i].value or 0)
    cr=r.rows[0] if r.rows else None; pr=r.rows[1] if len(r.rows)>1 else None
    cs=int(v(cr,0)) if cr else 0; cu=int(v(cr,1)) if cr else 0
    cp=int(v(cr,2)) if cr else 0; cb=round(v(cr,3)*100,2) if cr else 0
    cd=int(v(cr,4)) if cr else 0
    ps=int(v(pr,0)) if pr else 0; pu=int(v(pr,1)) if pr else 0; pp=int(v(pr,2)) if pr else 0

    src=c.run_report(RunReportRequest(
        property=f"properties/{pid}",
        date_ranges=[DateRange(start_date=START,end_date=END)],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")],limit=20
    ))
    og=di=re=0
    for row in src.rows:
        ch=row.dimension_values[0].value; s=int(row.metric_values[0].value or 0)
        if "Organic" in ch: og+=s
        elif "Direct" in ch: di+=s
        elif "Referral" in ch: re+=s

    ai={}
    for aname,domain in AI_SOURCES.items():
        try:
            ar=c.run_report(RunReportRequest(
                property=f"properties/{pid}",
                date_ranges=[DateRange(start_date=START,end_date=END)],
                dimensions=[Dimension(name="sessionSource")],
                metrics=[Metric(name="sessions")],
                dimension_filter=FilterExpression(filter=Filter(
                    field_name="sessionSource",
                    string_filter=Filter.StringFilter(match_type=Filter.StringFilter.MatchType.CONTAINS,value=domain)
                )),limit=10
            ))
            ai[aname]=sum(int(rr.metric_values[0].value or 0) for rr in ar.rows)
        except: ai[aname]=0

    forms = pull_form_submissions(c, pid, creds, name)

    return [TODAY,MONTH,"",cs,ps,cs-ps,cu,pu,cu-pu,cp,pp,cp-pp,cb,cd,
            og,di,re,ai["ChatGPT"],ai["Claude"],ai["Perplexity"],ai["Gemini"],forms]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--client",default=None)
    args=parser.parse_args()
    print(f"ThirdSlash — GA4 Puller\n{'='*45}")
    print(f"Period : {START} to {END} ({MONTH})\n")
    cm={"connect":load_creds(TOKEN_CONNECT),"reporting":load_creds(TOKEN_REPORTING)}
    gc=gspread.authorize(load_creds(TOKEN_SHEETS))
    sheet=gc.open_by_key(SHEET_ID)
    try: ws=sheet.worksheet(TAB_NAME)
    except: ws=sheet.add_worksheet(title=TAB_NAME,rows=500,cols=23)
    targets=CLIENTS
    if args.client: targets=[(n,p,t) for n,p,t in CLIENTS if n.lower()==args.client.lower()]
    rows=[]
    for name,pid,tk in targets:
        print(f"  {name:25}...",end=" ",flush=True)
        try:
            row=pull_ga4(pid,cm[tk],name); row[2]=name; rows.append(row)
            print(f"✓ S:{row[3]:,} Org:{row[14]:,} GPT:{row[17]} Forms:{row[21]}")
        except Exception as e: print(f"✗ {str(e)[:70]}")
    if rows:
        all_vals=ws.get_all_values()
        kept=[r for r in all_vals[1:] if r and len(r)>1 and r[1]!=MONTH]
        ws.clear(); ws.update(range_name="A1",values=[HEADER]+kept+rows)
        print(f"\nDone — {len(rows)} clients written for {MONTH}")
    print(f"Sheet: https://docs.google.com/spreadsheets/d/{SHEET_ID}")

if __name__=="__main__": main()
