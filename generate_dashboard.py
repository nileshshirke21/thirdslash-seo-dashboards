"""
ThirdSlash SEO Dashboards — Generator
Reads All_GA4 + 04_Rank Tracking Log from Google Sheet
Generates one HTML dashboard per client
Run: python3 generate_dashboard.py
"""

import pickle, os, json
from datetime import datetime
from collections import defaultdict
import gspread
from google.auth.transport.requests import Request

SHEET_ID   = "1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"
BASE       = os.path.dirname(os.path.abspath(__file__))
DASH_DIR   = os.path.expanduser("~/ThirdSlash_SEO_Dashboards/dashboards")
TOKEN      = os.path.join(BASE, "token.pickle")

# Client name must match EXACTLY what's in Google Sheets (All_GA4 + 04_Rank Tracking Log)
CLIENTS = {
    "Asset Thread":          "asset-thread",
    "HRM Thread":            "hrm-thread",
    "Lancers CBSE":          "lancers-cbse",
    "Lancers Early Years":   "lancers-early-years",
    "Lancers Army School":   "lancers-army-school",
    "Potential Engineering": "potential-engineering",
    "Estrela Hotels":        "estrela-hotels",
    "Kelly Powers":          "kelly-powers",
    "HappyLyfe":             "happylyfe",
    "Public69":              "public69",
    "Ovation Square":        "ovation-square",
    "Piovra Group":          "piovra-group",
    "Brickroom LA":          "brickroom-la",
    "MJ Gorgeous":           "mj-gorgeous",
    "EZ Lifestyle":          "ez-lifestyle",
    "Lancers GSEB":          "lancers-gseb",
}

def load_creds():
    with open(TOKEN,"rb") as f: c=pickle.load(f)
    if c.expired and c.refresh_token:
        c.refresh(Request())
        with open(TOKEN,"wb") as f: pickle.dump(c,f)
    return c

def get_sheet_data(gc):
    sheet = gc.open_by_key(SHEET_ID)
    ga4_ws   = sheet.worksheet("All_GA4")
    ga4_rows = ga4_ws.get_all_records()
    try:
        rank_ws   = sheet.worksheet("04_Rank Tracking Log")
        rank_rows = rank_ws.get_all_records()
    except:
        rank_rows = []
    try:
        gmb_ws   = sheet.worksheet("All_GMB")
        gmb_vals = gmb_ws.get_all_values()
        gmb_headers = gmb_vals[2]  # row 3 = headers
        gmb_rows = []
        for row in gmb_vals[3:]:
            if row[0] and row[1]:
                gmb_rows.append(dict(zip(gmb_headers, row)))
    except:
        gmb_rows = []
    try:
        tasks_ws = sheet.worksheet("All_SEO_Tasks")
        tasks_rows = tasks_ws.get_all_records()
    except Exception as e:
        print(f"  tasks sheet error: {e}")
        tasks_rows = []
    try:
        lb_ws = sheet.worksheet("All_Link_Building")
        lb_rows = lb_ws.get_all_records()
    except Exception as e:
        print(f"  lb sheet error: {e}")
        lb_rows = []
    return ga4_rows, rank_rows, gmb_rows, tasks_rows, lb_rows

def build_client_ga4(ga4_rows, client_name):
    rows = [r for r in ga4_rows if r.get("Client Name") == client_name]
    def parse_month(m):
        try: return datetime.strptime(m, "%b-%Y")
        except: return datetime.min
    return sorted(rows, key=lambda x: parse_month(x.get("Month","")))

def build_client_ranks(rank_rows, client_name):
    rows = [r for r in rank_rows if r.get("Client Name") == client_name]
    # Column names in 04_Rank Tracking Log:
    # Client Name, Domain, Keyword, Current Position, Previous Position,
    # Current URL, Search Volume, Status, Last Updated
    ranking = [r for r in rows if str(r.get("Status","NR")) == "Ranking"]
    not_ranking = [r for r in rows if str(r.get("Status","NR")) != "Ranking"]
    try:
        ranking_sorted = sorted(ranking, key=lambda x: int(str(x.get("Current Position",999)) or 999))
    except:
        ranking_sorted = ranking
    return ranking_sorted + not_ranking

def movement_class(cur, prev):
    """Compute movement class from current and previous positions."""
    if not cur or cur == "" or cur == "NR":
        return "flat"
    if not prev or prev == "" or prev == "NR":
        return "new"
    try:
        c, p = int(cur), int(prev)
        if c < p: return "up"
        if c > p: return "down"
        return "flat"
    except:
        return "flat"

def movement_icon(cur, prev):
    """Compute movement icon from current and previous positions."""
    if not cur or cur == "" or str(cur) == "NR":
        return "NR"
    if not prev or prev == "" or str(prev) == "NR":
        return "★ NEW"
    try:
        c, p = int(cur), int(prev)
        diff = p - c  # positive = improved (moved up)
        if diff > 0: return f"▲ +{diff}"
        if diff < 0: return f"▼ {diff}"
        return "—"
    except:
        return "—"

def safe_int(v):
    try: return int(str(v).replace(",","")) if v else 0
    except: return 0

def safe_float(v):
    try: return float(str(v).replace("%","")) if v else 0.0
    except: return 0.0

def _render_backlinks_table(data):
    """Render the Total Backlinks Report + 6-month history for the Overview tab."""
    if not data:
        return ""

    # Sort months newest first, take up to 6
    from datetime import datetime as _dt
    def parse_m(m):
        try: return _dt.strptime(m, "%b-%Y")
        except: return _dt.min

    months     = sorted(data.keys(), key=parse_m, reverse=True)
    cur_month  = months[0] if months else None
    prev_month = months[1] if len(months) > 1 else None
    hist_months = list(reversed(months[:6]))  # oldest→newest for history chart

    cur  = data.get(cur_month, {})
    prev = data.get(prev_month, {})

    # ── helpers ──────────────────────────────────────────────────────────────
    def fmt_num(v):
        if v is None: return "—"
        try: return f"{int(v):,}"
        except: return str(v)

    def fmt_score(v):
        if v is None: return "—"
        try:
            f = float(v)
            return str(int(f)) if f == int(f) else f"{f:.1f}"
        except: return str(v)

    def delta_html(key, is_score=False):
        c = cur.get(key)
        p = prev.get(key)
        if c is None or p is None:
            return '<span style="color:#CBD5E1;font-size:11px;">—</span>'
        try:
            d = float(c) - float(p)
            if d == 0:
                return '<span style="color:#94A3B8;font-size:12px;font-weight:600;">—</span>'
            sign  = "▲" if d > 0 else "▼"
            ad    = abs(d)
            val   = (str(int(ad)) if ad == int(ad) else f"{ad:.1f}") if is_score else f"{int(ad):,}"
            color = "#059669" if d > 0 else "#DC2626"
            return f'<span style="color:{color};font-size:12px;font-weight:700;">{sign} {val}</span>'
        except:
            return ""

    # ── 4 metric rows ─────────────────────────────────────────────────────────
    METRICS = [
        ("ahrefs_backlinks",          "Ahrefs",  "External Backlinks",          False, "#1E3A5F"),
        ("ahrefs_referring_domains",  "Ahrefs",  "Unique Referring Domains",    False, "#1E3A5F"),
        ("domain_rating",             "Ahrefs",  "Domain Rating (Out of 100)",  True,  "#2563EB"),
        ("domain_authority",          "Moz",     "Domain Authority (Out of 100)", True, "#7C3AED"),
    ]

    summary_rows = ""
    for key, source, label, is_score, color in METRICS:
        val_cur  = fmt_score(cur.get(key))  if is_score else fmt_num(cur.get(key))
        val_prev = fmt_score(prev.get(key)) if is_score else fmt_num(prev.get(key))
        summary_rows += f"""
          <tr>
            <td style="padding:11px 16px;font-weight:600;color:{color};white-space:nowrap;border-bottom:1px solid #F1F5F9;">{source}</td>
            <td style="padding:11px 16px;font-weight:500;color:#0F172A;border-bottom:1px solid #F1F5F9;">{label}</td>
            <td style="padding:11px 16px;text-align:center;border-bottom:1px solid #F1F5F9;">{delta_html(key, is_score)}</td>
            <td style="padding:11px 16px;text-align:center;font-weight:700;font-size:15px;color:#0F172A;border-bottom:1px solid #F1F5F9;">{val_cur}</td>
            <td style="padding:11px 16px;text-align:center;color:#64748B;border-bottom:1px solid #F1F5F9;">{val_prev}</td>
          </tr>"""

    # ── 6-month history table ─────────────────────────────────────────────────
    hist_headers = "".join(
        f'<th style="padding:9px 14px;text-align:center;font-size:11px;font-weight:600;color:#fff;white-space:nowrap;border-left:1px solid rgba(255,255,255,0.15);">{m}</th>'
        for m in hist_months
    )

    def hist_row(label, key, is_score=False):
        cells = ""
        for m in hist_months:
            v = data.get(m, {}).get(key)
            display = fmt_score(v) if is_score else fmt_num(v)
            is_latest = (m == cur_month)
            bg = "background:#EFF6FF;" if is_latest else ""
            fw = "font-weight:700;" if is_latest else ""
            cells += f'<td style="padding:9px 14px;text-align:center;{bg}{fw}color:#0F172A;border-left:1px solid #F1F5F9;">{display}</td>'
        return f'<tr><td style="padding:9px 14px;font-weight:500;color:#334155;white-space:nowrap;">{label}</td>{cells}</tr>'

    history_rows = (
        hist_row("Ahrefs Backlinks",          "ahrefs_backlinks")        +
        hist_row("Ahrefs Referring Domains",  "ahrefs_referring_domains") +
        hist_row("Domain Rating (Out of 100)",     "domain_rating",  True)    +
        hist_row("Domain Authority (Out of 100)",  "domain_authority", True)
    )

    col_cur  = cur_month  or "Current"
    col_prev = prev_month or "Previous"

    return f"""
  <div style="background:#fff;border:1px solid #E2E8F0;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-top:24px;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;">
      <span style="color:#fff;font-size:13px;font-weight:700;">Total Backlinks Report</span>
      <span style="color:rgba(255,255,255,0.7);font-size:11px;">{col_cur} vs {col_prev}</span>
    </div>

    <!-- Current vs Previous summary -->
    <div style="overflow-x:auto;">
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#F8FAFC;">
            <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:0.6px;border-bottom:2px solid #E2E8F0;">Source</th>
            <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:0.6px;border-bottom:2px solid #E2E8F0;">Metric</th>
            <th style="padding:10px 16px;text-align:center;font-size:11px;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:0.6px;border-bottom:2px solid #E2E8F0;">vs Last Month</th>
            <th style="padding:10px 16px;text-align:center;font-size:11px;font-weight:600;color:#2563EB;text-transform:uppercase;letter-spacing:0.6px;border-bottom:2px solid #E2E8F0;">{col_cur}</th>
            <th style="padding:10px 16px;text-align:center;font-size:11px;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:0.6px;border-bottom:2px solid #E2E8F0;">{col_prev}</th>
          </tr>
        </thead>
        <tbody>{summary_rows}
        </tbody>
      </table>
    </div>

    <!-- 6-month history -->
    <div style="border-top:2px solid #E2E8F0;overflow-x:auto;">
      <div style="padding:10px 16px 6px;font-size:11px;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:0.6px;background:#F8FAFC;">
        6-Month History
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:12px;">
        <thead>
          <tr style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);">
            <th style="padding:9px 14px;text-align:left;font-size:11px;font-weight:600;color:#fff;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">Metric</th>
            {hist_headers}
          </tr>
        </thead>
        <tbody style="background:#fff;">
          {history_rows}
        </tbody>
      </table>
    </div>

    <!-- Footer -->
    <div style="padding:8px 16px;background:#F8FAFC;border-top:1px solid #E2E8F0;font-size:10px;color:#94A3B8;">
      DR by <a href="https://ahrefs.com/" target="_blank" style="color:#94A3B8;">Ahrefs</a> &nbsp;|&nbsp; DA by Moz &nbsp;|&nbsp; Backlinks data via DataForSEO
    </div>
  </div>"""


