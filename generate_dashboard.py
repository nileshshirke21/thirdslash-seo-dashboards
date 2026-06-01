"""
ThirdSlash SEO Automation
Script: generate_dashboard.py
Purpose: Read Google Sheet data and generate one HTML dashboard per client
Run: python3 generate_dashboard.py
     python3 generate_dashboard.py --client "Public69"
"""

import gspread, pickle, os, re, argparse
from datetime import datetime
from google.auth.transport.requests import Request

SHEET_ID      = "1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"
TOKEN_FILE    = os.path.join(os.path.dirname(__file__), "token.pickle")
TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "dashboard_template.html")
OUTPUT_DIR    = os.path.join(os.path.dirname(__file__), "dashboards")
REPORT_MONTH  = datetime.now().strftime("%B %Y")
TODAY         = datetime.now().strftime("%d %b %Y")

def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

def get_sheet_client():
    with open(TOKEN_FILE, "rb") as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return gspread.authorize(creds)

def build_rank_rows(rank_data):
    ranking = [r for r in rank_data if r.get('This Month Rank','NR') not in ('NR','')]
    not_ranking = [r for r in rank_data if r.get('This Month Rank','NR') in ('NR','')]
    rows = []
    for r in ranking:
        kw   = r.get('Keyword','')
        cur  = r.get('This Month Rank','NR')
        prev = r.get('Last Month Rank','NR')
        chg  = r.get('Movement','-')
        url  = r.get('Target URL','')
        url_short = url.replace('https://','').replace('http://','')[:45]
        if chg.startswith('+'): move = f'<span class="move-up">↑ {chg}</span>'
        elif chg.startswith('-') and chg != '-': move = f'<span class="move-down">↓ {chg}</span>'
        elif chg == 'NEW': move = '<span class="move-new">NEW</span>'
        else: move = '<span class="move-flat">—</span>'
        rows.append(f'<tr><td>{kw}</td><td><span class="rank-num">{cur}</span></td><td><span class="rank-num" style="color:var(--text2)">{prev if prev != "NR" else "—"}</span></td><td>{move}</td><td><span class="kw-url">{url_short}</span></td></tr>')
    if not_ranking:
        rows.append(f'<tr><td colspan="5" style="color:var(--text3);font-family:\'DM Mono\',monospace;font-size:11px;padding:14px 12px;">+ {len(not_ranking)} keywords not yet ranking in top 100</td></tr>')
    return '\n'.join(rows) if rows else '<tr><td colspan="5" style="color:var(--text3);padding:20px 12px;">No ranking data for this month yet.</td></tr>'

def build_task_cards(task_data):
    task_types = {}
    for row in task_data:
        t = row.get('Task Type','')
        s = row.get('Status','Not Started')
        if t:
            if t not in task_types: task_types[t] = {'total':0,'done':0,'blocked':0,'waiting':0}
            task_types[t]['total'] += 1
            if 'Done' in s or 'done' in s.lower(): task_types[t]['done'] += 1
            elif 'Blocked' in s: task_types[t]['blocked'] += 1
            elif 'Waiting' in s: task_types[t]['waiting'] += 1
    cards = []
    for task_name, counts in task_types.items():
        total = counts['total']
        done  = counts['done']
        pct   = int((done/total*100)) if total else 0
        status = 'done' if pct==100 else ('blocked' if counts['blocked']>0 else ('waiting' if counts['waiting']>0 else ''))
        cards.append(f'<div class="task-card"><div class="task-name">{task_name}</div><div class="task-bar-bg"><div class="task-bar-fill {status}" data-width="{pct}" style="width:0%"></div></div><div class="task-meta">{done}/{total} steps <span>· {pct}%</span></div></div>')
    return '\n'.join(cards) if cards else '<div style="color:var(--text3);font-size:13px;">No tasks logged yet.</div>'

