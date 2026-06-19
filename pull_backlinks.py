"""
ThirdSlash SEO Dashboards — Backlinks Data Puller
Fetches monthly backlink metrics for all clients and saves to backlinks_data.json

Sources:
  - Manual_Data Google Sheet  → Ahrefs Backlinks + Referring Domains (manual entry)
  - Ahrefs Public API (free)  → Domain Rating (no key needed)
  - Moz Links API (free tier) → Domain Authority

Run: python3 pull_backlinks.py
Cost: $0 (all free sources)

Workflow:
  1. Fill in Ahrefs backlinks + referring domains in Manual_Data sheet
  2. Run this script — it reads the sheet and fetches DR + DA automatically
  3. Run generate_dashboard.py to rebuild dashboards
"""

import os, json, pickle, requests, time
from datetime import datetime
from google.auth.transport.requests import Request

# ── Configuration ────────────────────────────────────────────────────────────

BASE     = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(BASE, "backlinks_data.json")
TOKEN    = os.path.join(BASE, "token.pickle")
SHEET_ID = "1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"

# Load .env file if present
_env_file = os.path.join(BASE, ".env")
if os.path.exists(_env_file):
    for _line in open(_env_file):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

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
    "HappyLyfe":             "happylyfe.in.th",
    "Public69":              "public69.com",
    "Ovation Square":        "ovationsquare.com",
    "Piovra Group":          "piovragroup.com",
    "Brickroom LA":          "brickroomla.com",
    "MJ Gorgeous":           "mjgorgeous.com",
    "EZ Lifestyle":          "ezlifestyle.in",
    "Lancers GSEB":          "lancersgseb.com",
    "ThirdSlash":            "thirdslash.com",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_creds():
    try:
        with open(TOKEN, "rb") as f:
            c = pickle.load(f)
        if c.expired and c.refresh_token:
            c.refresh(Request())
            with open(TOKEN, "wb") as f:
                pickle.dump(c, f)
        return c
    except Exception as e:
        print(f"  [Auth] Could not load token: {e}")
        return None


def safe_int(v):
    try:
        return int(str(v).replace(",", "").strip()) if v else None
    except:
        return None


def safe_float(v):
    try:
        return float(str(v).strip()) if v else None
    except:
        return None


# ── Google Sheet: Read Manual_Data ────────────────────────────────────────────

def read_manual_data(gc, month_label):
    """
    Read Ahrefs backlinks, referring domains, GMB posts, rating, reviews
    from the Manual_Data sheet for the given month.
    Returns dict: { client_name: { ahrefs_backlinks, ahrefs_referring_domains, ... } }
    """
    import gspread
    try:
        sheet = gc.open_by_key(SHEET_ID)
        ws = sheet.worksheet("Manual_Data")
        rows = ws.get_all_records()
    except Exception as e:
        print(f"  [Sheet] Could not read Manual_Data: {e}")
        return {}

    results = {}
    for r in rows:
        if r.get("Month", "") == month_label:
            client = r.get("Client Name", "")
            if client:
                results[client] = {
                    "ahrefs_backlinks":      safe_int(r.get("Ahrefs External Backlinks")),
                    "ahrefs_referring_domains": safe_int(r.get("Ahrefs Referring Domains")),
                    "gmb_posts":             safe_int(r.get("GMB Posts")),
                    "gmb_avg_rating":        safe_float(r.get("GMB Average Rating")),
                    "gmb_new_reviews":       safe_int(r.get("GMB New Reviews")),
                }
    return results


# ── Ahrefs Public API: Domain Rating (free, no key) ──────────────────────────

def fetch_ahrefs_dr(domain):
    url = f"https://api.ahrefs.com/v3/public/domain-rating-free?target={domain}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return round(data.get("domain_rating", {}).get("domain_rating", 0), 1)
    except Exception as e:
        print(f"  [Ahrefs DR] {domain}: {e}")
        return None


# ── Moz API: Domain Authority (free, 50 rows/month) ──────────────────────────

def fetch_moz_da(domain):
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


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import gspread

    month_label = datetime.now().strftime("%b-%Y")
    print(f"\n=== Backlinks Pull — {month_label} ===\n")

    # Load existing data to preserve history
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE) as f:
            all_data = json.load(f)
    else:
        all_data = {}

    # Auth + read manual data from Google Sheet
    creds = load_creds()
    gc = gspread.authorize(creds)

    print("[1/3] Reading Manual_Data sheet...")
    manual = read_manual_data(gc, month_label)
    print(f"      Found manual data for {len(manual)} clients.")

    # Per-domain: fetch DR + DA, merge with manual data
    for client_name, domain in CLIENTS.items():
        print(f"\n  {client_name} ({domain})")

        # Ahrefs DR (free API)
        print("    → Ahrefs DR...")
        dr = fetch_ahrefs_dr(domain)
        time.sleep(0.5)

        # Moz DA (free tier)
        print("    → Moz DA...")
        da = fetch_moz_da(domain)
        time.sleep(0.5)

        # Manual data from sheet
        m = manual.get(client_name, {})
        ahrefs_bl = m.get("ahrefs_backlinks")
        ahrefs_rd = m.get("ahrefs_referring_domains")

        # Build this month's record
        record = {
            "month":                    month_label,
            "domain":                   domain,
            "ahrefs_backlinks":         ahrefs_bl,
            "ahrefs_referring_domains": ahrefs_rd,
            "domain_rating":            dr,
            "domain_authority":         da,
        }

        # Store under client, keyed by month
        if client_name not in all_data:
            all_data[client_name] = {}
        all_data[client_name][month_label] = record

        bl_src = "sheet" if ahrefs_bl is not None else "empty"
        print(f"    ✓ DR={dr}  DA={da}  BL={ahrefs_bl} ({bl_src})  RD={ahrefs_rd}")

    # Save
    with open(OUT_FILE, "w") as f:
        json.dump(all_data, f, indent=2)

    print(f"\n✅ Saved to {OUT_FILE}")
    print(f"   Cost: $0 (all free sources)")
    print(f"\n📝 Remember to fill in Manual_Data sheet before running:")
    print(f"   https://docs.google.com/spreadsheets/d/{SHEET_ID}")


if __name__ == "__main__":
    main()
