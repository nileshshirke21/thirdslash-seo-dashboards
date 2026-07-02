#!/usr/bin/env python3
"""
Generate Tech Audit HTML tab from Screaming Frog CSV exports.
Output is an HTML string to embed inside <div id="tab-techaudit" class="section">.
"""

import csv
import json
import os
import re
from datetime import datetime


def _read_csv(path):
    """Read a CSV file and return list of dicts. Handles BOM."""
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception:
        return []


def _count_rows(path):
    """Count data rows in a CSV."""
    return len(_read_csv(path))


def _get_addresses(path):
    """Extract Address column values from a CSV."""
    rows = _read_csv(path)
    return [r.get("Address", r.get("﻿Address", "")) for r in rows if r.get("Address", r.get("﻿Address", ""))]


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _calc_health_score(issues):
    """Calculate health score from detected issues."""
    score = 100
    counts = {i["id_key"]: i["count"] for i in issues}

    # 404 errors
    c = counts.get("404_errors", 0)
    if c > 50:
        score -= 25
    elif c > 0:
        score -= 15

    # 5xx errors
    c = counts.get("5xx_errors", 0)
    if c > 20:
        score -= 25
    elif c > 0:
        score -= 15

    # Redirects
    c = counts.get("3xx_redirects", 0)
    if c > 100:
        score -= 10
    elif c > 50:
        score -= 5

    # Title issues (long + short + missing)
    c = counts.get("title_long", 0) + counts.get("title_short", 0) + counts.get("title_missing", 0)
    score -= min(15, 5 * (c // 10))

    # Meta desc issues
    c = counts.get("meta_missing", 0) + counts.get("meta_long", 0) + counts.get("meta_short", 0)
    score -= min(10, 5 * (c // 10))

    # H1 missing
    c = counts.get("h1_missing", 0) + counts.get("h1_duplicate", 0)
    score -= min(10, 5 * (c // 10))

    # Thin content
    c = counts.get("thin_content", 0)
    score -= min(10, 5 * (c // 5))

    # Noindex
    c = counts.get("noindex", 0)
    score -= min(5, 2 * (c // 5))

    # Missing canonical
    c = counts.get("missing_canonical", 0)
    score -= min(6, 3 * c)

    return max(0, score)


def generate_tech_audit_html(crawl_dir, client_name, domain, audit_date):
    """
    Generate Tech Audit HTML section from Screaming Frog CSV exports.

    Args:
        crawl_dir: Path to directory containing SF CSV exports
        client_name: Client name (e.g. "Asset Thread")
        domain: Domain (e.g. "assetthread.com")
        audit_date: Date string (e.g. "2026-06-19")

    Returns:
        HTML string for embedding in the dashboard tech audit tab.
    """
    client_slug = _slug(client_name)
    dt = datetime.strptime(audit_date, "%Y-%m-%d")
    month_year = dt.strftime("%b_%Y").lower()
    ls_key = f"{client_slug}_techaudit_{month_year}"

    # --- Read CSVs ---
    internal_html = _read_csv(os.path.join(crawl_dir, "internal_html.csv"))
    total_html = len(internal_html)
    ok_200 = sum(1 for r in internal_html if r.get("Status Code", "") == "200")
    indexable = sum(1 for r in internal_html if r.get("Indexability", "").strip().lower() == "indexable")

    # --- Define issue specs ---
    issue_specs = [
        {
            "id_key": "404_errors",
            "csv": "response_codes_client_error_(4xx).csv",
            "title_tpl": "{n} pages returning 404 errors",
            "cat": "errors", "prio": "high", "pill": "ta-pill-red", "btn": "ta-btn-red",
            "plain": "These pages return a 404 Not Found status. Search engines will deindex them and users hitting these URLs get a dead end.",
            "fix": "Set up 301 redirects to the most relevant live page. If the content was removed intentionally, ensure proper 410 Gone status and update internal links.",
            "devNote": "dev", "own": "Developer", "stat": "Under Review",
        },
        {
            "id_key": "5xx_errors",
            "csv": "response_codes_server_error_(5xx).csv",
            "title_tpl": "{n} pages returning 5xx server errors",
            "cat": "errors", "prio": "high", "pill": "ta-pill-red", "btn": "ta-btn-red",
            "plain": "Server errors prevent both users and search engines from accessing these pages. Persistent 5xx errors signal instability to Google.",
            "fix": "Investigate server logs for root cause. Common fixes: increase server resources, fix broken database queries, or resolve plugin conflicts.",
            "devNote": "dev", "own": "Developer", "stat": "Under Review",
        },
        {
            "id_key": "3xx_redirects",
            "csv": "response_codes_redirection_(3xx).csv",
            "title_tpl": "{n} pages with 3xx redirects",
            "cat": "technical", "prio": "medium", "pill": "ta-pill-amber", "btn": "ta-btn-amber",
            "plain": "Redirect chains waste crawl budget and dilute link equity. Too many redirects slow down page discovery.",
            "fix": "Update internal links to point directly to the final destination URL. Remove unnecessary redirect hops. Consolidate redirect chains to single 301s.",
            "devNote": "dev", "own": "Developer", "stat": "Under Review",
        },
        {
            "id_key": "title_long",
            "csv": "page_titles_over_60_characters.csv",
            "title_tpl": "{n} pages with titles over 60 characters",
            "cat": "onpage", "prio": "medium", "pill": "ta-pill-amber", "btn": "ta-btn-amber",
            "plain": "Titles longer than 60 characters get truncated in Google search results, reducing click-through rates.",
            "fix": "Rewrite titles to be under 60 characters while keeping the primary keyword near the front. Remove filler words.",
            "devNote": "seo", "own": "ThirdSlash", "stat": "Under Review",
        },
        {
            "id_key": "title_missing",
            "csv": "page_titles_missing.csv",
            "title_tpl": "{n} pages with missing titles",
            "cat": "onpage", "prio": "high", "pill": "ta-pill-red", "btn": "ta-btn-red",
            "plain": "Pages without title tags cannot rank effectively. Google will auto-generate a title which is often inaccurate.",
            "fix": "Add a unique, descriptive <title> tag to each page that includes the target keyword.",
            "devNote": "seo", "own": "ThirdSlash", "stat": "Under Review",
        },
        {
            "id_key": "title_short",
            "csv": "page_titles_below_30_characters.csv",
            "title_tpl": "{n} pages with titles below 30 characters",
            "cat": "onpage", "prio": "low", "pill": "ta-pill-blue", "btn": "ta-btn-blue",
            "plain": "Very short titles miss the opportunity to include relevant keywords and may not clearly describe the page content.",
            "fix": "Expand titles to include the primary keyword, a modifier, and the brand name where appropriate.",
            "devNote": "seo", "own": "ThirdSlash", "stat": "Under Review",
        },
        {
            "id_key": "meta_missing",
            "csv": "meta_description_missing.csv",
            "title_tpl": "{n} pages with missing meta descriptions",
            "cat": "onpage", "prio": "medium", "pill": "ta-pill-amber", "btn": "ta-btn-amber",
            "plain": "Missing meta descriptions mean Google auto-generates the snippet. This often results in less compelling search result listings.",
            "fix": "Write unique meta descriptions (70-155 characters) for each page that include the target keyword and a clear call to action.",
            "devNote": "seo", "own": "ThirdSlash", "stat": "Under Review",
        },
        {
            "id_key": "meta_long",
            "csv": "meta_description_over_155_characters.csv",
            "title_tpl": "{n} pages with meta descriptions over 155 characters",
            "cat": "onpage", "prio": "low", "pill": "ta-pill-blue", "btn": "ta-btn-blue",
            "plain": "Meta descriptions over 155 characters get truncated in search results, cutting off your message mid-sentence.",
            "fix": "Trim meta descriptions to 155 characters or fewer. Front-load the most important information and CTA.",
            "devNote": "seo", "own": "ThirdSlash", "stat": "Under Review",
        },
        {
            "id_key": "meta_short",
            "csv": "meta_description_below_70_characters.csv",
            "title_tpl": "{n} pages with meta descriptions below 70 characters",
            "cat": "onpage", "prio": "low", "pill": "ta-pill-blue", "btn": "ta-btn-blue",
            "plain": "Very short meta descriptions waste valuable SERP real estate and miss the chance to persuade users to click.",
            "fix": "Expand meta descriptions to at least 70 characters with a compelling summary and call to action.",
            "devNote": "seo", "own": "ThirdSlash", "stat": "Under Review",
        },
        {
            "id_key": "h1_missing",
            "csv": "h1_missing.csv",
            "title_tpl": "{n} pages with missing H1 tags",
            "cat": "onpage", "prio": "high", "pill": "ta-pill-red", "btn": "ta-btn-red",
            "plain": "The H1 tag is the primary heading signal for search engines. Missing H1s weaken topical relevance and hurt rankings.",
            "fix": "Add a single, unique H1 tag to each page that includes the primary keyword and clearly describes the page topic.",
            "devNote": "both", "own": "Developer", "stat": "Under Review",
        },
        {
            "id_key": "h1_duplicate",
            "csv": "h1_duplicate.csv",
            "title_tpl": "{n} pages with duplicate H1 tags",
            "cat": "onpage", "prio": "medium", "pill": "ta-pill-amber", "btn": "ta-btn-amber",
            "plain": "Multiple H1 tags on a page dilute the heading hierarchy and confuse search engines about the primary topic.",
            "fix": "Ensure each page has exactly one H1 tag. Demote additional H1s to H2 or H3 as appropriate.",
            "devNote": "dev", "own": "Developer", "stat": "Under Review",
        },
        {
            "id_key": "noindex",
            "csv": "directives_noindex.csv",
            "title_tpl": "{n} pages set to noindex",
            "cat": "technical", "prio": "medium", "pill": "ta-pill-amber", "btn": "ta-btn-amber",
            "plain": "These pages are explicitly blocked from appearing in search results. Verify this is intentional for each page.",
            "fix": "Review each noindexed page. If it should be indexed, remove the noindex directive. Common false positives: staging tags left on production pages.",
            "devNote": "seo", "own": "ThirdSlash", "stat": "Under Review",
        },
        {
            "id_key": "missing_canonical",
            "csv": "canonicals_missing.csv",
            "title_tpl": "{n} pages with missing canonical tags",
            "cat": "technical", "prio": "high", "pill": "ta-pill-red", "btn": "ta-btn-red",
            "plain": "Without canonical tags, search engines may index duplicate versions of these pages, splitting ranking signals.",
            "fix": "Add a self-referencing canonical tag to each page. For duplicate content, point the canonical to the preferred version.",
            "devNote": "dev", "own": "Developer", "stat": "Under Review",
        },
        {
            "id_key": "thin_content",
            "csv": "content_low_content_pages.csv",
            "title_tpl": "{n} pages with thin / low content",
            "cat": "content", "prio": "medium", "pill": "ta-pill-amber", "btn": "ta-btn-amber",
            "plain": "Pages with very little content provide minimal value to users and are unlikely to rank. Google may flag these as low-quality.",
            "fix": "Expand content to at least 300 words with useful, unique information. If the page serves no purpose, consider consolidating or removing it.",
            "devNote": "seo", "own": "ThirdSlash", "stat": "Under Review",
        },
    ]

    # --- Build issues list ---
    issues = []
    all_urls_map = {}
    idx = 0
    for spec in issue_specs:
        csv_path = os.path.join(crawl_dir, spec["csv"])
        count = _count_rows(csv_path)
        if count == 0:
            continue
        idx += 1
        iid = f"i{idx:02d}"
        urls = _get_addresses(csv_path)
        all_urls_map[iid] = urls
        issues.append({
            "id": iid,
            "id_key": spec["id_key"],
            "cat": spec["cat"],
            "prio": spec["prio"],
            "title": spec["title_tpl"].format(n=count),
            "count": count,
            "pill": spec["pill"],
            "src": ["SF"],
            "btn": spec["btn"],
            "plain": spec["plain"],
            "fix": spec["fix"],
            "devNote": spec["devNote"],
            "own": spec["own"],
            "stat": spec["stat"],
        })

    health_score = _calc_health_score(issues)

    # Counts for metric cards
    count_404 = _count_rows(os.path.join(crawl_dir, "response_codes_client_error_(4xx).csv"))
    count_5xx = _count_rows(os.path.join(crawl_dir, "response_codes_server_error_(5xx).csv"))
    count_3xx = _count_rows(os.path.join(crawl_dir, "response_codes_redirection_(3xx).csv"))
    count_title_issues = sum(1 for i in issues if i["id_key"] in ("title_long", "title_short", "title_missing"))
    title_issue_count = sum(i["count"] for i in issues if i["id_key"] in ("title_long", "title_short", "title_missing"))
    meta_issue_count = sum(i["count"] for i in issues if i["id_key"] in ("meta_missing", "meta_long", "meta_short"))

    # Score color
    if health_score >= 80:
        score_color = "#16A34A"
        score_label = "Good"
    elif health_score >= 60:
        score_color = "#D97706"
        score_label = "Needs Work"
    else:
        score_color = "#DC2626"
        score_label = "Critical"

    # Score ring calculations
    circumference = 2 * 3.14159 * 54
    offset = circumference * (1 - health_score / 100)

    # Issues JSON for JS
    issues_json = json.dumps(issues)
    urls_json = json.dumps(all_urls_map)

    # --- Build HTML ---
    html = f"""
<style>
/* ── Tech Audit Scoped Styles ── */
.ta-wrap {{
  --navy:#1B2A4A; --orange:#F4812A; --orange-light:#FEF0E6; --bg:#F5F6F8; --card:#fff; --border:#E4E7ED;
  --text:#1A1D23; --text-muted:#6B7280; --text-light:#9CA3AF;
  --red:#DC2626; --red-bg:#FEF2F2; --red-border:#FECACA;
  --amber:#D97706; --amber-bg:#FFFBEB; --amber-border:#FDE68A;
  --green:#16A34A; --green-bg:#F0FDF4; --green-border:#BBF7D0;
  --blue:#2563EB; --blue-bg:#EFF6FF; --blue-border:#BFDBFE;
  --purple:#7C3AED; --purple-bg:#F5F3FF; --purple-border:#DDD6FE;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: var(--text);
}}
.ta-banner {{
  background: var(--navy);
  border-radius: 12px;
  padding: 32px;
  display: flex;
  align-items: center;
  gap: 32px;
  margin-bottom: 24px;
  color: #fff;
}}
.ta-score-ring {{
  position: relative;
  width: 128px;
  height: 128px;
  flex-shrink: 0;
}}
.ta-score-ring svg {{
  transform: rotate(-90deg);
}}
.ta-score-num {{
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}}
.ta-score-num .ta-big {{
  font-size: 36px;
  font-weight: 800;
  line-height: 1;
}}
.ta-score-num .ta-of {{
  font-size: 13px;
  opacity: .6;
}}
.ta-banner-text h2 {{
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 700;
}}
.ta-banner-text p {{
  margin: 0;
  opacity: .7;
  font-size: 14px;
}}
.ta-banner-text .ta-label {{
  display: inline-block;
  margin-top: 8px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}}
.ta-metrics {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}}
.ta-metric-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
}}
.ta-metric-card .ta-mc-val {{
  font-size: 28px;
  font-weight: 800;
  color: var(--navy);
}}
.ta-metric-card .ta-mc-label {{
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}}
.ta-metric-card.ta-mc-red .ta-mc-val {{ color: var(--red); }}
.ta-metric-card.ta-mc-amber .ta-mc-val {{ color: var(--amber); }}
.ta-metric-card.ta-mc-green .ta-mc-val {{ color: var(--green); }}

.ta-legend {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 24px;
  font-size: 13px;
  color: var(--text-muted);
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}}
.ta-legend span {{
  font-weight: 600;
  color: var(--navy);
}}

/* Filters */
.ta-filters {{
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  align-items: center;
}}
.ta-chip {{
  padding: 6px 16px;
  border-radius: 20px;
  border: 1px solid var(--border);
  background: var(--card);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  transition: all .15s;
}}
.ta-chip.active {{
  background: var(--navy);
  color: #fff;
  border-color: var(--navy);
}}
.ta-chip:hover {{
  border-color: var(--navy);
}}
.ta-select {{
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  font-size: 13px;
  color: var(--text);
  background: var(--card);
  cursor: pointer;
}}

/* Issue table */
.ta-table {{
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: var(--card);
  border-radius: 10px;
  border: 1px solid var(--border);
  overflow: hidden;
}}
.ta-table th {{
  background: var(--bg);
  padding: 10px 14px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--text-muted);
  text-align: left;
  border-bottom: 1px solid var(--border);
}}
.ta-table td {{
  padding: 12px 14px;
  font-size: 13px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}}
.ta-table tr:last-child td {{ border-bottom: none; }}
.ta-table tr.ta-row-issue {{ cursor: pointer; }}
.ta-table tr.ta-row-issue:hover {{ background: var(--bg); }}

/* Pills */
.ta-pill {{
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 700;
}}
.ta-pill-red {{ background: var(--red-bg); color: var(--red); border: 1px solid var(--red-border); }}
.ta-pill-amber {{ background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }}
.ta-pill-blue {{ background: var(--blue-bg); color: var(--blue); border: 1px solid var(--blue-border); }}
.ta-pill-green {{ background: var(--green-bg); color: var(--green); border: 1px solid var(--green-border); }}

/* Priority badges */
.ta-prio {{
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}}
.ta-prio-high {{ background: var(--red-bg); color: var(--red); }}
.ta-prio-medium {{ background: var(--amber-bg); color: var(--amber); }}
.ta-prio-low {{ background: var(--blue-bg); color: var(--blue); }}

/* Source tag */
.ta-src {{
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  background: var(--purple-bg);
  color: var(--purple);
  border: 1px solid var(--purple-border);
  margin-left: 4px;
}}

/* Expandable URL panel */
.ta-url-panel {{
  display: none;
}}
.ta-url-panel.open {{
  display: table-row;
}}
.ta-url-panel td {{
  background: var(--bg);
  padding: 0;
}}
.ta-url-inner {{
  padding: 12px 20px;
  max-height: 300px;
  overflow-y: auto;
}}
.ta-url-inner .ta-url-item {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
}}
.ta-url-inner .ta-url-item:last-child {{ border-bottom: none; }}
.ta-url-inner .ta-url-item a {{
  color: var(--blue);
  text-decoration: none;
  word-break: break-all;
}}
.ta-url-inner .ta-url-item a:hover {{ text-decoration: underline; }}
.ta-copy-btn {{
  background: none;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11px;
  cursor: pointer;
  color: var(--text-muted);
  flex-shrink: 0;
  margin-left: 8px;
}}
.ta-copy-btn:hover {{ background: var(--border); }}

/* Owner / Status dropdowns in table */
.ta-table select {{
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid var(--border);
  font-size: 12px;
  background: var(--card);
  cursor: pointer;
}}

/* Expand arrow */
.ta-arrow {{
  display: inline-block;
  transition: transform .2s;
  margin-right: 6px;
  font-size: 10px;
  color: var(--text-muted);
}}
.ta-arrow.open {{
  transform: rotate(90deg);
}}
</style>

<div class="ta-wrap">

  <!-- Health Score Banner -->
  <div class="ta-banner">
    <div class="ta-score-ring">
      <svg width="128" height="128" viewBox="0 0 128 128">
        <circle cx="64" cy="64" r="54" fill="none" stroke="rgba(255,255,255,.15)" stroke-width="10"/>
        <circle cx="64" cy="64" r="54" fill="none" stroke="{score_color}" stroke-width="10"
                stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{offset:.1f}"
                stroke-linecap="round"/>
      </svg>
      <div class="ta-score-num">
        <span class="ta-big">{health_score}</span>
        <span class="ta-of">/ 100</span>
      </div>
    </div>
    <div class="ta-banner-text">
      <h2>Technical SEO Health</h2>
      <p>{client_name} &middot; {domain} &middot; Screaming Frog Pro Crawl &middot; {dt.strftime("%d %b %Y")} &middot; {total_html} pages scanned</p>
      <span class="ta-label" style="background:{score_color};color:#fff">{score_label}</span>
    </div>
  </div>

  <!-- Metric Cards -->
  <div class="ta-metrics">
    <div class="ta-metric-card"><div class="ta-mc-val">{total_html}</div><div class="ta-mc-label">Total HTML Pages</div></div>
    <div class="ta-metric-card ta-mc-green"><div class="ta-mc-val">{ok_200}</div><div class="ta-mc-label">200 OK</div></div>
    <div class="ta-metric-card ta-mc-green"><div class="ta-mc-val">{indexable}</div><div class="ta-mc-label">Indexable</div></div>
    <div class="ta-metric-card {"ta-mc-red" if count_404 > 0 else ""}"><div class="ta-mc-val">{count_404}</div><div class="ta-mc-label">404 Errors</div></div>
    <div class="ta-metric-card {"ta-mc-red" if count_5xx > 0 else ""}"><div class="ta-mc-val">{count_5xx}</div><div class="ta-mc-label">5xx Errors</div></div>
    <div class="ta-metric-card {"ta-mc-amber" if count_3xx > 0 else ""}"><div class="ta-mc-val">{count_3xx}</div><div class="ta-mc-label">Redirects (3xx)</div></div>
    <div class="ta-metric-card {"ta-mc-amber" if title_issue_count > 0 else ""}"><div class="ta-mc-val">{title_issue_count}</div><div class="ta-mc-label">Title Issues</div></div>
    <div class="ta-metric-card {"ta-mc-amber" if meta_issue_count > 0 else ""}"><div class="ta-mc-val">{meta_issue_count}</div><div class="ta-mc-label">Meta Issues</div></div>
  </div>


  <!-- Filters -->
  <div class="ta-filters">
    <button class="ta-chip active" data-cat="all" onclick="taFilter(this)">All Issues</button>
    <button class="ta-chip" data-cat="errors" onclick="taFilter(this)">Errors</button>
    <button class="ta-chip" data-cat="onpage" onclick="taFilter(this)">On-Page</button>
    <button class="ta-chip" data-cat="content" onclick="taFilter(this)">Content</button>
    <button class="ta-chip" data-cat="technical" onclick="taFilter(this)">Technical</button>
    <select class="ta-select" id="ta-prio-filter" onchange="taApplyFilters()">
      <option value="all">All Priorities</option>
      <option value="high">High</option>
      <option value="medium">Medium</option>
      <option value="low">Low</option>
    </select>
    <select class="ta-select" id="ta-status-filter" onchange="taApplyFilters()">
      <option value="all">All Statuses</option>
      <option value="Under Review">Under Review</option>
      <option value="Completed">Completed</option>
      <option value="Not Completed">Not Completed</option>
      <option value="Blocked">Blocked</option>
      <option value="Waiting for Approval">Waiting for Approval</option>
      <option value="Rejected">Rejected</option>
    </select>
  </div>

  <!-- Issue Log Table -->
  <table class="ta-table" id="ta-issue-table">
    <thead>
      <tr>
        <th style="width:28%;cursor:pointer" onclick="taSortTable(0)">Issue &#8645;</th>
        <th style="width:60px;cursor:pointer" onclick="taSortTable(1)">Count &#8645;</th>
        <th style="width:80px;cursor:pointer" onclick="taSortTable(2)">Priority &#8645;</th>
        <th style="width:22%;cursor:pointer" onclick="taSortTable(3)">What This Means &#8645;</th>
        <th style="width:22%;cursor:pointer" onclick="taSortTable(4)">How to Fix It &#8645;</th>
        <th style="width:110px;cursor:pointer" onclick="taSortTable(5)">Owner &#8645;</th>
        <th style="width:130px;cursor:pointer" onclick="taSortTable(6)">Status &#8645;</th>
      </tr>
    </thead>
    <tbody>
"""

    owner_options = ["ThirdSlash", "Client", "Developer"]
    status_options = ["Under Review", "Completed", "Not Completed", "Blocked", "Waiting for Approval", "Rejected"]

    for issue in issues:
        iid = issue["id"]
        src_tags = ""

        own_select = f'<select class="ta-select ta-own-sel" data-id="{iid}" onchange="taSaveState()">'
        for opt in owner_options:
            sel = " selected" if opt == issue["own"] else ""
            own_select += f'<option value="{opt}"{sel}>{opt}</option>'
        own_select += "</select>"

        stat_select = f'<select class="ta-select ta-stat-sel" data-id="{iid}" onchange="taSaveState()">'
        for opt in status_options:
            sel = " selected" if opt == issue["stat"] else ""
            stat_select += f'<option value="{opt}"{sel}>{opt}</option>'
        stat_select += "</select>"

        html += f"""      <tr class="ta-row-issue" data-id="{iid}" data-cat="{issue['cat']}" data-prio="{issue['prio']}" onclick="taToggle('{iid}')">
        <td><span class="ta-arrow" id="ta-arrow-{iid}">&#9654;</span>{issue['title']} {src_tags}</td>
        <td><span class="ta-pill {issue['pill']}">{issue['count']}</span></td>
        <td><span class="ta-prio ta-prio-{issue['prio']}">{issue['prio'].upper()}</span></td>
        <td>{issue['plain']}</td>
        <td>{issue['fix']}</td>
        <td onclick="event.stopPropagation()">{own_select}</td>
        <td onclick="event.stopPropagation()">{stat_select}</td>
      </tr>
      <tr class="ta-url-panel" id="ta-panel-{iid}">
        <td colspan="7">
          <div class="ta-url-inner" id="ta-urls-{iid}"></div>
        </td>
      </tr>
"""

    html += """    </tbody>
  </table>
</div>

<script>
(function() {
  var LS_KEY = """ + json.dumps(ls_key) + """;
  var ALL_URLS = """ + urls_json + """;

  // Restore saved state
  function taLoadState() {
    try {
      var s = JSON.parse(localStorage.getItem(LS_KEY) || '{}');
      document.querySelectorAll('.ta-own-sel').forEach(function(el) {
        if (s[el.dataset.id] && s[el.dataset.id].own) el.value = s[el.dataset.id].own;
      });
      document.querySelectorAll('.ta-stat-sel').forEach(function(el) {
        if (s[el.dataset.id] && s[el.dataset.id].stat) el.value = s[el.dataset.id].stat;
      });
    } catch(e) {}
  }

  window.taSaveState = function() {
    var s = {};
    document.querySelectorAll('.ta-own-sel').forEach(function(el) {
      if (!s[el.dataset.id]) s[el.dataset.id] = {};
      s[el.dataset.id].own = el.value;
    });
    document.querySelectorAll('.ta-stat-sel').forEach(function(el) {
      if (!s[el.dataset.id]) s[el.dataset.id] = {};
      s[el.dataset.id].stat = el.value;
    });
    localStorage.setItem(LS_KEY, JSON.stringify(s));
  };

  // Toggle expandable URL panel
  window.taToggle = function(iid) {
    var panel = document.getElementById('ta-panel-' + iid);
    var arrow = document.getElementById('ta-arrow-' + iid);
    var isOpen = panel.classList.contains('open');
    // Close all
    document.querySelectorAll('.ta-url-panel').forEach(function(p) { p.classList.remove('open'); });
    document.querySelectorAll('.ta-arrow').forEach(function(a) { a.classList.remove('open'); });
    if (!isOpen) {
      panel.classList.add('open');
      arrow.classList.add('open');
      // Populate URLs
      var container = document.getElementById('ta-urls-' + iid);
      if (!container.dataset.loaded) {
        var urls = ALL_URLS[iid] || [];
        var html = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><strong style="font-size:12px;color:#6B7280">' + urls.length + ' affected URLs</strong><button class="ta-copy-btn" onclick="event.stopPropagation();taCopyAll(\\'' + iid + '\\')">Copy All URLs</button></div>';
        urls.forEach(function(u, idx) {
          html += '<div class="ta-url-item"><span style="min-width:36px;font-size:12px;font-weight:600;color:#94A3B8;font-family:monospace;">' + (idx+1) + '.</span><a href="' + u + '" target="_blank" rel="noopener" style="flex:1">' + u + '</a><button class="ta-copy-btn" onclick="event.stopPropagation();taCopyUrl(this,\\'' + u.replace(/'/g, "\\\\'") + '\\')">Copy</button></div>';
        });
        container.innerHTML = html;
        container.dataset.loaded = '1';
      }
    }
  };

  window.taCopyUrl = function(btn, url) {
    navigator.clipboard.writeText(url).then(function() {
      btn.textContent = 'Copied!';
      setTimeout(function() { btn.textContent = 'Copy'; }, 1500);
    });
  };

  window.taCopyAll = function(iid) {
    var urls = ALL_URLS[iid] || [];
    navigator.clipboard.writeText(urls.join('\\n')).then(function() {
      var btn = document.querySelector('#ta-urls-' + iid + ' .ta-copy-btn');
      if (btn) { btn.textContent = 'Copied!'; setTimeout(function() { btn.textContent = 'Copy All URLs'; }, 1500); }
    });
  };

  // Filter by category chip
  var activeCat = 'all';
  window.taFilter = function(btn) {
    document.querySelectorAll('.ta-chip').forEach(function(c) { c.classList.remove('active'); });
    btn.classList.add('active');
    activeCat = btn.dataset.cat;
    taApplyFilters();
  };

  window.taApplyFilters = function() {
    var prio = document.getElementById('ta-prio-filter').value;
    var stat = document.getElementById('ta-status-filter').value;
    document.querySelectorAll('.ta-row-issue').forEach(function(row) {
      var iid = row.dataset.id;
      var show = true;
      if (activeCat !== 'all' && row.dataset.cat !== activeCat) show = false;
      if (prio !== 'all' && row.dataset.prio !== prio) show = false;
      if (stat !== 'all') {
        var sel = row.querySelector('.ta-stat-sel');
        if (sel && sel.value !== stat) show = false;
      }
      row.style.display = show ? '' : 'none';
      var panel = document.getElementById('ta-panel-' + iid);
      if (!show && panel) { panel.classList.remove('open'); }
    });
  };

  // Sort issue table by column, keeping each issue row paired with its URL panel
  var taSortDir = {};
  window.taSortTable = function(col) {
    var tbody = document.querySelector('.ta-table tbody');
    if (!tbody) return;
    var pairs = Array.from(tbody.querySelectorAll('tr.ta-row-issue')).map(function(row) {
      var panel = row.nextElementSibling;
      if (!panel || !panel.classList.contains('ta-url-panel')) panel = null;
      return { row: row, panel: panel };
    });
    var asc = !taSortDir[col]; taSortDir = {}; taSortDir[col] = asc;
    var prioOrder = { high: 3, medium: 2, low: 1 };
    pairs.sort(function(a, b) {
      var av, bv;
      if (col === 2) { av = prioOrder[a.row.dataset.prio] || 0; bv = prioOrder[b.row.dataset.prio] || 0; }
      else if (col === 1) { av = parseFloat((a.row.cells[1].innerText || '').replace(/[^\\d.-]/g, '')) || 0; bv = parseFloat((b.row.cells[1].innerText || '').replace(/[^\\d.-]/g, '')) || 0; }
      else if (col === 5) { av = (a.row.querySelector('.ta-own-sel') || {}).value || ''; bv = (b.row.querySelector('.ta-own-sel') || {}).value || ''; }
      else if (col === 6) { av = (a.row.querySelector('.ta-stat-sel') || {}).value || ''; bv = (b.row.querySelector('.ta-stat-sel') || {}).value || ''; }
      else { av = (a.row.cells[col] || {}).innerText || ''; bv = (b.row.cells[col] || {}).innerText || ''; }
      if (typeof av === 'number') return asc ? av - bv : bv - av;
      av = String(av).trim().toLowerCase(); bv = String(bv).trim().toLowerCase();
      return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    });
    pairs.forEach(function(p) { tbody.appendChild(p.row); if (p.panel) tbody.appendChild(p.panel); });
  };

  taLoadState();
})();
</script>
"""

    return html


# ── CLI entry point ──
if __name__ == "__main__":
    import sys

    crawl_dir = sys.argv[1] if len(sys.argv) > 1 else "/Users/nileshshirke/ThirdSlash_SEO_Dashboards/crawls/asset-thread"
    client_name = sys.argv[2] if len(sys.argv) > 2 else "Asset Thread"
    domain = sys.argv[3] if len(sys.argv) > 3 else "assetthread.com"
    audit_date = sys.argv[4] if len(sys.argv) > 4 else datetime.now().strftime("%Y-%m-%d")

    html = generate_tech_audit_html(crawl_dir, client_name, domain, audit_date)

    # Write standalone preview file
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tech_audit_preview.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tech Audit - {client_name}</title>
<style>body{{margin:0;padding:24px;background:#F5F6F8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}}</style>
</head>
<body>
<div id="tab-techaudit" class="section">
{html}
</div>
</body>
</html>""")
    print(f"Preview written to {out_path}")

    # Also print summary
    print(f"\nGenerated tech audit for {client_name} ({domain})")
    print(f"HTML length: {len(html):,} characters")
