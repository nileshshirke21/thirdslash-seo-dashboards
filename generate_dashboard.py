import gspread,pickle,os,re,argparse,json
from datetime import datetime,timedelta
import calendar
from google.auth.transport.requests import Request

SHEET_ID="1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"
TOKEN_FILE=os.path.join(os.path.dirname(__file__),"token.pickle")
TEMPLATE_FILE=os.path.join(os.path.dirname(__file__),"dashboard_template.html")
OUTPUT_DIR=os.path.join(os.path.dirname(__file__),"dashboards")
TODAY=datetime.now().strftime("%d %b %Y")

def get_report_month():
    t=datetime.now(); fc=t.replace(day=1); lp=fc-timedelta(days=1)
    return lp.strftime("%B %Y"),lp.strftime("%b-%Y")

REPORT_MONTH,MONTH_KEY=get_report_month()

def get_16_months():
    t=datetime.now(); fc=t.replace(day=1); lm=fc-timedelta(days=1); ls=lm.replace(day=1)
    months=[]
    for i in range(15,-1,-1):
        m=ls
        for _ in range(i): m=(m.replace(day=1)-timedelta(days=1)).replace(day=1)
        months.append(m.strftime("%b-%Y"))
    return months

MONTHS_16=get_16_months()

def slugify(n): return re.sub(r'[^a-z0-9]+','-',n.lower()).strip('-')

def get_sheet_client():
    with open(TOKEN_FILE,"rb") as f: creds=pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE,"wb") as f: pickle.dump(creds,f)
    return gspread.authorize(creds)

def fmt(n):
    try: return f"{int(str(n).replace(',','')):,}" if str(n) not in ('','—') else '—'
    except: return str(n) if n else '—'

def delta_cls(v):
    try:
        x=float(str(v).replace(',',''))
        return "delta-up" if x>0 else ("delta-down" if x<0 else "delta-neutral")
    except: return "delta-neutral"

def delta_icon(v,lower_better=False):
    try:
        x=float(str(v).replace(',',''))
        if lower_better: return "↓" if x<0 else("↑" if x>0 else "—")
        return "↑" if x>0 else("↓" if x<0 else "—")
    except: return "—"

def safe_int(v):
    try: return int(str(v).replace(',','')) if str(v) not in ('','—',None) else 0
    except: return 0

def safe_float(v):
    try: return float(str(v).replace(',','')) if str(v) not in ('','—',None) else None
    except: return None

def build_chart_data(name, ga4_all):
    ga4m={r.get('Month',''):r for r in ga4_all if r.get('Client Name','').strip()==name}
    months=[]; sessions=[]; organic_sessions=[]; avg_position=[]
    chatgpt=[]; claude=[]; perplexity=[]; gemini=[]; forms=[]
    for month in MONTHS_16:
        g=ga4m.get(month,{})
        months.append(month)
        sessions.append(safe_int(g.get('Sessions (Current)',0)))
        organic_sessions.append(safe_int(g.get('Organic Sessions',0)))
        pos=safe_float(None)
        avg_position.append(pos)
        chatgpt.append(safe_int(g.get('ChatGPT Sessions',0)))
        claude.append(safe_int(g.get('Claude Sessions',0)))
        perplexity.append(safe_int(g.get('Perplexity Sessions',0)))
        gemini.append(safe_int(g.get('Gemini Sessions',0)))
        forms.append(safe_int(g.get('Form Submissions',0)))
    return json.dumps({"months":months,"sessions":sessions,"organic_sessions":organic_sessions,"avg_position":avg_position,"chatgpt":chatgpt,"claude":claude,"perplexity":perplexity,"gemini":gemini,"forms":forms})

def build_history_rows(name, ga4_all):
    ga4m={r.get('Month',''):r for r in ga4_all if r.get('Client Name','').strip()==name}
    rows=[]
    def n(v):
        try: return f"{int(str(v).replace(',','')):,}" if str(v) not in ('','—',None) else '—'
        except: return str(v) if v else '—'
    for month in reversed(MONTHS_16):
        g=ga4m.get(month,{})
        cls=' class="current-month"' if month==MONTH_KEY else ''
        rows.append(f'<tr{cls}><td>{month}</td><td>{n(g.get("Sessions (Current)",""))}</td><td>{n(g.get("Organic Sessions",""))}</td><td>{n(g.get("Direct Sessions",""))}</td><td>{g.get("Bounce Rate %","—")}</td><td>{n(g.get("ChatGPT Sessions",""))}</td><td>{n(g.get("Claude Sessions",""))}</td><td>{n(g.get("Perplexity Sessions",""))}</td><td>{n(g.get("Gemini Sessions",""))}</td><td>{n(g.get("Form Submissions",""))}</td></tr>')
    return '\n'.join(rows) if rows else '<tr><td colspan="10" style="color:var(--text3);padding:20px 12px;">No historical data yet.</td></tr>'