def generate_for_client(client_row, all_ranks, all_tasks, all_backlinks, all_delivery, template):
    name   = client_row.get('Client Name','').strip()
    domain = client_row.get('Website URL','').replace('https://','').replace('http://','').rstrip('/')
    niche  = ''
    notes  = client_row.get('Notes','')
    if 'Niche:' in notes: niche = notes.split('Niche:')[-1].strip().split('|')[0].strip()
    team   = client_row.get('Assigned Team Member','').strip()
    gmb_city = client_row.get('GMB City','-').strip()

    rank_data    = [r for r in all_ranks    if r.get('Client Name','').strip()==name]
    task_data    = [r for r in all_tasks    if r.get('Client Name','').strip()==name]
    backlink_data= [r for r in all_backlinks if r.get('Client Name','').strip()==name]
    delivery_data= [r for r in all_delivery  if r.get('Client Name','').strip()==name]

    ranking_count     = len([r for r in rank_data if r.get('This Month Rank','NR') not in ('NR','')])
    not_ranking_count = len([r for r in rank_data if r.get('This Month Rank','NR') in ('NR','')])

    backlink_rows = ''
    for r in backlink_data:
        ltype  = r.get('Link Type','')
        source = r.get('Source URL','')[:40]
        target = r.get('Target URL (Client Page)','').replace('https://','')[:30]
        anchor = r.get('Anchor Text','')
        status = r.get('Link Status','')
        date   = r.get('Date Built','')
        tc = {'Citation':'bl-citation','Reddit':'bl-reddit','Guest Post':'bl-guest','Blog Comment':'bl-comment'}.get(ltype,'bl-citation')
        sc = 'bl-live' if status=='Live' else 'bl-pending'
        backlink_rows += f'<tr><td><span class="bl-type {tc}">{ltype}</span></td><td style="font-family:\'DM Mono\',monospace;font-size:11px;color:var(--text2)">{source}</td><td style="font-family:\'DM Mono\',monospace;font-size:11px;color:var(--text2)">{target}</td><td style="font-size:12px">{anchor}</td><td><span class="{sc}">{status}</span></td><td style="font-family:\'DM Mono\',monospace;font-size:11px;color:var(--text3)">{date}</td></tr>'
    if not backlink_rows: backlink_rows = '<tr><td colspan="6" style="color:var(--text3);padding:20px 12px;">No backlinks logged yet.</td></tr>'

    delivery_rows = ''
    for r in delivery_data:
        date    = r.get('Date Sent','')
        dtype   = r.get('Deliverable Type','')
        link    = r.get('Document / Link','')
        sent_by = r.get('Sent By','')
        resp    = r.get('Client Response','—')
        fu      = r.get('Follow-Up Required','No')
        fu_html = '<span style="color:var(--warn);font-size:11px">needed</span>' if fu=='Yes' else '<span style="color:var(--text3);font-size:11px">—</span>'
        link_html = f'<a href="{link}" target="_blank" style="color:var(--neutral);font-size:11px;text-decoration:none">{dtype}</a>' if link and link.startswith('http') else dtype
        delivery_rows += f'<tr><td style="font-family:\'DM Mono\',monospace;font-size:11px;color:var(--text3)">{date}</td><td>{link_html}</td><td style="font-size:12px;color:var(--text2)">{sent_by}</td><td style="font-size:12px">{resp}</td><td>{fu_html}</td></tr>'
    if not delivery_rows: delivery_rows = '<tr><td colspan="5" style="color:var(--text3);padding:20px 12px;">No deliverables logged yet.</td></tr>'

    html = template
    for key, val in {
        '{{CLIENT_NAME}}': name, '{{CLIENT_DOMAIN}}': domain,
        '{{CLIENT_NICHE}}': niche, '{{REPORT_MONTH}}': REPORT_MONTH,
        '{{ACCOUNT_MANAGER}}': 'Nilesh Shirke', '{{TEAM_MEMBER}}': team,
        '{{LAST_UPDATED}}': TODAY, '{{TARGET_LOCATION}}': gmb_city,
        '{{SESSIONS}}': '—', '{{USERS}}': '—', '{{ORGANIC_CLICKS}}': '—',
        '{{IMPRESSIONS}}': '—', '{{AVG_POSITION}}': '—', '{{CTR}}': '—',
        '{{SESSIONS_DELTA}}': '—', '{{USERS_DELTA}}': '—', '{{CLICKS_DELTA}}': '—',
        '{{IMPR_DELTA}}': '—', '{{POS_DELTA}}': '—',
        '{{SESSIONS_DELTA_CLASS}}': 'delta-neutral', '{{USERS_DELTA_CLASS}}': 'delta-neutral',
        '{{CLICKS_DELTA_CLASS}}': 'delta-neutral', '{{IMPR_DELTA_CLASS}}': 'delta-neutral',
        '{{POS_DELTA_CLASS}}': 'delta-neutral', '{{SESSIONS_DELTA_ICON}}': '—',
        '{{USERS_DELTA_ICON}}': '—', '{{CLICKS_DELTA_ICON}}': '—',
        '{{IMPR_DELTA_ICON}}': '—', '{{POS_DELTA_ICON}}': '—',
        '{{RANK_DATE}}': TODAY, '{{RANK_LOCATION}}': gmb_city,
        '{{RANK_ROWS}}': build_rank_rows(rank_data),
        '{{RANKING_COUNT}}': str(ranking_count),
        '{{NOT_RANKING_COUNT}}': str(not_ranking_count),
        '{{TASK_CARDS}}': build_task_cards(task_data),
        '{{BACKLINK_ROWS}}': backlink_rows,
        '{{DELIVERY_ROWS}}': delivery_rows,
    }.items():
        html = html.replace(key, str(val))
    return html

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client', default=None)
    args = parser.parse_args()

    print("ThirdSlash — Dashboard Generator")
    print("=" * 40)

    if not os.path.exists(TEMPLATE_FILE):
        print(f"ERROR: dashboard_template.html not found at {TEMPLATE_FILE}")
        return

    with open(TEMPLATE_FILE,'r') as f: template = f.read()

    print("Connecting to Google Sheet...")
    gc    = get_sheet_client()
    sheet = gc.open_by_key(SHEET_ID)

    clients   = sheet.worksheet('01_Client Profile').get_all_records(head=3)
    tasks     = sheet.worksheet('02_Monthly Task Tracker').get_all_records()
    delivery  = sheet.worksheet('03_Delivery Log').get_all_records()
    ranks     = sheet.worksheet('04_Rank Tracking Log').get_all_records()
    backlinks = sheet.worksheet('05_Backlink Log').get_all_records()

    active = [c for c in clients if c.get('Active','').strip()=='Yes']
    if args.client:
        active = [c for c in active if c.get('Client Name','').strip().lower()==args.client.lower()]
        if not active: print(f"Client '{args.client}' not found."); return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    generated = []

    for client in active:
        name = client.get('Client Name','').strip()
        slug = slugify(name)
        client_dir = os.path.join(OUTPUT_DIR, slug)
        os.makedirs(client_dir, exist_ok=True)
        html = generate_for_client(client, ranks, tasks, backlinks, delivery, template)
        out_path = os.path.join(client_dir, 'index.html')
        with open(out_path,'w',encoding='utf-8') as f: f.write(html)
        print(f"  ✓ {name:30} → dashboards/{slug}/index.html")
        generated.append((name, slug))

    print(f"\nGenerated {len(generated)} dashboards")
    print("\nGitHub Pages URLs (after push):")
    for name, slug in generated:
        print(f"  {name:30} https://nileshshirke21.github.io/thirdslash-seo-dashboards/{slug}/")

if __name__ == "__main__":
    main()
