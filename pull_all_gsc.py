import pickle,os,argparse
from datetime import datetime,timedelta
import gspread
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
SHEET_ID="1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"
BASE=os.path.expanduser("~/ThirdSlash_SEO_Automation")
TOKEN_SHEETS=os.path.join(BASE,"token.pickle")
TOKEN_CONNECT=os.path.join(BASE,"token_ga4.pickle")
TOKEN_REPORTING=os.path.join(BASE,"token_reporting.pickle")
TAB_NAME="All_GSC"
TODAY=datetime.now().strftime("%d-%b-%Y")
def get_dates():
    t=datetime.now();fc=t.replace(day=1);lp=fc-timedelta(days=1);fp=lp.replace(day=1)
    lp2=fp-timedelta(days=1);fp2=lp2.replace(day=1)
    return fp.strftime("%Y-%m-%d"),lp.strftime("%Y-%m-%d"),fp2.strftime("%Y-%m-%d"),lp2.strftime("%Y-%m-%d"),lp.strftime("%b-%Y")
START,END,PS,PE,MONTH=get_dates()
CLIENTS=[
    ("Asset Thread","https://assetthread.com/","connect"),
    ("HRM Thread","https://www.hrmthread.com/","connect"),
    ("Lancers CBSE","https://lancerscbse.com/","connect"),
    ("Lancers GSEB","https://lancersgseb.com/","connect"),
    ("Lancers Early Years","https://lancersearlyyears.com/","connect"),
    ("Lancers Army School","https://lancersarmyschools.com/","connect"),
    ("Potential Engineering","https://potentialengineering.com/","connect"),
    ("EZ Lifestyle","https://ez-lifestyle.com/","connect"),
    ("Estrela Hotels","https://www.estrelahotels.com/","reporting"),
    ("Kelly Powers","https://www.kellyepowers.com/","connect"),
    ("HappyLyfe","https://happylyfe.in.th/","reporting"),
    ("Public69","sc-domain:public69.com","reporting"),
    ("Ovation Square","https://www.ovationsquare.com/","connect"),
    ("Piovra Group","https://www.piovragroup.com/","connect"),
    ("Brickroom LA","https://brickroomla.com/","connect"),
    ("MJ Gorgeous","https://mjgorgeous.com/","connect"),
]
HEADER=["Date Pulled","Month","Client Name","Clicks (Current)","Clicks (Prev)","Clicks Change","Impressions (Current)","Impressions (Prev)","Impressions Change","CTR % (Current)","Avg Position (Current)","Avg Position (Prev)","Position Change","Top Keyword","Top Keyword Clicks"]
def load_creds(f):
    with open(f,"rb") as fh: creds=pickle.load(fh)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(f,"wb") as fh: pickle.dump(creds,fh)
    return creds
def pull_gsc(url,creds):
    svc=build("searchconsole","v1",credentials=creds)
    def query(s,e): return svc.searchanalytics().query(siteUrl=url,body={"startDate":s,"endDate":e,"dimensions":["query"],"rowLimit":25}).execute()
    cr=query(START,END);pr=query(PS,PE)
    def totals(r):
        rows=r.get("rows",[])
        if not rows: return 0,0,0,0
        cl=sum(x.get("clicks",0) for x in rows);im=sum(x.get("impressions",0) for x in rows)
        ap=round(sum(x.get("position",0)*x.get("impressions",0) for x in rows)/im,1) if im else 0
        ct=round(cl/im*100,2) if im else 0
        return cl,im,ap,ct
    cc,ci,cp,ctr=totals(cr);pc,pi,pp,_=totals(pr)
    top_kw="";top_cl=0
    if cr.get("rows"):
        top=sorted(cr["rows"],key=lambda x:x.get("clicks",0),reverse=True)[0]
        top_kw=top.get("keys",[""])[0];top_cl=top.get("clicks",0)
    return [TODAY,MONTH,"",cc,pc,cc-pc,ci,pi,ci-pi,ctr,cp,pp,round(pp-cp,1),top_kw,top_cl]
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--client",default=None)
    args=parser.parse_args()
    print(f"ThirdSlash — GSC Puller\n{'='*45}\nPeriod : {START} to {END} ({MONTH})\nCompare: {PS} to {PE}\n")
    cm={"connect":load_creds(TOKEN_CONNECT),"reporting":load_creds(TOKEN_REPORTING)}
    gc=gspread.authorize(load_creds(TOKEN_SHEETS))
    sheet=gc.open_by_key(SHEET_ID)
    try: ws=sheet.worksheet(TAB_NAME)
    except: ws=sheet.add_worksheet(title=TAB_NAME,rows=500,cols=16)
    targets=CLIENTS
    if args.client: targets=[(n,p,t) for n,p,t in CLIENTS if n.lower()==args.client.lower()]
    rows=[]
    for name,url,tk in targets:
        print(f"  {name:25}...",end=" ",flush=True)
        try:
            row=pull_gsc(url,cm[tk]);row[2]=name;rows.append(row)
            print(f"✓ Clicks:{row[3]:,} Pos:{row[10]} Top:{str(row[13])[:25]}")
        except Exception as e: print(f"✗ {str(e)[:70]}")
    if rows:
        all_vals=ws.get_all_values()
        kept=[r for r in all_vals[1:] if r and len(r)>1 and r[1]!=MONTH]
        ws.clear();ws.update(range_name="A1",values=[HEADER]+kept+rows)
        print(f"\nDone — {len(rows)}/16 written to '{TAB_NAME}' for {MONTH}")
    print(f"Sheet: https://docs.google.com/spreadsheets/d/{SHEET_ID}")
if __name__=="__main__": main()
