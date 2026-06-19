"""
ThirdSlash SEO Dashboards — Backlinks Data Puller
Fetches monthly backlink metrics for all clients and saves to backlinks_data.json

Sources:
  - DataForSEO Backlinks API  → Ahrefs Backlinks + Referring Domains
  - Ahrefs Public API (free)  → Domain Rating (no key needed)
  - Moz Links API (free tier) → Domain Authority
  - Google Search Console     → GSC Backlinks + GSC Referring Domains

Run: python3 pull_backlinks.py
Cost: ~$0.02 per client domain (DataForSEO only)
"""

import os, json, pickle, base64, requests, time
from datetime import datetime
from google.auth.transport.requests import Request

# ── Configuration ────────────────────────────────────────────────────────────

BASE     = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(BASE, "backlinks_data.json")
TOKEN    = os.path.join(BASE, "token.pickle")

# Load .env file if present (keeps secrets out of source control)
_env_file = os.path.join(BASE, ".env")
if os.path.exists(_env_file):
    for _line in open(_env_file):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# DataForSEO credentials — stored in .env
DATAFORSEO_LOGIN    = os.environ.get("DATAFORSEO_LOGIN", "")
DATAFORSEO_PASSWORD = os.environ.get("DATAFORSEO_PASSWORD", "")

# Moz API — Bearer token from https://moz.com/account/api/tokens
MOZ_API_TOKEN = os.environ.get("MOZ_API_TOKEN", "")