def build_rank_rows(rank_data):
    ranking=[r for r in rank_data if str(r.get('This Month Rank','NR')) not in ('NR','')]
    not_ranking=[r for r in rank_data if str(r.get('This Month Rank','NR')) in ('NR','')]
    rows=[]
    for r in ranking:
        kw=r.get('Keyword',''); cur=r.get('This Month Rank','NR'); prev=r.get('Last Month Rank','NR')
        chg=str(r.get('Movement','-')); url=r.get('Target URL','')
        url_short=url.replace('https://','').replace('http://','')[:45]
        if chg.startswith('+'): move=f'<span class="move-up">↑ {chg}</span>'
        elif chg.startswith('-') and chg!='-': move=f'<span class="move-down">↓ {chg}</span>'
        elif chg=='NEW': move='<span class="move-new">NEW</span>'
        else: move='<span class="move-flat">—</span>'
        rows.append(f'<tr><td>{kw}</td><td><span class="rank-num">{cur}</span></td><td><span class="rank-num" style="color:var(--text2)">{prev if prev!="NR" else "—"}</span></td><td>{move}</td><td><span class="kw-url">{url_short}</span></td></tr>')
    if not_ranking:
        rows.append(f'<tr><td colspan="5" style="color:var(--text3);font-family:\'DM Mono\',monospace;font-size:11px;padding:14px 12px;">+ {len(not_ranking)} keywords not yet ranking in top 100</td></tr>')
    return '\n'.join(rows) if rows else '<tr><td colspan="5" style="color:var(--text3);padding:20px 12px;">No ranking data yet.</td></tr>'

def build_task_cards(task_data):
    tt={}
    for row in task_data:
        t=row.get('Task Type',''); s=row.get('Status','')
        if t:
            if t not in tt: tt[t]={'total':0,'done':0,'blocked':0,'waiting':0}
            tt[t]['total']+=1
            if 'Done' in s or 'done' in s.lower(): tt[t]['done']+=1
            elif 'Blocked' in s: tt[t]['blocked']+=1
            elif 'Waiting' in s: tt[t]['waiting']+=1
    cards=[]
    for tn,c in tt.items():
        total=c['total']; done=c['done']; pct=int(done/total*100) if total else 0
        st='done' if pct==100 else('blocked' if c['blocked']>0 else('waiting' if c['waiting']>0 else ''))
        cards.append(f'<div class="task-card"><div class="task-name">{tn}</div><div class="task-bar-bg"><div class="task-bar-fill {st}" data-width="{pct}" style="width:0%"></div></div><div class="task-meta">{done}/{total} steps <span>· {pct}%</span></div></div>')
    return '\n'.join(cards) if cards else '<div style="color:var(--text3);font-size:13px;">No tasks logged yet.</div>'

def build_backlink_rows(bl_data):
    rows=[]
    for r in bl_data:
        lt=r.get('Link Type',''); src=r.get('Source URL','')[:40]
        tgt=r.get('Target URL (Client Page)','').replace('https://','')[:30]
        anchor=r.get('Anchor Text',''); status=r.get('Link Status',''); date=r.get('Date Built','')
        tc={'Citation':'bl-citation','Reddit':'bl-reddit','Guest Post':'bl-guest','Blog Comment':'bl-comment'}.get(lt,'bl-citation')
        sc='bl-live' if status=='Live' else 'bl-pending'
        rows.append(f'<tr><td><span class="bl-type {tc}">{lt}</span></td><td style="font-family:\'DM Mono\',monospace;font-size:11px;color:var(--text2)">{src}</td><td style="font-family:\'DM Mono\',monospace;font-size:11px;color:var(--text2)">{tgt}</td><td style="font-size:12px">{anchor}</td><td><span class="{sc}">{status}</span></td><td style="font-family:\'DM Mono\',monospace;font-size:11px;color:var(--text3)">{date}</td></tr>')
    return '\n'.join(rows) if rows else '<tr><td colspan="6" style="color:var(--text3);padding:20px 12px;">No backlinks logged yet.</td></tr>'