def build_html(client_name, ga4_rows, rank_rows, gmb_rows=[], tasks_rows=[], lb_rows=[], backlinks_data=None):
    from datetime import datetime as _dt
    import datetime as _dtime

    today = _dt.today()
    current_month_str = today.strftime("%b-%Y")

    def parse_m(m):
        try: return _dt.strptime(m, "%b-%Y")
        except: return _dt.min

    # Exclude current incomplete month
    completed_rows = [r for r in ga4_rows if r.get("Month","") != current_month_str]
    sorted_rows = sorted(completed_rows, key=lambda x: parse_m(x.get("Month","")), reverse=True)
    latest = sorted_rows[0] if sorted_rows else {}
    prev   = sorted_rows[1] if len(sorted_rows) > 1 else {}

    def delta(key, fmt="int"):
        if fmt == "float":
            cur = safe_float(latest.get(key, 0))
            prv = safe_float(prev.get(key, 0))
        else:
            cur = safe_int(latest.get(key, 0))
            prv = safe_int(prev.get(key, 0))
        diff = cur - prv
        pct  = round((diff / prv * 100), 1) if prv else 0
        cls  = "pos" if diff >= 0 else "neg"
        arrow = "▲" if diff >= 0 else "▼"
        return cur, f'<span class="delta {cls}">{arrow} {abs(pct)}%</span>'

    # SEO + AI traffic = Organic + all AI sources
    org_s     = safe_int(latest.get("Organic Sessions", 0))
    ai_s      = safe_int(latest.get("ChatGPT Sessions", 0)) + safe_int(latest.get("Claude Sessions", 0)) + safe_int(latest.get("Perplexity Sessions", 0)) + safe_int(latest.get("Gemini Sessions", 0)) + safe_int(latest.get("Copilot Sessions", 0))
    seo_ai    = org_s + ai_s
    org_s_p   = safe_int(prev.get("Organic Sessions", 0))
    ai_s_p    = safe_int(prev.get("ChatGPT Sessions", 0)) + safe_int(prev.get("Claude Sessions", 0)) + safe_int(prev.get("Perplexity Sessions", 0)) + safe_int(prev.get("Gemini Sessions", 0)) + safe_int(prev.get("Copilot Sessions", 0))
    seo_ai_p  = org_s_p + ai_s_p
    seo_diff  = seo_ai - seo_ai_p
    seo_pct   = round((seo_diff / seo_ai_p * 100), 1) if seo_ai_p else 0
    seo_cls   = "pos" if seo_diff >= 0 else "neg"
    seo_arrow = "▲" if seo_diff >= 0 else "▼"
    d_seo_ai  = f'<span class="delta {seo_cls}">{seo_arrow} {abs(seo_pct)}%</span>'
    # GMB data - last 6 months
    def safe_num(v):
        try: return int(v) if v else 0
        except: return 0

    gmb_sorted = sorted(
        [r for r in gmb_rows if r.get("Month","")],
        key=lambda x: parse_m(x.get("Month","")),
        reverse=True
    )[:6]
    latest_gmb = gmb_sorted[0] if gmb_sorted else {}
    gmb_views      = safe_num(latest_gmb.get("Total Views", 0))
    gmb_clicks     = safe_num(latest_gmb.get("Website Clicks", 0))
    gmb_calls      = safe_num(latest_gmb.get("Phone Calls", 0))
    gmb_directions = safe_num(latest_gmb.get("Direction Requests", 0))
    gmb_posts      = safe_num(latest_gmb.get("GMB Posts", 0))
    gmb_reviews    = safe_num(latest_gmb.get("New Reviews", 0))
    gmb_rating     = latest_gmb.get("Average Rating", "—")
    gmb_month      = latest_gmb.get("Month", "—")
    gmb_has_data   = len(gmb_sorted) > 0

    # GMB history for chart
    gmb_months_chart  = [r.get("Month","") for r in reversed(gmb_sorted)]
    gmb_views_chart   = [safe_num(r.get("Total Views",0)) for r in reversed(gmb_sorted)]
    gmb_clicks_chart  = [safe_num(r.get("Website Clicks",0)) for r in reversed(gmb_sorted)]
    gmb_calls_chart   = [safe_num(r.get("Phone Calls",0)) for r in reversed(gmb_sorted)]

    sessions,     d_sessions = delta("Sessions (Current)")
    users,        d_users    = delta("Users (Current)")
    org_sessions, d_org      = delta("Organic Sessions")
    pageviews,    d_pv       = delta("Pageviews (Current)")
    bounce,       d_bounce   = delta("Bounce Rate %", "float")
    avg_dur,      d_dur      = delta("Avg Session Duration (sec)")
    direct,       d_direct   = delta("Direct Sessions")
    forms,        d_forms    = delta("Form Submissions")

    # History rows — last 13 completed months, newest first
    _hist_rows = sorted(
        [r for r in ga4_rows if r.get("Month","") != current_month_str],
        key=lambda x: parse_m(x.get("Month","")),
        reverse=True
    )[:13]

    # Chart data — last 12 completed months, oldest first
    _chart_rows = sorted(
        [r for r in ga4_rows if r.get("Month","") != current_month_str],
        key=lambda x: parse_m(x.get("Month",""))
    )[-12:]

    months = [r.get("Month","") for r in _chart_rows]
    sess_d = [safe_int(r.get("Sessions (Current)",0)) for r in _chart_rows]
    org_d  = [safe_int(r.get("Organic Sessions",0))   for r in _chart_rows]
    form_d = [safe_int(r.get("Form Submissions",0))   for r in _chart_rows]

    # AI traffic
    ai_keys   = ["ChatGPT Sessions","Gemini Sessions","Claude Sessions","Perplexity Sessions","Copilot Sessions"]
    ai_labels = ["ChatGPT","Gemini","Claude","Perplexity","Copilot"]
    ai_vals      = [safe_int(latest.get(k,0)) for k in ai_keys]
    ai_prev_vals = [safe_int(prev.get(k,0))   for k in ai_keys]

    # Traffic channels
    ch_keys   = ["Organic Sessions","Direct Sessions","Referral Sessions","Social Sessions","Email Sessions","Paid Sessions"]
    ch_labels = ["Organic","Direct","Referral","Social","Email","Paid"]
    ch_colors = ["#4CAF50","#2196F3","#FF9800","#E91E63","#9C27B0","#00BCD4"]
    ch_vals   = [safe_int(latest.get(k,0)) for k in ch_keys]

    # Stacked AI monthly
    ai_monthly = {label: [safe_int(r.get(k,0)) for r in _chart_rows]
                  for k, label in zip(ai_keys, ai_labels)}

    # Rankings — use correct column names from 04_Rank Tracking Log
    # Columns: Keyword, Current Position, Previous Position, Current URL, Search Volume, Status, Last Updated
    total_tracked = len(rank_rows)
    ranking_only  = [r for r in rank_rows if str(r.get("Status","")) == "Ranking"]
    top3  = len([r for r in ranking_only if safe_int(r.get("Current Position",999)) <= 3])
    top10 = len([r for r in ranking_only if safe_int(r.get("Current Position",999)) <= 10])
    top50 = len([r for r in ranking_only if safe_int(r.get("Current Position",999)) <= 50])
    top20_only    = len([r for r in ranking_only if 11 <= safe_int(r.get("Current Position",999)) <= 20])
    top21_50      = len([r for r in ranking_only if 21 <= safe_int(r.get("Current Position",999)) <= 50])
    top51_100     = len([r for r in ranking_only if 51 <= safe_int(r.get("Current Position",999)) <= 100])
    not_ranking_count = len([r for r in rank_rows if str(r.get("Status","NR")) != "Ranking"])

    # Previous bucket counts
    prev_top10    = len([r for r in rank_rows if safe_int(r.get("Previous Position",999)) <= 10 and str(r.get("Previous Position","")) not in ["","NR"]])
    prev_top20    = len([r for r in rank_rows if 11 <= safe_int(r.get("Previous Position",999)) <= 20 and str(r.get("Previous Position","")) not in ["","NR"]])
    prev_top21_50 = len([r for r in rank_rows if 21 <= safe_int(r.get("Previous Position",999)) <= 50 and str(r.get("Previous Position","")) not in ["","NR"]])
    prev_top51_100= len([r for r in rank_rows if 51 <= safe_int(r.get("Previous Position",999)) <= 100 and str(r.get("Previous Position","")) not in ["","NR"]])
    prev_nr       = len([r for r in rank_rows if str(r.get("Previous Position","")) in ["","NR"]])

    def bucket_change(cur, prev):
        diff = cur - prev
        if diff > 0: return f'<span style="color:#4ade80">+{diff}</span>'
        if diff < 0: return f'<span style="color:#f87171">{diff}</span>'
        return '<span style="color:#94a3b8">—</span>'
    top20_only    = len([r for r in ranking_only if 11 <= safe_int(r.get("Current Position",999)) <= 20])
    top21_50      = len([r for r in ranking_only if 21 <= safe_int(r.get("Current Position",999)) <= 50])
    top51_100     = len([r for r in ranking_only if 51 <= safe_int(r.get("Current Position",999)) <= 100])
    not_ranking_count = len([r for r in rank_rows if str(r.get("Status","NR")) != "Ranking"])

    # Previous bucket counts
    prev_top10    = len([r for r in rank_rows if safe_int(r.get("Previous Position",999)) <= 10 and str(r.get("Previous Position","")) not in ["","NR"]])
    prev_top20    = len([r for r in rank_rows if 11 <= safe_int(r.get("Previous Position",999)) <= 20 and str(r.get("Previous Position","")) not in ["","NR"]])
    prev_top21_50 = len([r for r in rank_rows if 21 <= safe_int(r.get("Previous Position",999)) <= 50 and str(r.get("Previous Position","")) not in ["","NR"]])
    prev_top51_100= len([r for r in rank_rows if 51 <= safe_int(r.get("Previous Position",999)) <= 100 and str(r.get("Previous Position","")) not in ["","NR"]])
    prev_nr       = len([r for r in rank_rows if str(r.get("Previous Position","")) in ["","NR"]])

    def bucket_change(cur, prev):
        diff = cur - prev
        if diff > 0: return f'<span style="color:#4ade80">+{diff}</span>'
        if diff < 0: return f'<span style="color:#f87171">{diff}</span>'
        return '<span style="color:#94a3b8">—</span>'

    last_updated = rank_rows[0].get("Last Updated","—") if rank_rows else "—"

    rank_rows_html = ""
    for _sr, r in enumerate(rank_rows, 1):
        cur  = r.get("Current Position","")
        prv  = r.get("Previous Position","")
        kw   = r.get("Keyword","")
        vol  = r.get("Search Volume","")
        url  = r.get("Current URL","")
        status = str(r.get("Status","NR"))

        cls  = movement_class(cur, prv)
        icon = movement_icon(cur, prv)

        # Display position
        cur_display = cur if cur != "" else "NR"
        prv_display = prv if prv != "" else "NR"

        url_str = str(url) if url else ""
        rank_rows_html += f"""
        <tr>
          <td style="text-align:center;color:#64748b;font-size:12px;width:40px">{_sr}</td>
          <td class="kw-cell" title="{kw}">{kw}</td>
          <td class="rank-cell rank-{cls}" style="text-align:center">{cur_display}</td>
          <td class="rank-cell" style="text-align:center">{prv_display}</td>
          <td class="move-cell {cls}">{icon}</td>
          <td class="vol-cell">{vol}</td>
          <td class="url-cell"><a href="{url_str}" target="_blank">{url_str}</a></td>
        </tr>"""

    now = datetime.now().strftime("%d %b %Y")

    # Build history HTML outside f-string
    _hist_rows_html = "".join([
        f'<tr><td>{r.get("Month","")}</td>' +
        f'<td>{safe_int(r.get("Sessions (Current)",0)):,}</td>' +
        f'<td>{safe_int(r.get("Organic Sessions",0)):,}</td>' +
        f'<td>{safe_int(r.get("Direct Sessions",0)):,}</td>' +
        f'<td>{safe_int(r.get("ChatGPT Sessions",0)) + safe_int(r.get("Claude Sessions",0)) + safe_int(r.get("Perplexity Sessions",0)) + safe_int(r.get("Gemini Sessions",0)) + safe_int(r.get("Copilot Sessions",0)):,}</td>' +
        f'<td>{safe_int(r.get("Users (Current)",0)):,}</td>' +
        f'<td>{safe_int(r.get("Pageviews (Current)",0)):,}</td>' +
        f'<td>{safe_float(r.get("Bounce Rate %",0)):.1f}%</td>' +
        f'<td>{safe_int(r.get("Form Submissions",0)):,}</td></tr>'
        for r in _hist_rows
    ])


    # Last completed month
    import datetime as _ldt2
    _prev2 = _ldt2.datetime.today().replace(day=1) - _ldt2.timedelta(days=1)
    last_month_str = _prev2.strftime("%b-%Y")

    # GMB data
    def safe_num(v):
        try: return int(v) if v else 0
        except: return 0

    gmb_sorted = sorted(
        [r for r in gmb_rows if r.get("Month","")],
        key=lambda x: parse_m(x.get("Month","")), reverse=True
    )[:6]
    latest_gmb     = gmb_sorted[0] if gmb_sorted else {}
    gmb_views      = safe_num(latest_gmb.get("Total Views", 0))
    gmb_clicks     = safe_num(latest_gmb.get("Website Clicks", 0))
    gmb_calls      = safe_num(latest_gmb.get("Phone Calls", 0))
    gmb_directions = safe_num(latest_gmb.get("Direction Requests", 0))
    gmb_posts      = safe_num(latest_gmb.get("GMB Posts", 0))
    gmb_reviews    = safe_num(latest_gmb.get("New Reviews", 0))
    gmb_rating     = latest_gmb.get("Average Rating", "—")
    gmb_month      = latest_gmb.get("Month", "—")
    gmb_has_data   = len(gmb_sorted) > 0
    gmb_months_chart = [r.get("Month","") for r in reversed(gmb_sorted)]
    gmb_views_chart  = [safe_num(r.get("Total Views",0)) for r in reversed(gmb_sorted)]
    gmb_clicks_chart = [safe_num(r.get("Website Clicks",0)) for r in reversed(gmb_sorted)]
    gmb_calls_chart  = [safe_num(r.get("Phone Calls",0)) for r in reversed(gmb_sorted)]

    # SEO Tasks
    _tasks         = [r for r in tasks_rows if r.get("Month","") == last_month_str]
    _tasks_done    = len([r for r in _tasks if str(r.get("Status","")) == "Completed"])
    _tasks_prog    = len([r for r in _tasks if str(r.get("Status","")) == "In Progress"])
    _tasks_pending = len([r for r in _tasks if str(r.get("Status","")) == "Pending"])

    def _stask(s):
        s = str(s)
        d = {"Completed": ("#D1FAE5","#065F46","&#10003; Completed"),
             "In Progress": ("#FEF3C7","#92400E","&#8635; In Progress")}
        bg, fg, txt = d.get(s, ("#F1F5F9","#64748B","&#9675; Pending"))
        return ('<span style="background:' + bg + ';color:' + fg +
                ';padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap;display:inline-block;">' + txt + '</span>')

    _task_rows_html = []
    for _ti, r in enumerate(_tasks, 1):
        _tn    = str(r.get("Task Name",""))
        _ta    = str(r.get("Assigned To","ThirdSlash"))
        _ts    = str(r.get("Status",""))
        _tl    = str(r.get("Link to Sheet / Doc","") or "")
        _tnote = str(r.get("Notes","") or "")
        _tlink = ('<a href="' + _tl + '" target="_blank" style="color:#2563EB;font-size:11px;">View</a>'
                  if _tl else "—")
        _task_rows_html.append(
            '<tr>'
            '<td style="text-align:center;color:#64748b;font-size:12px">' + str(_ti) + '</td>'
            '<td style="font-weight:500;color:#0F172A;padding:12px 14px">' + _tn + '</td>'
            '<td style="text-align:center;font-size:12px;color:#64748B">' + _ta + '</td>'
            '<td style="text-align:center">' + _stask(_ts) + '</td>'
            '<td style="text-align:center">' + _tlink + '</td>'
            '<td style="font-size:11px;color:#64748B">' + _tnote + '</td>'
            '</tr>'
        )
    _task_rows_html = "".join(_task_rows_html)

    # Link Building
    _lb     = [r for r in lb_rows if r.get("Month","") == last_month_str]
    _reddit = [r for r in _lb if str(r.get("Type","")) == "Reddit"]
    _quora  = [r for r in _lb if str(r.get("Type","")) == "Quora"]
    _blogs  = [r for r in _lb if str(r.get("Type","")) == "Blog Comment"]
    _dirs   = [r for r in _lb if str(r.get("Type","")) == "Directory"]

    def _slb(s):
        s = str(s)
        d = {"Live":         ("#D1FAE5","#065F46","&#9679; Live"),
             "Approved":     ("#DBEAFE","#1E40AF","&#10003; Approved"),
             "Not Approved": ("#FEE2E2","#991B1B","&#10007; Not Approved")}
        bg, fg, txt = d.get(s, ("#FEF3C7","#92400E","&#8635; Pending"))
        return ('<span style="background:' + bg + ';color:' + fg +
                ';padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap;display:inline-block;">' + txt + '</span>')

    def _type_badge(t):
        d = {"Reddit": ("#FF4500","#fff"), "Quora": ("#A82400","#fff"),
             "Blog Comment": ("#2563EB","#fff"), "Directory": ("#059669","#fff")}
        bg, fg = d.get(t, ("#64748B","#fff"))
        return ('<span style="background:' + bg + ';color:' + fg +
                ';padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;white-space:nowrap;display:inline-block;">' + t + '</span>')

    _lb_rows_html = []
    for _lbi, r in enumerate(_lb, 1):
        t   = str(r.get("Type",""))
        u   = str(r.get("Post / Blog URL","") or "")
        an  = str(r.get("Anchor Text","") or "")
        lt  = str(r.get("Linking To","") or "")
        lv  = str(r.get("Live Link","") or "")
        st  = str(r.get("Status",""))
        cm  = str(r.get("Comment","") or "")
        lvh = ('<a href="' + lv + '" target="_blank" style="color:#2563EB;font-size:11px">View</a>'
               if lv else "—")
        _lb_rows_html.append(
            '<tr data-type="' + t + '" data-status="' + st + '">'
            '<td style="text-align:center;color:#64748b;font-size:12px">' + str(_lbi) + '</td>'
            '<td style="padding:8px 10px;white-space:nowrap;vertical-align:middle">' + _type_badge(t) + '</td>'
            '<td style="padding:10px 14px;word-break:break-all;font-size:12px">'
            '<a href="' + u + '" target="_blank" style="color:#2563EB;font-weight:500">' + u + '</a></td>'
            '<td style="font-size:12px;color:#0F172A">' + an + '</td>'
            '<td style="font-size:12px;color:#64748B;word-break:break-all">' + lt + '</td>'
            '<td style="text-align:center">' + lvh + '</td>'
            '<td style="text-align:center">' + _slb(st) + '</td>'
            '<td style="font-size:11px;color:#94A3B8">' + cm + '</td>'
            '</tr>'
        )
    _lb_combined_html = ("".join(_lb_rows_html) if _lb_rows_html else
        '<tr><td colspan="8" style="text-align:center;color:#94A3B8;padding:20px;">'
        'No link building activity this month</td></tr>')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{client_name} — SEO Dashboard | ThirdSlash</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #F5F7FA; --bg2: #EDF0F4; --card: #FFFFFF; --card2: #F8FAFC;
    --accent: #2563EB; --accent2: #1D4ED8;
    --text: #0F172A; --muted: #64748B; --border: #E2E8F0;
    --green: #059669; --red: #DC2626; --orange: #D97706; --blue: #2563EB;
    --up: #059669; --down: #DC2626; --new: #7C3AED; --flat: #94A3B8;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }}
  .header {{ background: linear-gradient(135deg, #1E3A5F 0%, #2563EB 100%); padding: 20px 32px; display: flex; justify-content: space-between; align-items: center; }}
  .header-left h1 {{ font-size: 22px; font-weight: 700; color: #fff; }}
  .header-left .subtitle {{ font-size: 12px; color: rgba(255,255,255,0.7); margin-top: 3px; }}
  .header-right {{ display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }}
  .logo {{ font-size: 14px; font-weight: 800; color: #fff; letter-spacing: 2px; }}
  .updated {{ font-size: 11px; color: rgba(255,255,255,0.6); }}
  .nav {{ background: #fff; border-bottom: 1px solid var(--border); padding: 0 32px; display: flex; gap: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .nav-tab {{ padding: 14px 20px; font-size: 13px; font-weight: 600; color: var(--muted); cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.2s; }}
  .nav-tab.active {{ color: var(--accent); border-bottom-color: var(--accent); }}
  .nav-tab:hover {{ color: var(--text); }}
  .section {{ display: none; padding: 28px 32px; }}
  .section.active {{ display: block; }}
  .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }}
  .metric-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; position: relative; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 4px solid var(--accent); }}
  .metric-label {{ font-size: 11px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 4px; }}
  .period-label {{ font-size: 10px; color: var(--muted); margin-bottom: 10px; }}
  .metric-value {{ font-size: 28px; font-weight: 800; color: var(--text); line-height: 1; margin-bottom: 6px; }}
  .delta {{ font-size: 12px; font-weight: 600; }}
  .delta.pos {{ color: var(--green); }}
  .delta.neg {{ color: var(--red); }}
  .charts-grid {{ display: grid; grid-template-columns: repeat(2,1fr); gap: 20px; margin-bottom: 28px; }}
  .chart-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .chart-title {{ font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 14px; }}
  .chart-wrap {{ position: relative; height: 220px; }}
  .ai-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }}
  .ai-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .ai-card .ai-icon {{ font-size: 26px; margin-bottom: 8px; }}
  .ai-card .ai-label {{ font-size: 11px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.7px; }}
  .ai-card .ai-val {{ font-size: 26px; font-weight: 700; color: var(--accent); margin: 6px 0 4px; }}
  .ai-card .ai-delta {{ font-size: 12px; }}
  .rank-summary {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; margin-bottom: 24px; }}
  .rank-badge {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .rank-badge .badge-num {{ font-size: 34px; font-weight: 800; }}
  .rank-badge .badge-label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; margin-top: 4px; }}
  .rank-badge.top3 .badge-num {{ color: #F59E0B; }}
  .rank-badge.top10 .badge-num {{ color: var(--green); }}
  .rank-badge.top50 .badge-num {{ color: var(--blue); }}
  .rank-badge.total .badge-num {{ color: var(--muted); }}
  .rank-table-wrap {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .rank-table-header {{ padding: 16px 20px; border-bottom: 1px solid var(--border); font-size: 13px; font-weight: 700; display: flex; justify-content: space-between; align-items: center; background: var(--card2); }}
  .rank-table-header .period {{ font-size: 11px; color: var(--muted); font-weight: 400; }}
  .rank-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .rank-table th {{ padding: 10px 14px; text-align: left; font-size: 11px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.6px; border-bottom: 2px solid var(--border); background: #F8FAFC; }}
  .rank-table td {{ padding: 11px 14px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
  .rank-table tr:last-child td {{ border-bottom: none; }}
  .rank-table tr:hover td {{ background: #EFF6FF; }}
  .rank-table-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
  .rank-table {{ width: 100%; min-width: 600px; table-layout: auto; }}
  .kw-cell {{ word-break: break-word; white-space: normal; color: var(--text); min-width: 180px; font-weight: 500; }}
  .rank-cell {{ font-weight: 700; text-align: center; width: 70px; }}
  .rank-cell.rank-up {{ color: var(--green); }}
  .rank-cell.rank-down {{ color: var(--red); }}
  .rank-cell.rank-new {{ color: var(--new); }}
  .rank-cell.rank-flat {{ color: var(--muted); }}
  .move-cell {{ font-size: 12px; font-weight: 700; width: 80px; }}
  .move-cell.up {{ color: var(--up); }}
  .move-cell.down {{ color: var(--down); }}
  .move-cell.new {{ color: var(--new); }}
  .move-cell.flat {{ color: var(--flat); }}
  .vol-cell {{ color: var(--muted); font-size: 12px; width: 80px; }}
  .url-cell {{ font-size: 11px; color: var(--muted); word-break: break-all; white-space: normal; }}
  .url-cell a {{ color: var(--accent); text-decoration: none; font-weight: 500; }}
  .url-cell a:hover {{ text-decoration: underline; }}
  .rank-bucket-wrap {{ margin-bottom: 24px; display: block; width: 100%; }}
  .rank-controls {{ padding: 12px 16px; display:flex; align-items:center; border-bottom: 1px solid var(--border); background: var(--card2); }}
  .sort-icon {{ font-size:10px; color:var(--muted); margin-left:3px; vertical-align:middle; }}
  .rank-bucket-table {{ width: 100%; max-width: 640px; border-collapse: collapse; background: var(--card); border-radius: 8px; overflow: hidden; border: 1px solid var(--border); margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .rank-bucket-table th {{ background: linear-gradient(135deg, #1E3A5F 0%, #2563EB 100%); padding: 12px 20px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #fff; text-align: left; white-space: nowrap; }}
  .rank-bucket-table td {{ padding: 10px 20px; font-size: 13px; border-top: 1px solid var(--border); white-space: nowrap; }}
  .rank-bucket-table tr:hover td {{ background: #EFF6FF; }}
  .history-wrap {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: auto; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .history-table {{ width: 100%; border-collapse: collapse; font-size: 12px; min-width: 900px; }}
  .history-table th {{ padding: 10px 14px; text-align: right; font-size: 11px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid var(--border); background: linear-gradient(135deg, #1E3A5F 0%, #2563EB 100%); color: #fff; white-space: nowrap; }}
  .history-table th:first-child {{ text-align: left; }}
  .history-table td {{ padding: 9px 14px; border-bottom: 1px solid var(--border); text-align: right; }}
  .history-table td:first-child {{ text-align: left; font-weight: 600; color: var(--accent); }}
  .history-table tr:last-child td {{ border-bottom: none; }}
  .history-table tr:hover td {{ background: #EFF6FF; }}
  .no-data {{ text-align: center; padding: 60px 20px; color: var(--muted); }}
  .rank-table td {{ vertical-align: middle; }}
  .rank-table th {{ white-space: nowrap; }}
  @media (max-width: 768px) {{
    .section {{ padding: 16px 12px; }}
    .metrics-grid {{ grid-template-columns: 1fr 1fr; gap: 10px; }}
    .charts-grid {{ grid-template-columns: 1fr; }}
    .ai-grid {{ grid-template-columns: 1fr 1fr; }}
    .gmb-grid {{ grid-template-columns: repeat(2, 1fr) !important; gap: 8px; }}
    .rank-table-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
    .rank-bucket-wrap {{ overflow-x: auto; }}
    .history-wrap {{ overflow-x: auto; }}
    .nav {{ overflow-x: auto; white-space: nowrap; -webkit-overflow-scrolling: touch; }}
    .nav-tab {{ padding: 12px 12px; font-size: 12px; flex-shrink: 0; }}
    .header {{ padding: 12px 16px; }}
    .header-left h1 {{ font-size: 15px; }}
    .header-left p {{ font-size: 11px; }}
    .chart-card {{ padding: 16px 12px; }}
    .metric-card {{ padding: 14px 12px; }}
    .metric-value {{ font-size: 22px; }}
  }}
  @media (max-width: 480px) {{
    .metrics-grid {{ grid-template-columns: 1fr; }}
    .gmb-grid {{ grid-template-columns: 1fr 1fr !important; }}
    .ai-grid {{ grid-template-columns: 1fr 1fr; }}
    .header-right {{ display: none; }}
  }}
  .gmb-section {{ margin-bottom: 28px; }}
  .gmb-header {{ display: flex; align-items: center; margin-bottom: 16px; }}
  .gmb-title {{ font-size: 15px; font-weight: 700; color: var(--text); }}
  .gmb-grid {{ display: grid; grid-template-columns: repeat(7,1fr); gap: 12px; margin-bottom: 16px; }}
  .gmb-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 12px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-top: 3px solid #059669; }}
  .gmb-icon {{ font-size: 20px; margin-bottom: 6px; }}
  .gmb-val {{ font-size: 20px; font-weight: 700; color: #059669; }}
  .gmb-label {{ font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }}
  @media(max-width:1100px) {{ .gmb-grid {{ grid-template-columns: repeat(4,1fr); }} }}
  .no-data .icon {{ font-size: 48px; margin-bottom: 12px; }}
  .no-data p {{ font-size: 14px; }}
  @media (max-width: 1100px) {{
    .metrics-grid {{ grid-template-columns: repeat(2,1fr); }}
    .ai-grid {{ grid-template-columns: repeat(2,1fr); }}
    .rank-summary {{ grid-template-columns: repeat(2,1fr); }}
    .charts-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <h1>{client_name}</h1>
    <div class="subtitle">SEO Performance Dashboard</div>
  </div>
  <div class="header-right">
    <div class="logo">THIRDSLASH</div>
    <div class="updated">Updated: {now}</div>
  </div>
</div>

<div class="nav">
  <div class="nav-tab active" onclick="showTab('overview', this)\">Overview</div>
  <div class="nav-tab" onclick="showTab('rankings', this)\">Rankings</div>
  <div class="nav-tab" onclick="showTab('history', this)\">History</div>
  <div class="nav-tab" onclick="showTab('gmb', this)\">GMB</div>
  <div class="nav-tab" onclick="showTab('tasks', this)\">SEO Tasks</div>
  <div class="nav-tab" onclick="showTab('linkbuilding', this)\">Link Building</div>
</div>

<!-- OVERVIEW TAB -->
<div id="tab-overview" class="section active">
  <div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-label">SEO + AI Traffic</div>
      <div class="period-label">{latest.get("Month","—")} vs {prev.get("Month","—")}</div>
      <div class="metric-value">{seo_ai:,}</div>
      {d_seo_ai}
    </div>
    <div class="metric-card">
      <div class="metric-label">Organic Sessions</div>
      <div class="period-label">{latest.get("Month","—")} vs {prev.get("Month","—")}</div>
      <div class="metric-value">{org_sessions:,}</div>
      {d_org}
    </div>
    <div class="metric-card">
      <div class="metric-label">Total Sessions</div>
      <div class="period-label">{latest.get("Month","—")} vs {prev.get("Month","—")}</div>
      <div class="metric-value">{sessions:,}</div>
      {d_sessions}
    </div>
    <div class="metric-card">
      <div class="metric-label">Pageviews</div>
      <div class="period-label">{latest.get("Month","—")} vs {prev.get("Month","—")}</div>
      <div class="metric-value">{pageviews:,}</div>
      {d_pv}
    </div>
    <div class="metric-card">
      <div class="metric-label">Bounce Rate</div>
      <div class="period-label">{latest.get("Month","—")} vs {prev.get("Month","—")}</div>
      <div class="metric-value">{bounce:.1f}%</div>
      {d_bounce}
    </div>
    <div class="metric-card">
      <div class="metric-label">Avg Duration (sec)</div>
      <div class="period-label">{latest.get("Month","—")} vs {prev.get("Month","—")}</div>
      <div class="metric-value">{avg_dur:,}</div>
      {d_dur}
    </div>
    <div class="metric-card">
      <div class="metric-label">Direct Sessions</div>
      <div class="period-label">{latest.get("Month","—")} vs {prev.get("Month","—")}</div>
      <div class="metric-value">{direct:,}</div>
      {d_direct}
    </div>
    <div class="metric-card">
      <div class="metric-label">Form Submissions</div>
      <div class="period-label">{latest.get("Month","—")} vs {prev.get("Month","—")}</div>
      <div class="metric-value">{forms:,}</div>
      {d_forms}
    </div>
  </div>

  <div class="charts-grid">
    <div class="chart-card">
      <div class="chart-title">Sessions vs Organic Sessions (Last 12 Completed Months)</div>
      <div class="chart-wrap"><canvas id="sessChart"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Form Submissions</div>
      <div class="chart-wrap"><canvas id="formChart"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">AI Traffic Trend</div>
      <div class="chart-wrap"><canvas id="aiChart"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Traffic Channels (Latest Month)</div>
      <div class="chart-wrap"><canvas id="chChart"></canvas></div>
    </div>
  </div>

  <div class="ai-grid" style="grid-template-columns:repeat(5,1fr);">
    {"".join([f'''<div class="ai-card">
      <div class="ai-icon"><img src="{["../icons/chatgpt.png","https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/google-gemini.png","../icons/claude.png","https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/perplexity.png","https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/microsoft-copilot.png"][i]}" alt="{ai_labels[i]}" style="width:28px;height:28px;border-radius:6px;object-fit:contain;"></div>
      <div class="ai-label">{ai_labels[i]}</div>
      <div class="ai-val">{ai_vals[i]:,}</div>
      <div class="ai-delta {'pos' if ai_vals[i]>=ai_prev_vals[i] else 'neg'} delta">{"▲" if ai_vals[i]>=ai_prev_vals[i] else "▼"} {abs(ai_vals[i]-ai_prev_vals[i])}</div>
    </div>''' for i in range(5)])}
  </div>

  {_render_backlinks_table(backlinks_data)}
</div>

<div id="tab-rankings" class="section">
  {"" if total_tracked == 0 else f'''
  <div class="rank-bucket-wrap">
    <table class="rank-bucket-table">
      <thead>
        <tr>
          <th>Position Bucket</th>
          <th style="text-align:center">Current</th>
          <th style="text-align:center">Previous</th>
          <th style="text-align:center">Change</th>
        </tr>
      </thead>
      <tbody>
        <tr><td>🥇 Top 10</td><td style="text-align:center;color:#4ade80;font-weight:600">{top10}</td><td style="text-align:center;color:#94a3b8">{prev_top10}</td><td style="text-align:center">{bucket_change(top10,prev_top10)}</td></tr>
        <tr><td>🥈 Position 11–20</td><td style="text-align:center;color:#facc15;font-weight:600">{top20_only}</td><td style="text-align:center;color:#94a3b8">{prev_top20}</td><td style="text-align:center">{bucket_change(top20_only,prev_top20)}</td></tr>
        <tr><td>🥉 Position 21–50</td><td style="text-align:center;color:#fb923c;font-weight:600">{top21_50}</td><td style="text-align:center;color:#94a3b8">{prev_top21_50}</td><td style="text-align:center">{bucket_change(top21_50,prev_top21_50)}</td></tr>
        <tr><td>📉 Position 51–100</td><td style="text-align:center;color:#f87171;font-weight:600">{top51_100}</td><td style="text-align:center;color:#94a3b8">{prev_top51_100}</td><td style="text-align:center">{bucket_change(top51_100,prev_top51_100)}</td></tr>
        <tr><td>❌ Not Ranking</td><td style="text-align:center;color:#94a3b8;font-weight:600">{not_ranking_count}</td><td style="text-align:center;color:#94a3b8">{prev_nr}</td><td style="text-align:center">{bucket_change(not_ranking_count,prev_nr)}</td></tr>
        <tr style="border-top:1px solid #334155"><td><strong>Total Tracked</strong></td><td style="text-align:center;font-weight:700">{total_tracked}</td><td style="text-align:center;color:#94a3b8">{total_tracked}</td><td style="text-align:center;color:#94a3b8">—</td></tr>
      </tbody>
    </table>
  </div>
  <div class="rank-table-wrap">
    <div class="rank-table-header">
      Keyword Rankings
      <span class="period">Last Updated: {last_updated}</span>
    </div>
    <div class="rank-controls">
      <input type="text" id="kwSearch" placeholder="🔍 Search keyword..." oninput="filterTable()" style="padding:8px 12px;border-radius:6px;border:1px solid var(--border);background:#F1F5F9;color:var(--text);font-size:13px;width:260px;">
      <span style="font-size:12px;color:var(--muted);margin-left:12px">Click column headers to sort</span>
    </div>
    <table class="rank-table" id="rankTable">
      <thead>
        <tr>
          <th style="text-align:center;width:40px">Sr.</th>
          <th onclick="sortTable(1)" style="cursor:pointer;white-space:nowrap">Keyword <span class="sort-icon">⇅</span></th>
          <th onclick="sortTable(2)" style="cursor:pointer;text-align:center;white-space:nowrap">Current <span class="sort-icon">⇅</span></th>
          <th onclick="sortTable(3)" style="cursor:pointer;text-align:center;white-space:nowrap">Previous <span class="sort-icon">⇅</span></th>
          <th style="white-space:nowrap">Movement</th>
          <th onclick="sortTable(5)" style="cursor:pointer;white-space:nowrap">Volume <span class="sort-icon">⇅</span></th>
          <th style="white-space:nowrap">Ranking URL</th>
        </tr>
      </thead>
      <tbody id="rankTableBody">
        {rank_rows_html}
      </tbody>
    </table>
  </div>
  <script>
  var sortDir = {{}};
  function sortTable(col) {{
    var tbody = document.getElementById("rankTableBody");
    var rows = Array.from(tbody.querySelectorAll("tr"));
    var asc = !sortDir[col];
    sortDir = {{}};
    sortDir[col] = asc;
    rows.sort(function(a, b) {{
      var av = a.cells[col] ? a.cells[col].innerText.trim() : "";
      var bv = b.cells[col] ? b.cells[col].innerText.trim() : "";
      var an = parseFloat(av.replace(/[^0-9.-]/g,""));
      var bn = parseFloat(bv.replace(/[^0-9.-]/g,""));
      if (!isNaN(an) && !isNaN(bn)) {{
        return asc ? an - bn : bn - an;
      }}
      if (av === "NR") return asc ? 1 : -1;
      if (bv === "NR") return asc ? -1 : 1;
      return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    }});
    rows.forEach(function(r) {{ tbody.appendChild(r); }});
    // Update Sr. numbers after sort
    rows.forEach(function(r, i) {{ if(r.cells[0]) r.cells[0].innerText = i+1; }});
  }}
  function filterTable() {{
    var q = document.getElementById("kwSearch").value.toLowerCase();
    var rows = document.getElementById("rankTableBody").querySelectorAll("tr");
    rows.forEach(function(r) {{
      var kw = r.cells[1] ? r.cells[1].innerText.toLowerCase() : "";
      r.style.display = kw.includes(q) ? "" : "none";
    }});
  }}
  </script>
  ''' if total_tracked > 0 else '''
  <div class="no-data">
    <div class="icon">📊</div>
    <p>No rank tracking data available for this client yet.</p>
  </div>
  '''}
</div>

<!-- HISTORY TAB -->
<div id="tab-history" class="section">
  {"" if not _hist_rows else f'''
  <div class="history-wrap">
    <p style="font-size:12px;color:var(--muted);padding:10px 20px;margin:0;border-bottom:1px solid var(--border);background:var(--card2);">GA4 Historical Data — Last 13 completed months</p>
    <table class="history-table">
      <thead>
        <tr>
          <th>Month</th><th>Sessions</th><th>Organic</th><th>Direct</th>
          <th>AI Traffic</th><th>Users</th><th>Pageviews</th><th>Bounce %</th>
          <th>Forms</th>
        </tr>
      </thead>
      <tbody>{_hist_rows_html}</tbody>
    </table>
  </div>
  '''}
</div>

<script>
function showTab(name) {{
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}}
const months   = {json.dumps(months)};
const sessData = {json.dumps(sess_d)};
const orgData  = {json.dumps(org_d)};
const formData = {json.dumps(form_d)};
const chLabels = {json.dumps(ch_labels)};
const chVals   = {json.dumps(ch_vals)};
const chColors = {json.dumps(ch_colors)};
const aiMonthly = {json.dumps(ai_monthly)};
const aiLabels  = {json.dumps(ai_labels)};
const aiColors  = ['#F48024','#A855F7','#6366F1','#4285F4'];
const dflt = {{
  responsive: true, maintainAspectRatio: false,
  plugins: {{ legend: {{ labels: {{ color: '#64748B', font: {{ size: 11 }} }} }} }},
  scales: {{
    x: {{ ticks: {{ color: '#64748B', font: {{ size: 10 }} }}, grid: {{ display: false }} }},
    y: {{ ticks: {{ color: '#64748B', font: {{ size: 10 }} }}, grid: {{ color: 'rgba(0,0,0,0.04)' }} }}
  }}
}};
new Chart(document.getElementById('sessChart'), {{
  type: 'bar',
  data: {{ labels: months, datasets: [
    {{ label: 'Sessions', data: sessData, backgroundColor: 'rgba(37,99,235,0.7)', borderColor: '#2563EB', borderWidth: 1, borderRadius: 4 }},
    {{ label: 'Organic',  data: orgData,  backgroundColor: 'rgba(5,150,105,0.7)', borderColor: '#059669', borderWidth: 1, borderRadius: 4 }}
  ]}},
  options: {{...dflt}}
}});
new Chart(document.getElementById('formChart'), {{
  type: 'bar',
  data: {{ labels: months, datasets: [{{ label: 'Form Submissions', data: formData, backgroundColor: 'rgba(37,99,235,0.6)', borderColor: '#2563EB', borderWidth: 1, borderRadius: 4 }}]}},
  options: {{...dflt}}
}});
new Chart(document.getElementById('aiChart'), {{
  type: 'bar',
  data: {{ labels: months, datasets: aiLabels.map((label, i) => ({{ label, data: aiMonthly[label], backgroundColor: aiColors[i]+'cc', borderColor: aiColors[i], borderWidth: 1 }})) }},
  options: {{ ...dflt, scales: {{ ...dflt.scales, x: {{ ...dflt.scales.x, stacked: true }}, y: {{ ...dflt.scales.y, stacked: true }} }} }}
}});
{"" if not gmb_has_data else f'''
new Chart(document.getElementById('gmbChart'), {{
  type: 'bar',
  data: {{ labels: {json.dumps(gmb_months_chart)}, datasets: [
    {{ label: 'Views', data: {json.dumps(gmb_views_chart)}, backgroundColor: 'rgba(5,150,105,0.7)', borderColor: '#059669', borderWidth:1, borderRadius:4 }},
    {{ label: 'Clicks', data: {json.dumps(gmb_clicks_chart)}, backgroundColor: 'rgba(37,99,235,0.7)', borderColor: '#2563EB', borderWidth:1, borderRadius:4 }},
    {{ label: 'Calls', data: {json.dumps(gmb_calls_chart)}, backgroundColor: 'rgba(217,119,6,0.7)', borderColor: '#D97706', borderWidth:1, borderRadius:4 }}
  ]}},
  options: {{...dflt}}
}});
'''}
new Chart(document.getElementById('chChart'), {{
  type: 'doughnut',
  data: {{ labels: chLabels, datasets: [{{ data: chVals, backgroundColor: chColors, borderColor: '#ffffff', borderWidth: 2 }}]}},
  options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ color: '#64748B', font: {{ size: 11 }}, boxWidth: 12 }} }} }} }}
}});
</script>


<!-- RANKINGS TAB -->
<div id="tab-rankings" class="section">
  {(f'''<div class=\"rank-bucket-wrap\"><table class=\"rank-bucket-table\"><thead><tr><th>Position Bucket</th><th style=\"text-align:center\">Current</th><th style=\"text-align:center\">Previous</th><th style=\"text-align:center\">Change</th></tr></thead><tbody><tr><td>&#127947; Top 10</td><td style=\"text-align:center;color:#4ade80;font-weight:600\">{top10}</td><td style=\"text-align:center;color:#94a3b8\">{prev_top10}</td><td style=\"text-align:center\">{bucket_change(top10,prev_top10)}</td></tr><tr><td>&#129352; 11-20</td><td style=\"text-align:center;color:#facc15;font-weight:600\">{top20_only}</td><td style=\"text-align:center;color:#94a3b8\">{prev_top20}</td><td style=\"text-align:center\">{bucket_change(top20_only,prev_top20)}</td></tr><tr><td>&#129353; 21-50</td><td style=\"text-align:center;color:#fb923c;font-weight:600\">{top21_50}</td><td style=\"text-align:center;color:#94a3b8\">{prev_top21_50}</td><td style=\"text-align:center\">{bucket_change(top21_50,prev_top21_50)}</td></tr><tr><td>&#128200; 51-100</td><td style=\"text-align:center;color:#f87171;font-weight:600\">{top51_100}</td><td style=\"text-align:center;color:#94a3b8\">{prev_top51_100}</td><td style=\"text-align:center\">{bucket_change(top51_100,prev_top51_100)}</td></tr><tr><td>&#10060; Not Ranking</td><td style=\"text-align:center;color:#94a3b8;font-weight:600\">{not_ranking_count}</td><td style=\"text-align:center;color:#94a3b8\">{prev_nr}</td><td style=\"text-align:center\">{bucket_change(not_ranking_count,prev_nr)}</td></tr><tr><td><strong>Total Tracked</strong></td><td style=\"text-align:center;font-weight:700\">{total_tracked}</td><td style=\"text-align:center;color:#94a3b8\">{total_tracked}</td><td style=\"text-align:center;color:#94a3b8\">&mdash;</td></tr></tbody></table></div><div class=\"rank-table-wrap\"><div class=\"rank-table-header\">Keyword Rankings<span class=\"period\">Last Updated: {last_updated}</span></div><div class=\"rank-controls\"><input type=\"text\" id=\"kwSearch\" placeholder=\"Search keyword...\" oninput=\"filterTable()\" style=\"padding:8px 12px;border-radius:6px;border:1px solid var(--border);background:#F1F5F9;font-size:13px;width:260px;\"></div><table class=\"rank-table\" id=\"rankTable\"><thead><tr><th style=\"text-align:center;width:40px\">Sr.</th><th onclick=\"sortTable(1)\" style=\"cursor:pointer\">Keyword &#8645;</th><th onclick=\"sortTable(2)\" style=\"cursor:pointer;text-align:center\">Current &#8645;</th><th onclick=\"sortTable(3)\" style=\"cursor:pointer;text-align:center\">Previous &#8645;</th><th>Movement</th><th onclick=\"sortTable(5)\" style=\"cursor:pointer\">Volume &#8645;</th><th>Ranking URL</th></tr></thead><tbody id=\"rankTableBody\">{rank_rows_html}</tbody></table></div>''' if total_tracked > 0 else '<div class="no-data"><p>No rank tracking data yet.</p></div>')}
</div>


<!-- GMB TAB -->
<div id="tab-gmb" class="section">
  {(f'''<div style=\"margin-bottom:16px;\"><span style=\"font-size:15px;font-weight:700;color:var(--text);\">&#128205; Google My Business &mdash; {gmb_month}</span></div><div class=\"gmb-grid\"><div class=\"gmb-card\"><div class=\"gmb-icon\">&#128065;&#65039;</div><div class=\"gmb-val\">{gmb_views:,}</div><div class=\"gmb-label\">Total Views</div></div><div class=\"gmb-card\"><div class=\"gmb-icon\">&#128433;&#65039;</div><div class=\"gmb-val\">{gmb_clicks:,}</div><div class=\"gmb-label\">Website Clicks</div></div><div class=\"gmb-card\"><div class=\"gmb-icon\">&#128222;</div><div class=\"gmb-val\">{gmb_calls:,}</div><div class=\"gmb-label\">Phone Calls</div></div><div class=\"gmb-card\"><div class=\"gmb-icon\">&#128506;&#65039;</div><div class=\"gmb-val\">{gmb_directions:,}</div><div class=\"gmb-label\">Direction Requests</div></div><div class=\"gmb-card\"><div class=\"gmb-icon\">&#128221;</div><div class=\"gmb-val\">{gmb_posts}</div><div class=\"gmb-label\">GMB Posts</div></div><div class=\"gmb-card\"><div class=\"gmb-icon\">&#11088;</div><div class=\"gmb-val\">{gmb_rating}</div><div class=\"gmb-label\">Avg Rating</div></div><div class=\"gmb-card\"><div class=\"gmb-icon\">&#128172;</div><div class=\"gmb-val\">{gmb_reviews}</div><div class=\"gmb-label\">New Reviews</div></div></div><div class=\"chart-card\" style=\"margin-top:16px;\"><div class=\"chart-title\">GMB Performance &mdash; Last 6 Months</div><div class=\"chart-wrap\"><canvas id=\"gmbChart\"></canvas></div></div>''' if gmb_has_data else '<div class="no-data"><div style="font-size:48px;margin-bottom:16px">&#128205;</div><p style="font-size:15px;font-weight:600;color:#374151;margin-bottom:8px">GMB Data Coming Soon</p><p style="font-size:13px;color:#6B7280">API access requested.</p></div>')}
</div>


<!-- SEO TASKS TAB -->
<div id="tab-tasks" class="section">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px;">
    <div>
      <div style="font-size:16px;font-weight:700;color:var(--text);">SEO Work Done &mdash; {last_month_str}</div>
      <div style="font-size:12px;color:var(--muted);margin-top:3px;">Delivered by ThirdSlash Digital Marketing Agency</div>
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;">
      <div style="background:#D1FAE5;color:#065F46;padding:6px 14px;border-radius:8px;font-size:12px;font-weight:600;">&#10003; {_tasks_done} Completed</div>
      <div style="background:#FEF3C7;color:#92400E;padding:6px 14px;border-radius:8px;font-size:12px;font-weight:600;">&#8635; {_tasks_prog} In Progress</div>
      <div style="background:#F1F5F9;color:#64748B;padding:6px 14px;border-radius:8px;font-size:12px;font-weight:600;">&#9675; {_tasks_pending} Pending</div>
    </div>
  </div>
  {('<div class="rank-table-wrap"><div class="rank-table-header" style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);color:#fff;"><span>Monthly SEO Activities</span><span style="font-size:11px;opacity:0.8;font-weight:400;">ThirdSlash &mdash; ' + last_month_str + '</span></div><table class="rank-table" style="min-width:700px;"><thead><tr><th style="text-align:center;width:40px">Sr.</th><th>Task Name</th><th style="text-align:center;width:120px">Assigned To</th><th style="text-align:center;width:130px">Status</th><th style="text-align:center;width:80px">Reference</th><th style="width:180px">Notes</th></tr></thead><tbody>' + _task_rows_html + '</tbody></table></div>')
  if _tasks else '<div class="no-data"><div style="font-size:48px;margin-bottom:16px">&#128203;</div><p style="font-size:15px;font-weight:600;color:#374151;margin-bottom:8px">No tasks recorded yet</p><p style="font-size:13px;color:#6B7280">Your team will update this monthly in Google Sheets.</p></div>'}
</div>


<!-- LINK BUILDING TAB -->
<div id="tab-linkbuilding" class="section">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px;">
    <div>
      <div style="font-size:16px;font-weight:700;color:var(--text);">Link Building &mdash; {last_month_str}</div>
      <div style="font-size:12px;color:var(--muted);margin-top:3px;">Reddit, Quora, Blog Comments &amp; Directories by ThirdSlash</div>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <div style="background:#FFF7ED;border:1px solid #FED7AA;color:#C2410C;padding:5px 12px;border-radius:8px;font-size:12px;font-weight:600;">Reddit: {len(_reddit)}</div>
      <div style="background:#F5F3FF;border:1px solid #DDD6FE;color:#6D28D9;padding:5px 12px;border-radius:8px;font-size:12px;font-weight:600;">Quora: {len(_quora)}</div>
      <div style="background:#EFF6FF;border:1px solid #BFDBFE;color:#1D4ED8;padding:5px 12px;border-radius:8px;font-size:12px;font-weight:600;">Blog: {len(_blogs)}</div>
      <div style="background:#F0FDF4;border:1px solid #BBF7D0;color:#15803D;padding:5px 12px;border-radius:8px;font-size:12px;font-weight:600;">Dirs: {len(_dirs)}</div>
    </div>
  </div>
  <div class="rank-table-wrap">
    <div class="rank-table-header" style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);color:#fff;display:flex;justify-content:space-between;align-items:center;">
      <span>All Link Building Activity &mdash; {last_month_str}</span>
      <div style="display:flex;gap:6px;align-items:center;">
        <select id="lbType" onchange="filterLB()" style="background:rgba(255,255,255,0.15);color:#fff;border:1px solid rgba(255,255,255,0.3);border-radius:6px;padding:3px 8px;font-size:12px;">
          <option value="all">All Types</option>
          <option value="Reddit">Reddit</option>
          <option value="Quora">Quora</option>
          <option value="Blog Comment">Blog Comments</option>
          <option value="Directory">Directories</option>
        </select>
        <select id="lbStatus" onchange="filterLB()" style="background:rgba(255,255,255,0.15);color:#fff;border:1px solid rgba(255,255,255,0.3);border-radius:6px;padding:3px 8px;font-size:12px;">
          <option value="all">All Status</option>
          <option value="Live">Live</option>
          <option value="Approved">Approved</option>
          <option value="Pending">Pending</option>
          <option value="Not Approved">Not Approved</option>
        </select>
      </div>
    </div>
    <table class="rank-table" style="min-width:900px;">
      <thead><tr style="background:#F8FAFC;">
        <th style="text-align:center;width:40px">Sr.</th>
        <th style="width:110px">Type</th>
        <th>URL</th>
        <th style="width:130px">Anchor Text</th>
        <th style="width:160px">Linking To</th>
        <th style="text-align:center;width:70px">Live Link</th>
        <th style="text-align:center;width:120px">Status</th>
        <th style="width:130px">Comment</th>
      </tr></thead>
      <tbody id="lbBody">{_lb_combined_html}</tbody>
    </table>
  </div>
</div>

{"" if not gmb_has_data else f'''<script>new Chart(document.getElementById(\'gmbChart\'), {{  type: \'bar\', data: {{ labels: ''' + json.dumps(gmb_months_chart) + ''', datasets: [{{ label: \'Views\', data: ''' + json.dumps(gmb_views_chart) + ''', backgroundColor: \'rgba(5,150,105,0.7)\', borderColor: \'#059669\', borderWidth:1, borderRadius:4 }},{{ label: \'Clicks\', data: ''' + json.dumps(gmb_clicks_chart) + ''', backgroundColor: \'rgba(37,99,235,0.7)\', borderColor: \'#2563EB\', borderWidth:1, borderRadius:4 }},{{ label: \'Calls\', data: ''' + json.dumps(gmb_calls_chart) + ''', backgroundColor: \'rgba(217,119,6,0.7)\', borderColor: \'#D97706\', borderWidth:1, borderRadius:4 }}], }}, options: {{...dflt}} }});</script>''' if gmb_has_data else ""}

</body>
</html>"""
    html += "\n<script>\nvar sortDir = {};\nvar taskSortDir = {};\nvar lbSortDir = {};\nvar _gmbDone = false;\nfunction showTab(name, el) {\n  document.querySelectorAll('.section').forEach(function(s){s.classList.remove('active');});\n  document.querySelectorAll('.nav-tab').forEach(function(t){t.classList.remove('active');});\n  document.getElementById('tab-' + name).classList.add('active');\n  if(el) el.classList.add('active');\n  if(name === 'gmb' && !_gmbDone && typeof initGmbChart === 'function') { initGmbChart(); _gmbDone = true; }\n}\nfunction sortTable(col) {\n  var tbody = document.getElementById('rankTableBody');\n  if(!tbody) return;\n  var rows = Array.from(tbody.querySelectorAll('tr'));\n  var asc = !sortDir[col]; sortDir = {}; sortDir[col] = asc;\n  rows.sort(function(a,b){\n    var av=a.cells[col]?a.cells[col].innerText.trim():'';\n    var bv=b.cells[col]?b.cells[col].innerText.trim():'';\n    var an=parseFloat(av.replace(/[^0-9.-]/g,'')); var bn=parseFloat(bv.replace(/[^0-9.-]/g,''));\n    if(!isNaN(an)&&!isNaN(bn)) return asc?an-bn:bn-an;\n    if(av==='NR') return asc?1:-1; if(bv==='NR') return asc?-1:1;\n    return asc?av.localeCompare(bv):bv.localeCompare(av);\n  });\n  rows.forEach(function(r){tbody.appendChild(r);});\n  rows.forEach(function(r,i){if(r.cells[0])r.cells[0].innerText=i+1;});\n}\nfunction filterTable() {\n  var q=document.getElementById('kwSearch').value.toLowerCase();\n  document.getElementById('rankTableBody').querySelectorAll('tr').forEach(function(r){\n    r.style.display=(r.cells[1]?r.cells[1].innerText.toLowerCase():'').includes(q)?'':'none';\n  });\n}\nfunction sortTaskTable(col) {\n  var tbody=document.getElementById('taskBody');\n  if(!tbody) return;\n  var rows=Array.from(tbody.querySelectorAll('tr'));\n  var asc=!taskSortDir[col]; taskSortDir={}; taskSortDir[col]=asc;\n  rows.sort(function(a,b){var av=a.cells[col]?a.cells[col].innerText.trim():'';var bv=b.cells[col]?b.cells[col].innerText.trim():'';return asc?av.localeCompare(bv):bv.localeCompare(av);});\n  rows.forEach(function(r,i){tbody.appendChild(r);if(r.cells[0])r.cells[0].innerText=i+1;});\n}\nfunction filterLB() {\n  var t=document.getElementById('lbType').value;\n  var s=document.getElementById('lbStatus').value;\n  var sr=1;\n  document.getElementById('lbBody').querySelectorAll('tr').forEach(function(r){\n    var rt=r.getAttribute('data-type')||'';\n    var rs=r.getAttribute('data-status')||'';\n    var show=(t==='all'||rt===t)&&(s==='all'||rs===s);\n    r.style.display=show?'':'none';\n    if(show&&r.cells[0])r.cells[0].innerText=sr++;\n  });\n}\nfunction sortLBTable(col) {\n  var tbody=document.getElementById('lbBody');\n  if(!tbody) return;\n  var rows=Array.from(tbody.querySelectorAll('tr')).filter(function(r){return r.style.display!=='none';});\n  var asc=!lbSortDir[col]; lbSortDir={}; lbSortDir[col]=asc;\n  rows.sort(function(a,b){var av=a.cells[col]?a.cells[col].innerText.trim():'';var bv=b.cells[col]?b.cells[col].innerText.trim():'';return asc?av.localeCompare(bv):bv.localeCompare(av);});\n  rows.forEach(function(r,i){tbody.appendChild(r);if(r.cells[0])r.cells[0].innerText=i+1;});\n}\n</script>\n"
    return html


def main():
    print("ThirdSlash Dashboard Generator")
    print("=" * 50)
    gc = gspread.authorize(load_creds())
    print("Loading sheet data...")
    ga4_rows, rank_rows, gmb_rows, tasks_rows, lb_rows = get_sheet_data(gc)
    print(f"GA4 rows: {len(ga4_rows)} | Rank rows: {len(rank_rows)}")

    # Load backlinks data if available
    backlinks_file = os.path.join(BASE, "backlinks_data.json")
    all_backlinks = {}
    if os.path.exists(backlinks_file):
        with open(backlinks_file) as f:
            all_backlinks = json.load(f)
        print(f"Backlinks data loaded for {len(all_backlinks)} clients.")
    else:
        print("No backlinks_data.json found — run pull_backlinks.py first.")

    os.makedirs(DASH_DIR, exist_ok=True)
    generated = 0

    for client_name, slug in CLIENTS.items():
        client_ga4   = build_client_ga4(ga4_rows, client_name)
        client_ranks = build_client_ranks(rank_rows, client_name)

        if not client_ga4:
            print(f"  {client_name:25} — no GA4 data, generating keywords-only dashboard")

        client_gmb       = [r for r in gmb_rows   if r.get("Client Name") == client_name]
        client_tasks     = [r for r in tasks_rows if r.get("Client Name") == client_name]
        client_lb        = [r for r in lb_rows    if r.get("Client Name") == client_name]
        client_backlinks = all_backlinks.get(client_name, {})
        html = build_html(client_name, client_ga4, client_ranks, client_gmb, client_tasks, client_lb, client_backlinks)
        client_dir = os.path.join(DASH_DIR, slug)
        os.makedirs(client_dir, exist_ok=True)
        out = os.path.join(client_dir, "index.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        rank_count = len(client_ranks)
        print(f"  {client_name:25} ✓  {len(client_ga4)} months GA4 | {rank_count} kws")
        generated += 1


    # Generate master agency index
    now_label = __import__('datetime').datetime.now().strftime('%b %Y')
    active_clients = [(name, slug) for name, slug in CLIENTS.items()]

    # Build per-client summary data
    from datetime import datetime as _idt
    def _parse_m(m):
        try: return _idt.strptime(m, "%b-%Y")
        except: return _idt.min

    cur_month = _idt.now().strftime("%b-%Y")

    # Domain map
    domain_map = {r.get("Client Name"): r.get("Domain","") for r in rank_rows}

    cards_html = ""
    total_sessions = 0
    total_keywords = 0
    total_top10 = 0

    for name, slug in active_clients:
        # GA4 data
        cga4 = [r for r in ga4_rows if r.get("Client Name") == name and r.get("Month","") != cur_month]
        cga4_sorted = sorted(cga4, key=lambda x: _parse_m(x.get("Month","")), reverse=True)
        latest_ga4 = cga4_sorted[0] if cga4_sorted else {}
        org = int(latest_ga4.get("Organic Sessions", 0) or 0)
        ai  = int(latest_ga4.get("ChatGPT Sessions", 0) or 0) + int(latest_ga4.get("Claude Sessions", 0) or 0) + int(latest_ga4.get("Perplexity Sessions", 0) or 0) + int(latest_ga4.get("Gemini Sessions", 0) or 0) + int(latest_ga4.get("Copilot Sessions", 0) or 0)
        sessions = org + ai
        latest_month = latest_ga4.get("Month", "—")
        total_sessions += sessions

        # Rank data
        cranks = [r for r in rank_rows if r.get("Client Name") == name]
        kw_total = len(cranks)
        kw_top10 = len([r for r in cranks if str(r.get("Status","")) == "Ranking" and
                        isinstance(r.get("Current Position",""), int) and r.get("Current Position",999) <= 10])
        kw_ranking = len([r for r in cranks if str(r.get("Status","")) == "Ranking"])
        total_keywords += kw_total
        total_top10 += kw_top10

        domain = domain_map.get(name, "")
        sessions_fmt = f"{int(sessions):,}" if sessions else "—"

        # Card status color
        status_color = "#4ade80" if kw_ranking > 0 else "#94a3b8"
        status_label = f"{kw_ranking} Ranking" if kw_ranking > 0 else "No Rankings Yet"

        cards_html += f"""
        <a href="{slug}/" class="card">
          <div class="card-header">
            <div class="card-name">{name}</div>
            <div class="card-domain">{domain}</div>
          </div>
          <div class="card-stats">
            <div class="card-stat">
              <div class="cs-val">{sessions_fmt}</div>
              <div class="cs-label">SEO+AI Traffic</div>
              <div class="cs-period">{latest_month}</div>
            </div>
            <div class="card-stat">
              <div class="cs-val">{kw_top10}</div>
              <div class="cs-label">Top 10</div>
            </div>
            <div class="card-stat">
              <div class="cs-val">{kw_total}</div>
              <div class="cs-label">Keywords</div>
            </div>
          </div>
          <div class="card-footer">
            <span class="card-status" style="color:{status_color};background:{'#F0FDF4' if kw_ranking > 0 else '#F1F5F9'};padding:3px 8px;border-radius:20px;font-weight:600;border:1px solid {'#BBF7D0' if kw_ranking > 0 else '#E2E8F0'}">&bull; {status_label}</span>
            <span class="card-cta">View Dashboard →</span>
          </div>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ThirdSlash | SEO Client Dashboards</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:'Inter',sans-serif;background:#F8F9FA;color:#111827;min-height:100vh;}}
header{{background:#ffffff;border-bottom:1px solid #E5E7EB;padding:16px 40px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 1px 3px rgba(0,0,0,0.04);}}
.logo{{font-size:16px;font-weight:800;letter-spacing:3px;color:#2563EB;}}
.meta{{font-size:12px;color:#6B7280;display:flex;gap:16px;align-items:center;}}
.meta-dot{{width:6px;height:6px;border-radius:50%;background:#16A34A;display:inline-block;margin-right:4px;}}
.hero{{padding:40px 40px 24px;}}
h1{{font-size:28px;font-weight:700;margin-bottom:6px;color:#111827;}}
h1 span{{color:#2563EB;}}
.subtitle{{color:#6B7280;font-size:13px;margin-bottom:32px;}}
.stats{{display:flex;gap:16px;margin-bottom:32px;flex-wrap:wrap;}}
.stat{{background:#ffffff;border:1px solid #E5E7EB;border-radius:8px;padding:16px 24px;min-width:130px;box-shadow:0 1px 3px rgba(0,0,0,0.04);border-top:3px solid #2563EB;}}
.stat-num{{font-size:24px;font-weight:700;color:#2563EB;}}
.stat-label{{font-size:11px;color:#6B7280;margin-top:3px;text-transform:uppercase;letter-spacing:1px;}}
.search-wrap{{padding:0 40px 20px;}}
.search-box{{width:100%;max-width:400px;padding:10px 16px;background:#ffffff;border:1px solid #E5E7EB;border-radius:8px;color:#111827;font-size:13px;outline:none;box-shadow:0 1px 2px rgba(0,0,0,0.04);}}
.search-box:focus{{border-color:#2563EB;box-shadow:0 0 0 3px rgba(37,99,235,0.1);}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;padding:0 40px 60px;}}
.card{{background:#ffffff;border:1px solid #E5E7EB;border-radius:10px;padding:20px;text-decoration:none;color:inherit;transition:box-shadow .2s,transform .15s,border-color .2s;display:flex;flex-direction:column;gap:14px;box-shadow:0 1px 3px rgba(0,0,0,0.04);}}
.card:hover{{border-color:#2563EB;transform:translateY(-2px);box-shadow:0 4px 16px rgba(37,99,235,0.1);}}
.card-header{{display:flex;flex-direction:column;gap:3px;}}
.card-name{{font-size:15px;font-weight:600;color:#111827;}}
.card-domain{{font-size:11px;color:#6B7280;}}
.card-stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;background:#F8F9FA;border-radius:8px;padding:12px;border:1px solid #E5E7EB;}}
.card-stat{{text-align:center;}}
.cs-val{{font-size:18px;font-weight:700;color:#2563EB;}}
.cs-label{{font-size:10px;color:#6B7280;text-transform:uppercase;letter-spacing:0.5px;margin-top:2px;}}
.cs-period{{font-size:9px;color:#9CA3AF;margin-top:1px;}}
.card-footer{{display:flex;justify-content:space-between;align-items:center;}}
.card-status{{font-size:11px;background:#EFF6FF;color:#2563EB;padding:3px 8px;border-radius:20px;font-weight:600;border:1px solid #BFDBFE;}}
.card-cta{{font-size:11px;color:#2563EB;font-weight:600;}}
footer{{text-align:center;padding:24px;color:#9CA3AF;font-size:12px;border-top:1px solid #E5E7EB;}}
@media(max-width:768px){{
  .hero,.search-wrap,.grid{{padding-left:16px;padding-right:16px;}}
  header{{padding:12px 16px;}}
  .grid{{grid-template-columns:1fr;}}
}}
</style>
</head>
<body>
<header>
<div class="logo">THIRDSLASH</div>
<div class="meta">
  <span><span class="meta-dot"></span>Live Dashboards</span>
  <span>{len(active_clients)} Active Clients</span>
  <span>Updated: {now_label}</span>
</div>
</header>
<div class="hero">
<h1>SEO Client <span>Dashboards</span></h1>
<p class="subtitle">Agency Command Center — all client data in one place</p>
<div class="stats">
  <div class="stat"><div class="stat-num">{len(active_clients)}</div><div class="stat-label">Active Clients</div></div>
  <div class="stat"><div class="stat-num">{total_keywords:,}</div><div class="stat-label">Keywords Tracked</div></div>
  <div class="stat"><div class="stat-num">{total_top10:,}</div><div class="stat-label">Top 10 Rankings</div></div>
  <div class="stat"><div class="stat-num">{total_sessions:,}</div><div class="stat-label">SEO+AI Traffic</div></div>
</div>
</div>
<div class="search-wrap">
  <input class="search-box" type="text" placeholder="🔍 Search client or domain..." oninput="filterCards(this.value)">
</div>
<div class="grid" id="clientGrid">{cards_html}
</div>
<footer>ThirdSlash Digital Marketing Agency &mdash; All dashboards auto-update monthly &mdash; Data: GA4 + Ubersuggest</footer>
<script>
function filterCards(q){{
  q = q.toLowerCase();
  document.querySelectorAll('#clientGrid .card').forEach(function(c){{
    var t = c.innerText.toLowerCase();
    c.style.display = t.includes(q) ? '' : 'none';
  }});
}}
</script>





</body>
</html>"""

    index_path = os.path.join(DASH_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"  Master index → {index_path}")

    print(f"\nGenerated {generated} dashboards → {DASH_DIR}")
    print("\nPush to GitHub:")
    print("  cd ~/ThirdSlash_SEO_Dashboards && git add -A && git commit -m 'Update dashboards with fresh rankings' && git push")

if __name__ == "__main__":
    main()