# Client → domain mapping
CLIENTS = {
    "Asset Thread":          "assetthread.com",
    "HRM Thread":            "hrmthread.com",
    "Lancers CBSE":          "lancerscbse.com",
    "Lancers Early Years":   "lancersearlyyears.com",
    "Lancers Army School":   "lancersarmyschool.com",
    "Potential Engineering": "potentialengineering.com",
    "Estrela Hotels":        "estrelahotels.com",
    "Kelly Powers":          "kellypowers.com",
    "HappyLyfe":             "happylyfe.in",
    "Public69":              "public69.com",
    "Ovation Square":        "ovationsquare.com",
    "Piovra Group":          "piovragroup.com",
    "Brickroom LA":          "brickroomla.com",
    "MJ Gorgeous":           "mjgorgeous.com",
    "EZ Lifestyle":          "ezlifestyle.in",
    "Lancers GSEB":          "lancersgseb.com",
    # ThirdSlash itself
    "ThirdSlash":            "thirdslash.com",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_gsc_creds():
    try:
        with open(TOKEN, "rb") as f:
            c = pickle.load(f)
        if c.expired and c.refresh_token:
            c.refresh(Request())
            with open(TOKEN, "wb") as f:
                pickle.dump(c, f)
        return c
    except Exception as e:
        print(f"  [GSC] Could not load token: {e}")
        return None


def fmt(n):
    """Format number with comma separator."""
    try:
        return f"{int(n):,}"
    except:
        return str(n)


# ── DataForSEO: Ahrefs Backlinks + Referring Domains ─────────────────────────

def fetch_dataforseo_backlinks(domains):
    """
    POST to backlinks/summary/live — one request per domain (trial plan limit).
    Returns dict: { domain: { backlinks, referring_domains } }
    Cost: $0.02 per domain
    """
    if not DATAFORSEO_LOGIN or not DATAFORSEO_PASSWORD:
        print("  [DataForSEO] Credentials not set — skipping.")
        return {}

    url = "https://api.dataforseo.com/v3/backlinks/summary/live"
    creds = base64.b64encode(f"{DATAFORSEO_LOGIN}:{DATAFORSEO_PASSWORD}".encode()).decode()
    headers = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

    results = {}
    for domain in domains:
        try:
            r = requests.post(url, headers=headers,
                              json=[{"target": domain, "include_subdomains": True}],
                              timeout=30)
            r.raise_for_status()
            data = r.json()
            for task in data.get("tasks", []):
                for item in (task.get("result") or []):
                    results[domain] = {
                        "backlinks":         item.get("backlinks"),
                        "referring_domains": item.get("referring_domains"),
                    }
        except Exception as e:
            print(f"  [DataForSEO] {domain}: {e}")
        time.sleep(0.3)  # stay under rate limits

    return results


# ── Ahrefs Public API: Domain Rating (free, no key) ──────────────────────────

def fetch_ahrefs_dr(domain):
    """
    Free Ahrefs public endpoint — no API key needed.
    Attribution required: "Domain Rating by Ahrefs" (https://ahrefs.com/)
    """
    url = f"https://api.ahrefs.com/v3/public/domain-rating-free?target={domain}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return round(data.get("domain_rating", {}).get("domain_rating", 0), 1)
    except Exception as e:
        print(f"  [Ahrefs DR] {domain}: {e}")
        return None


# ── Moz API: Domain Authority (free, 10 calls/month) ─────────────────────────

def fetch_moz_da(domain):
    """
    Moz Links API v2 — free tier: 50 rows/month.
    Auth: Bearer token from https://moz.com/account/api/tokens
    Docs: https://moz.com/products/mozscape/mozscape-api-docs
    """
    if not MOZ_API_TOKEN:
        print("  [Moz] API token not set — skipping.")
        return None

    url = "https://lsapi.seomoz.com/v2/url_metrics"
    payload = {"targets": [domain]}
    headers = {
        "Authorization": f"Bearer {MOZ_API_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        results = r.json().get("results", [])
        if results:
            return round(results[0].get("domain_authority", 0))
    except Exception as e:
        print(f"  [Moz DA] {domain}: {e}")
    return None


# ── Google Search Console: Backlinks + Referring Domains ─────────────────────

def fetch_gsc_links(domain, creds):
    """
    GSC Search Console API — Links report.
    Returns { gsc_backlinks, gsc_referring_domains }
    Note: GSC 'links' endpoint returns top linking sites count and total links.
    """
    if not creds:
        return {"gsc_backlinks": None, "gsc_referring_domains": None}

    from urllib.parse import quote
    site_url = f"sc-domain:{domain}"   # domain property format in GSC
    headers  = {"Authorization": f"Bearer {creds.token}"}
    base     = "https://searchconsole.googleapis.com/webmasters/v3"

    # Try sc-domain: format first, fall back to https://domain/
    for s_url in [f"sc-domain:{domain}", f"https://{domain}/"]:
        try:
            r = requests.get(
                f"{base}/sites/{quote(s_url, safe='')}/links",
                headers=headers, timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                ext = data.get("externalLinks", {})
                top_sources = ext.get("topSources", {}).get("rows", [])
                total_links  = sum(int(row.get("count", 0)) for row in top_sources)
                total_domains = len(top_sources)
                return {
                    "gsc_backlinks":         total_links  or None,
                    "gsc_referring_domains": total_domains or None,
                }
        except Exception as e:
            print(f"  [GSC Links] {domain} ({s_url}): {e}")

    return {"gsc_backlinks": None, "gsc_referring_domains": None}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    month_label = datetime.now().strftime("%b-%Y")
    print(f"\n=== Backlinks Pull — {month_label} ===\n")

    # Load existing data to preserve history
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE) as f:
            all_data = json.load(f)
    else:
        all_data = {}

    # Load GSC credentials once
    gsc_creds = load_gsc_creds()

    domains = list(CLIENTS.values())

    # ── Step 1: DataForSEO batch call (cheapest: 1 batch = N domains) ────────
    print(f"[1/4] DataForSEO — fetching backlinks + referring domains for {len(domains)} domains...")
    dfs_results = fetch_dataforseo_backlinks(domains)
    print(f"      Got data for {len(dfs_results)} domains.")

    # ── Step 2-4: Per-domain calls ────────────────────────────────────────────
    for client_name, domain in CLIENTS.items():
        print(f"\n  {client_name} ({domain})")

        # Ahrefs DR (free API)
        print("    → Ahrefs DR...")
        dr = fetch_ahrefs_dr(domain)
        time.sleep(0.5)  # be polite

        # Moz DA (free tier, max 10/month — comment out if quota exceeded)
        print("    → Moz DA...")
        da = fetch_moz_da(domain)
        time.sleep(0.5)

        # GSC links
        print("    → GSC links...")
        gsc = fetch_gsc_links(domain, gsc_creds)

        # DataForSEO result for this domain
        dfs = dfs_results.get(domain, {})

        # Build this month's record
        record = {
            "month":                 month_label,
            "domain":                domain,
            # GSC
            "gsc_backlinks":         gsc.get("gsc_backlinks"),
            "gsc_referring_domains": gsc.get("gsc_referring_domains"),
            # Ahrefs (via DataForSEO)
            "ahrefs_backlinks":      dfs.get("backlinks"),
            "ahrefs_referring_domains": dfs.get("referring_domains"),
            # Scores
            "domain_rating":         dr,    # Ahrefs DR (free API)
            "domain_authority":      da,    # Moz DA
        }

        # Store under client, keyed by month
        if client_name not in all_data:
            all_data[client_name] = {}
        all_data[client_name][month_label] = record

        print(f"    ✓ DR={dr}  DA={da}  "
              f"Ahrefs BL={dfs.get('backlinks')}  RD={dfs.get('referring_domains')}  "
              f"GSC BL={gsc.get('gsc_backlinks')}  GSC RD={gsc.get('gsc_referring_domains')}")

    # Save
    with open(OUT_FILE, "w") as f:
        json.dump(all_data, f, indent=2)

    print(f"\n✅ Saved to {OUT_FILE}")
    print(f"   Estimated DataForSEO cost: ${len(domains) * 0.02:.2f}")


if __name__ == "__main__":
    main()
