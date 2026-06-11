"""
ThirdSlash SEO Automation
Script: backfill_ga4_gsc.py
Purpose: Pull 16 months of GA4 + GSC data for all 16 clients
Range: Feb 2025 to May 2026
Run: python3 backfill_ga4_gsc.py
     python3 backfill_ga4_gsc.py --source ga4
     python3 backfill_ga4_gsc.py --source gsc
     python3 backfill_ga4_gsc.py --client "Public69"
"""

import pickle, os, argparse, time, calendar
from datetime import datetime, timedelta
import gspread
from google.auth.transport.requests import Request
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric,
    FilterExpression, Filter
)
from googleapiclient.discovery import build

SHEET_ID        = "1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"
BASE            = os.path.expanduser("~/ThirdSlash_SEO_Automation")
TOKEN_SHEETS    = os.path.join(BASE,"token.pickle")
TOKEN_CONNECT   = os.path.join(BASE,"token_ga4.pickle")
TOKEN_REPORTING = os.path.join(BASE,"token_reporting.pickle")
TODAY           = datetime.now().strftime("%d-%b-%Y")

# Generate 16 months: Feb 2025 to May 2026
def get_months():
    today = datetime.now()
    first_current = today.replace(day=1)
    last_month_end = first_current - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    months = []
    for i in range(15, -1, -1):
        m = last_month_start
        for _ in range(i):
            m = (m.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day = calendar.monthrange(m.year, m.month)[1]
        prev_end = m - timedelta(days=1)
        prev_start = prev_end.replace(day=1)
        months.append({
            "label":      m.strftime("%b-%Y"),
            "start":      m.strftime("%Y-%m-%d"),
            "end":        datetime(m.year, m.month, last_day).strftime("%Y-%m-%d"),
            "prev_start": prev_start.strftime("%Y-%m-%d"),
            "prev_end":   prev_end.strftime("%Y-%m-%d"),
        })
    return months

MONTHS = get_months()

GA4_CLIENTS = [
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

GSC_CLIENTS = [
    ("Asset Thread",        "https://assetthread.com/",          "connect"),
    ("HRM Thread",          "https://www.hrmthread.com/",        "connect"),
    ("Lancers CBSE",        "https://lancerscbse.com/",          "connect"),
    ("Lancers GSEB",        "https://lancersgseb.com/",          "connect"),
    ("Lancers Early Years", "https://lancersearlyyears.com/",    "connect"),
    ("Lancers Army School", "https://lancersarmyschools.com/",   "connect"),
    ("Potential Engineering","https://potentialengineering.com/","connect"),
    ("EZ Lifestyle",        "https://ez-lifestyle.com/",         "connect"),
    ("Estrela Hotels",      "https://www.estrelahotels.com/",    "reporting"),
    ("Kelly Powers",        "https://www.kellyepowers.com/",     "connect"),
    ("HappyLyfe",           "https://happylyfe.in.th/",          "reporting"),
    ("Public69",            "sc-domain:public69.com",            "reporting"),
    ("Ovation Square",      "https://www.ovationsquare.com/",    "connect"),
    ("Piovra Group",        "https://www.piovragroup.com/",      "connect"),
    ("Brickroom LA",        "https://brickroomla.com/",          "connect"),
    ("MJ Gorgeous",         "https://mjgorgeous.com/",           "connect"),
]

GA4_HEADER = [
    "Date Pulled","Month","Client Name",
    "Sessions (Current)","Sessions (Prev)","Sessions Change",
    "Users (Current)","Users (Prev)","Users Change",
    "Pageviews (Current)","Pageviews (Prev)","Pageviews Change",
    "Bounce Rate %","Avg Session Duration (sec)",
    "Organic Sessions","Direct Sessions","Referral Sessions",
    "ChatGPT Sessions","Claude Sessions","Perplexity Sessions","Gemini Sessions"
]

GSC_HEADER = [
    "Date Pulled","Month","Client Name",
    "Clicks (Current)","Clicks (Prev)","Clicks Change",
    "Impressions (Current)","Impressions (Prev)","Impressions Change",
    "CTR % (Current)","Avg Position (Current)","Avg Position (Prev)",
    "Position Change","Top Keyword","Top Keyword Clicks"
]

AI_SOURCES = {
    "ChatGPT":    "chatgpt.com",
    "Claude":     "claude.ai",
    "Perplexity": "perplexity.ai",
    "Gemini":     "gemini.google.com",
}

def load_creds(f):
    with open(f,"rb") as fh: creds=pickle.load(fh)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(f,"wb") as fh: pickle.dump(creds,fh)
    return creds

def pull_ga4_month(pid, creds, m):
    client = BetaAnalyticsDataClient(credentials=creds)
    resp = client.run_report(RunReportRequest(
        property=f"properties/{pid}",
        date_ranges=[
            DateRange(start_date=m["start"], end_date=m["end"]),
            DateRange(start_date=m["prev_start"], end_date=m["prev_end"]),
        ],
        metrics=[
            Metric(name="sessions"), Metric(name="activeUsers"),
            Metric(name="screenPageViews"), Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
        ]
    ))
    def v(row,i): return float(row.metric_values[i].value or 0)
    c=resp.rows[0] if resp.rows else None
    p=resp.rows[1] if len(resp.rows)>1 else None
    cs=int(v(c,0)) if c else 0; cu=int(v(c,1)) if c else 0
    cp=int(v(c,2)) if c else 0; cb=round(v(c,3)*100,2) if c else 0
    cd=int(v(c,4)) if c else 0
    ps=int(v(p,0)) if p else 0; pu=int(v(p,1)) if p else 0
    pp=int(v(p,2)) if p else 0

    src = client.run_report(RunReportRequest(
        property=f"properties/{pid}",
        date_ranges=[DateRange(start_date=m["start"],end_date=m["end"])],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")], limit=20
    ))
    og=di=re=0
    for row in src.rows:
        ch=row.dimension_values[0].value; s=int(row.metric_values[0].value or 0)
        if "Organic" in ch: og+=s
        elif "Direct" in ch: di+=s
        elif "Referral" in ch: re+=s

    ai={}
    for aname, domain in AI_SOURCES.items():
        try:
            ar=client.run_report(RunReportRequest(
                property=f"properties/{pid}",
                date_ranges=[DateRange(start_date=m["start"],end_date=m["end"])],
                dimensions=[Dimension(name="sessionSource")],
                metrics=[Metric(name="sessions")],
                dimension_filter=FilterExpression(filter=Filter(
                    field_name="sessionSource",
                    string_filter=Filter.StringFilter(
                        match_type=Filter.StringFilter.MatchType.CONTAINS,
                        value=domain
                    )
                )), limit=10
            ))
            ai[aname]=sum(int(r.metric_values[0].value or 0) for r in ar.rows)
        except: ai[aname]=0

    return [TODAY,m["label"],"",cs,ps,cs-ps,cu,pu,cu-pu,cp,pp,cp-pp,cb,cd,
            og,di,re,ai["ChatGPT"],ai["Claude"],ai["Perplexity"],ai["Gemini"]]

def pull_gsc_month(url, creds, m):
    svc=build("searchconsole","v1",credentials=creds)
    def query(s,e):
        return svc.searchanalytics().query(
            siteUrl=url,
            body={"startDate":s,"endDate":e,"dimensions":["query"],"rowLimit":25}
        ).execute()
    cr=query(m["start"],m["end"]); pr=query(m["prev_start"],m["prev_end"])
    def totals(r):
        rows=r.get("rows",[])
        if not rows: return 0,0,0,0
        cl=sum(x.get("clicks",0) for x in rows)
        im=sum(x.get("impressions",0) for x in rows)
        ap=round(sum(x.get("position",0)*x.get("impressions",0) for x in rows)/im,1) if im else 0
        ct=round(cl/im*100,2) if im else 0
        return cl,im,ap,ct
    cc,ci,cp,ctr=totals(cr); pc,pi,pp,_=totals(pr)
    top_kw=""; top_cl=0
    if cr.get("rows"):
        top=sorted(cr["rows"],key=lambda x:x.get("clicks",0),reverse=True)[0]
        top_kw=top.get("keys",[""])[0]; top_cl=top.get("clicks",0)
    return [TODAY,m["label"],"",cc,pc,cc-pc,ci,pi,ci-pi,ctr,cp,pp,round(pp-cp,1),top_kw,top_cl]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",default="both",choices=["ga4","gsc","both"])
    parser.add_argument("--client",default=None)
    args=parser.parse_args()

    print("ThirdSlash — 16-Month Backfill")
    print("="*50)
    print(f"Range  : {MONTHS[0]['label']} → {MONTHS[-1]['label']} ({len(MONTHS)} months)")
    print(f"Source : {args.source}")
    print(f"Clients: {len(GA4_CLIENTS)} active")
    print()

    cm={
        "connect":   load_creds(TOKEN_CONNECT),
        "reporting": load_creds(TOKEN_REPORTING),
    }
    gc    = gspread.authorize(load_creds(TOKEN_SHEETS))
    sheet = gc.open_by_key(SHEET_ID)

    # ── GA4 ───────────────────────────────────────────────────────────────────
    if args.source in ("ga4","both"):
        print("── GA4 Backfill ──")
        try: ws_ga4=sheet.worksheet("All_GA4")
        except: ws_ga4=sheet.add_worksheet(title="All_GA4",rows=1000,cols=22)

        ga4_targets=GA4_CLIENTS
        if args.client:
            ga4_targets=[(n,p,t) for n,p,t in GA4_CLIENTS if n.lower()==args.client.lower()]

        target_months={m["label"] for m in MONTHS}
        target_names={n for n,p,t in ga4_targets}
        existing=ws_ga4.get_all_values()
        kept=[r for r in existing[1:] if r and len(r)>2
              and not(r[1] in target_months and r[2] in target_names)]

        new_rows=[]
        total=len(MONTHS)*len(ga4_targets)
        done=0
        for m in MONTHS:
            print(f"\n  {m['label']}")
            for name,pid,tk in ga4_targets:
                print(f"    {name:25}...",end=" ",flush=True)
                try:
                    row=pull_ga4_month(pid,cm[tk],m)
                    row[2]=name; new_rows.append(row)
                    print(f"✓ S:{row[3]:,} Org:{row[14]:,} GPT:{row[17]} Cld:{row[18]}")
                except Exception as e:
                    print(f"✗ {str(e)[:45]}")
                done+=1
                time.sleep(0.5)
            # Batch write every month to avoid data loss
            if new_rows:
                ws_ga4.clear()
                ws_ga4.update(range_name="A1",values=[GA4_HEADER]+kept+new_rows)

        print(f"\n  GA4 complete — {len(new_rows)}/{total} rows written")

    # ── GSC ───────────────────────────────────────────────────────────────────
    if args.source in ("gsc","both"):
        print("\n── GSC Backfill ──")
        try: ws_gsc=sheet.worksheet("All_GSC")
        except: ws_gsc=sheet.add_worksheet(title="All_GSC",rows=1000,cols=16)

        gsc_targets=GSC_CLIENTS
        if args.client:
            gsc_targets=[(n,p,t) for n,p,t in GSC_CLIENTS if n.lower()==args.client.lower()]

        target_months={m["label"] for m in MONTHS}
        target_names={n for n,p,t in gsc_targets}
        existing=ws_gsc.get_all_values()
        kept=[r for r in existing[1:] if r and len(r)>2
              and not(r[1] in target_months and r[2] in target_names)]

        new_rows=[]
        total=len(MONTHS)*len(gsc_targets)
        for m in MONTHS:
            print(f"\n  {m['label']}")
            for name,url,tk in gsc_targets:
                print(f"    {name:25}...",end=" ",flush=True)
                try:
                    row=pull_gsc_month(url,cm[tk],m)
                    row[2]=name; new_rows.append(row)
                    print(f"✓ Clicks:{row[3]:,} Pos:{row[10]}")
                except Exception as e:
                    print(f"✗ {str(e)[:45]}")
                time.sleep(0.5)
            if new_rows:
                ws_gsc.clear()
                ws_gsc.update(range_name="A1",values=[GSC_HEADER]+kept+new_rows)

        print(f"\n  GSC complete — {len(new_rows)}/{total} rows written")

    print(f"\n{'='*50}")
    print(f"ALL DONE")
    print(f"Sheet: https://docs.google.com/spreadsheets/d/{SHEET_ID}")

if __name__=="__main__": main()