def build_delivery_rows(dl_data):
    rows=[]
    for r in dl_data:
        date=r.get('Date Sent',''); dtype=r.get('Deliverable Type',''); link=r.get('Document / Link','')
        sent=r.get('Sent By',''); resp=r.get('Client Response','—'); fu=r.get('Follow-Up Required','No')
        fu_html='<span style="color:var(--warn);font-size:11px">needed</span>' if fu=='Yes' else '<span style="color:var(--text3);font-size:11px">—</span>'
        lh=f'<a href="{link}" target="_blank" style="color:var(--neutral);font-size:11px;text-decoration:none">{dtype}</a>' if link and link.startswith('http') else dtype
        rows.append(f'<tr><td style="font-family:\'DM Mono\',monospace;font-size:11px;color:var(--text3)">{date}</td><td>{lh}</td><td style="font-size:12px;color:var(--text2)">{sent}</td><td style="font-size:12px">{resp}</td><td>{fu_html}</td></tr>')
    return '\n'.join(rows) if rows else '<tr><td colspan="5" style="color:var(--text3);padding:20px 12px;">No deliverables logged yet.</td></tr>'

def generate_for_client(client,all_ranks,all_tasks,all_bl,all_dl,ga4_all,template):
    name=client.get('Client Name','').strip()
    domain=client.get('Website URL','').replace('https://','').replace('http://','').rstrip('/')
    niche=''; notes=client.get('Notes','')
    if 'Niche:' in notes: niche=notes.split('Niche:')[-1].strip().split('|')[0].strip()
    team=client.get('Assigned Team Member','').strip()
    gmb_city=client.get('GMB City','-').strip()

    rank_data=[r for r in all_ranks if r.get('Client Name','').strip()==name]
    task_data=[r for r in all_tasks if r.get('Client Name','').strip()==name]
    bl_data  =[r for r in all_bl   if r.get('Client Name','').strip()==name]
    dl_data  =[r for r in all_dl   if r.get('Client Name','').strip()==name]

    # All data from GA4 only
    ga4m={r.get('Month',''):r for r in ga4_all if r.get('Client Name','').strip()==name}
    g=ga4m.get(MONTH_KEY,{})

    sessions    = fmt(g.get('Sessions (Current)','—'))
    sessions_p  = g.get('Sessions Change','0')
    users       = fmt(g.get('Users (Current)','—'))
    users_p     = g.get('Users Change','0')
    pageviews   = fmt(g.get('Pageviews (Current)','—'))
    pageviews_p = g.get('Pageviews Change','0')
    organic_s   = fmt(g.get('Organic Sessions','—'))
    direct_s    = fmt(g.get('Direct Sessions','—'))
    bounce      = str(g.get('Bounce Rate %','—'))
    duration    = str(g.get('Avg Session Duration (sec)','—'))
    chatgpt_s   = fmt(g.get('ChatGPT Sessions','0'))
    claude_s    = fmt(g.get('Claude Sessions','0'))
    perplexity_s= fmt(g.get('Perplexity Sessions','0'))
    gemini_s    = fmt(g.get('Gemini Sessions','0'))
    forms_s     = fmt(g.get('Form Submissions','0'))

    # Organic delta: current organic vs prev month organic
    prev_month  = MONTHS_16[-2] if len(MONTHS_16)>1 else MONTH_KEY
    g_prev      = ga4m.get(prev_month,{})
    organic_cur = safe_int(g.get('Organic Sessions',0))
    organic_prv = safe_int(g_prev.get('Organic Sessions',0))
    organic_delta = organic_cur - organic_prv

    ranking_count    =len([r for r in rank_data if str(r.get('This Month Rank','NR')) not in ('NR','')])
    not_ranking_count=len([r for r in rank_data if str(r.get('This Month Rank','NR')) in ('NR','')])

    html=template
    for k,v in {
        '{{CLIENT_NAME}}':name,'{{CLIENT_DOMAIN}}':domain,'{{CLIENT_NICHE}}':niche,
        '{{REPORT_MONTH}}':REPORT_MONTH,'{{ACCOUNT_MANAGER}}':'Nilesh Shirke',
        '{{TEAM_MEMBER}}':team,'{{LAST_UPDATED}}':TODAY,'{{TARGET_LOCATION}}':gmb_city,
        '{{SESSIONS}}':sessions,'{{USERS}}':users,
        '{{PAGEVIEWS}}':pageviews,'{{ORGANIC_SESSIONS}}':organic_s,
        '{{DIRECT_SESSIONS}}':direct_s,'{{BOUNCE_RATE}}':bounce,
        '{{AVG_DURATION}}':duration,'{{FORM_SUBMISSIONS}}':forms_s,
        '{{CHATGPT_SESSIONS}}':chatgpt_s,'{{CLAUDE_SESSIONS}}':claude_s,
        '{{PERPLEXITY_SESSIONS}}':perplexity_s,'{{GEMINI_SESSIONS}}':gemini_s,
        '{{SESSIONS_DELTA}}':str(sessions_p),
        '{{USERS_DELTA}}':str(users_p),
        '{{PAGEVIEWS_DELTA}}':str(pageviews_p),
        '{{ORGANIC_DELTA}}':str(organic_delta),
        '{{SESSIONS_DELTA_CLASS}}':delta_cls(sessions_p),
        '{{USERS_DELTA_CLASS}}':delta_cls(users_p),
        '{{PAGEVIEWS_DELTA_CLASS}}':delta_cls(pageviews_p),
        '{{ORGANIC_DELTA_CLASS}}':delta_cls(organic_delta),
        '{{SESSIONS_DELTA_ICON}}':delta_icon(sessions_p),
        '{{USERS_DELTA_ICON}}':delta_icon(users_p),
        '{{PAGEVIEWS_DELTA_ICON}}':delta_icon(pageviews_p),
        '{{ORGANIC_DELTA_ICON}}':delta_icon(organic_delta),
        '{{RANK_DATE}}':TODAY,'{{RANK_LOCATION}}':gmb_city,
        '{{RANK_ROWS}}':build_rank_rows(rank_data),
        '{{RANKING_COUNT}}':str(ranking_count),
        '{{NOT_RANKING_COUNT}}':str(not_ranking_count),
        '{{TASK_CARDS}}':build_task_cards(task_data),
        '{{BACKLINK_ROWS}}':build_backlink_rows(bl_data),
        '{{DELIVERY_ROWS}}':build_delivery_rows(dl_data),
        '{{HISTORY_ROWS}}':build_history_rows(name,ga4_all),
        '{{CHART_DATA_JSON}}':build_chart_data(name,ga4_all),
    }.items():
        html=html.replace(k,str(v))
    return html

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--client',default=None)
    args=parser.parse_args()
    print(f"ThirdSlash — Dashboard Generator\n{'='*40}")
    print(f"Report month: {REPORT_MONTH} ({MONTH_KEY})")
    with open(TEMPLATE_FILE,'r') as f: template=f.read()
    gc=get_sheet_client()
    sheet=gc.open_by_key(SHEET_ID)
    print("Loading sheet data...")
    clients  =sheet.worksheet('01_Client Profile').get_all_records(head=3,expected_headers=[])
    tasks    =sheet.worksheet('02_Monthly Task Tracker').get_all_records(expected_headers=[])
    delivery =sheet.worksheet('03_Delivery Log').get_all_records(expected_headers=[])
    ranks    =sheet.worksheet('04_Rank Tracking Log').get_all_records(expected_headers=[])
    backlinks=sheet.worksheet('05_Backlink Log').get_all_records(expected_headers=[])
    ga4_all=[]; gsc_all=[]
    try:
        ga4_all=sheet.worksheet('All_GA4').get_all_records(expected_headers=[])
        print(f"  GA4: {len(ga4_all)} rows")
    except: print("  ⚠ All_GA4 not found")
    try:
        gsc_all=sheet.worksheet('All_GSC').get_all_records(expected_headers=[])
        print(f"  GSC: {len(gsc_all)} rows")
    except: print("  ⚠ All_GSC not found")
    active=[c for c in clients if c.get('Active','').strip()=='Yes']
    if args.client:
        active=[c for c in active if c.get('Client Name','').strip().lower()==args.client.lower()]
        if not active: print(f"Client '{args.client}' not found."); return
    os.makedirs(OUTPUT_DIR,exist_ok=True)
    generated=[]
    for client in active:
        name=client.get('Client Name','').strip()
        slug=slugify(name)
        client_dir=os.path.join(OUTPUT_DIR,slug)
        os.makedirs(client_dir,exist_ok=True)
        html=generate_for_client(client,ranks,tasks,backlinks,delivery,ga4_all,template)
        with open(os.path.join(client_dir,'index.html'),'w',encoding='utf-8') as f: f.write(html)
        ga4_mo=len([r for r in ga4_all if r.get('Client Name','').strip()==name])
        print(f"  {name:30} GA4:{ga4_mo}mo → {slug}/")
        generated.append((name,slug))
    print(f"\nGenerated {len(generated)} dashboards")

if __name__=="__main__": main()
