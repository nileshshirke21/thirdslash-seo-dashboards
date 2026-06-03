import gspread, pickle, os
from google.auth.transport.requests import Request

SHEET_ID  = "1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"
TAB_NAME  = "04_Rank Tracking Log"
TOKEN_FILE = os.path.expanduser("~/ThirdSlash_SEO_Automation/token.pickle")

with open(TOKEN_FILE,"rb") as f: creds=pickle.load(f)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE,"wb") as f: pickle.dump(creds,f)

client = gspread.authorize(creds)
sheet  = client.open_by_key(SHEET_ID)
ws     = sheet.worksheet(TAB_NAME)

print("Step 1: Clearing entire tab...")
ws.clear()

print("Step 2: Writing correct header row...")
header = [
    "Client Name","Keyword","Target URL","Search Volume",
    "Last Month Rank","This Month Rank","Movement","Movement Label",
    "Date Checked","Device","Location","Source"
]
ws.update(range_name="A1", values=[header])

print("Step 3: Writing Public69 data rows...")
KEYWORDS = [
    ("escort directory uk",19,15,"https://public69.com/"),
    ("uk escort services",None,16,"https://public69.com/"),
    ("escort friendly hotels london",32,36,"https://public69.com/blog/best-7-luxury-hotels-in-london-escort-friendly"),
    ("escort hotel london",40,42,"https://public69.com/blog/best-7-luxury-hotels-in-london-escort-friendly"),
    ("escorts uk",None,None,""),("escorts in bristol",None,None,""),
    ("erotic massage",None,None,""),("derbyshire escorts",None,None,""),
    ("uk escorts",None,None,""),("female escort near me",None,None,""),
    ("male escorts near me",None,None,""),("edinburgh escort",None,None,""),
    ("erotic massage near me",None,None,""),("dublin escort service",None,None,""),
    ("bristol escorts",None,None,""),("mature escorts derbyshire",None,None,""),
    ("gay male escorts",None,None,""),("london escort services",None,None,""),
    ("escort services in dublin",None,None,""),("female escort carmarthenshire",None,None,""),
    ("couple escort",None,None,""),("couple escort london",None,None,""),
    ("independent trans escort",None,None,""),("escorts in cornwall",None,None,""),
    ("escort agency uk",None,None,""),("london trans escort",None,None,""),
    ("escorts in edinburgh",None,None,""),("mature escorts bristol",None,None,""),
    ("dublin escorts ie",None,None,""),("couple escorts",None,None,""),
    ("erotic massage london",None,None,""),("cornwall escort",None,None,""),
    ("dublin escorts",None,None,""),("escorts berkshire",None,None,""),
    ("independent dublin escorts",None,None,""),("london escort agency",None,None,""),
    ("male escorts",None,None,""),("dublin escort",None,None,""),
    ("escort service london",None,None,""),("london erotic massage",None,None,""),
    ("aberdeenshire escorts",None,None,""),("london escorts",None,None,""),
    ("escorts in surrey",None,None,""),("edinburgh escorts",None,None,""),
    ("escorts in derbyshire",None,None,""),("female escorts edinburgh",None,None,""),
    ("escort near me",None,None,""),("female escorts near me",None,None,""),
    ("mature escorts berkshire",None,None,""),("escort trans london",None,None,""),
    ("male escorting",None,None,""),("couple escorts near me",None,None,""),
    ("berkshire escort agency",None,None,""),("escort services in berkshire",None,None,""),
    ("escorts near me",None,None,""),("escorts surrey",None,None,""),
    ("escort carmarthenshire",None,None,""),("escorts in dumfries",None,None,""),
    ("mature escorts buckinghamshire",None,None,""),("male escort",None,None,""),
    ("escort couples",None,None,""),("manchester escorts",None,None,""),
    ("berkshire escorts",None,None,""),("manchester escort booking",None,None,""),
    ("female escort cornwall",None,None,""),("surrey escort",None,None,""),
    ("aberdeenshire escort",None,None,""),("female escorts bristol",None,None,""),
    ("trans escort london",None,None,""),("trans escorts",None,None,""),
    ("escorts in buckinghamshire",None,None,""),("male escorts london",None,None,""),
    ("trans escorts london",None,None,""),("buckinghamshire escorts",None,None,""),
    ("escort services in cornwall",None,None,""),("independent female escorts",None,None,""),
    ("male escort near me",None,None,""),("dumfries escorts",None,None,""),
    ("surrey escorts",None,None,""),("female escorts derbyshire",None,None,""),
    ("female escort",None,None,""),("trans escorts near me",None,None,""),
    ("escorts in carmarthenshire",None,None,""),("carmarthenshire escorts",None,None,""),
    ("escort service near me",None,None,""),("male escort london",None,None,""),
    ("female escorts",None,None,""),("escorts for couples",None,None,""),
    ("gay escort near me",None,None,""),("independent escorts uk",None,None,""),
    ("escorts in manchester",None,None,""),("independent berkshire escorts",None,None,""),
]

def chg(p,c):
    if p is None and c is None: return "-"
    if p is None: return "NEW"
    if c is None: return "DROPPED"
    d=p-c; return f"+{d}" if d>0 else str(d) if d<0 else "0"

def lbl(p,c):
    if p is None and c is None: return "— Not Ranking"
    if p is None: return "★ New Entry"
    if c is None: return "▼ Dropped Out"
    d=p-c; return "▲ Improved" if d>0 else "▼ Dropped" if d<0 else "— No Change"

rows = []
for kw,p,c,url in KEYWORDS:
    rows.append([
        "Public69", kw, url, "",
        str(p) if p else "NR",
        str(c) if c else "NR",
        chg(p,c), lbl(p,c),
        "24-May-2026", "Desktop", "UK", "Ubersuggest"
    ])

ws.update(range_name="A2", values=rows)

print(f"\nDONE — Tab rebuilt cleanly")
print(f"  Header: 12 columns (A to L)")
print(f"  Data rows: {len(rows)} (Public69)")
print(f"  No orphan rows")
print(f"\nOpen the sheet and check:")
print(f"  https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid=682386615")
