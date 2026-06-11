import gspread, pickle, os, time
from google.auth.transport.requests import Request
SHEET_ID="1J6yx5qZO05dDkmSiC-IvOXleqU4tL2GTqUu0b0idTxE"
TOKEN_FILE=os.path.expanduser("~/ThirdSlash_SEO_Automation/token.pickle")
GMB_DATA={"Asset Thread":("Yes","Type 2","Mumbai, India","India GMB active. Dubai suspended. Monthly blog post + city citations."),"HRM Thread":("Yes","Type 2","Mumbai, India","City expansion: HR Software Mumbai, Delhi. GMB posts monthly."),"Lancers CBSE":("Yes","Type 1","Surat, India","Hyperlocal school. Full GMB treatment."),"Lancers GSEB":("Yes","Type 1","Surat, India","Hyperlocal school. Full GMB treatment."),"Lancers Early Years":("Yes","Type 1","Surat, India","Hyperlocal preschool. Full GMB treatment."),"Lancers Army School":("Yes","Type 1","Surat, India","Hyperlocal school group. Full GMB treatment."),"mPokket":("Yes","Type 3","Pan-India","ORM only. Review tracking before loan signup."),"Potential Engineering":("Yes","Type 2","Mumbai, India","Active GMB. Monthly blog post shared on GMB."),"EZ Lifestyle":("No","None","-","National e-commerce. No GMB needed."),"Estrela Hotels":("Yes","Type 1","North Goa, India","Resort. GMB critical for travel + local searches."),"Kelly Powers":("Yes","Type 1","San Francisco, USA","Local dietitian. SF GMB. Keywords: SF Dietitian, San Diego Dietitian."),"HappyLyfe":("Yes","Type 1","Bangkok, Thailand","Physical CBD store. Walk-ins + Thailand-wide shipping."),"Public69":("No","None","-","Online directory. No GMB address possible."),"Ovation Square":("Yes","Type 1","Long Beach, CA","Physical event venue. Hyperlocal bookings."),"Piovra Group":("Yes","Type 1","Los Angeles, CA","Event venue management. LA and Orange County."),"Brickroom LA":("Yes","Type 1","Los Angeles, CA","Physical event space. All bookings local."),"MJ Gorgeous":("Yes","Type 1","Bangalore, India","Physical venue. Hyperlocal Bangalore.")}
def col_letter(n):
    result=""
    n+=1
    while n:
        n,r=divmod(n-1,26)
        result=chr(65+r)+result
    return result
def main():
    print("ThirdSlash — GMB Sheet Updater (batch)\n"+"="*40)
    with open(TOKEN_FILE,"rb") as f: creds=pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE,"wb") as f: pickle.dump(creds,f)
    gc=gspread.authorize(creds)
    sheet=gc.open_by_key(SHEET_ID)
    print("\nStep 1: Reading 01_Client Profile...")
    ws=sheet.worksheet("01_Client Profile")
    all_rows=ws.get_all_values()
    header=all_rows[2]
    print(f"  {len(header)} columns found")
    gmb_col=next((i for i,h in enumerate(header) if "GMB Connected" in h),None)
    if gmb_col is None: print("  ERROR: GMB Connected not found"); return
    print(f"  GMB Connected at {col_letter(gmb_col)}")
    new_col_defs=["GMB Type","GMB City","GMB Notes","Last Month GMB Reviews"]
    col_idx={h.strip():i for i,h in enumerate(header) if h.strip() in new_col_defs}
    next_idx=len(header)
    new_headers=[]
    for name in new_col_defs:
        if name not in col_idx:
            col_idx[name]=next_idx
            new_headers.append((next_idx,name))
            next_idx+=1
    batch=[]
    for idx,name in new_headers:
        batch.append({"range":f"{col_letter(idx)}3","values":[[name]]})
        print(f"  Adding column '{name}' at {col_letter(idx)}")
    found=0
    for ri,row in enumerate(all_rows):
        if ri<=2: continue
        if not row or len(row)<2: continue
        client=row[1].strip()
        if not client or client not in GMB_DATA: continue
        c,t,ci,no=GMB_DATA[client]
        sr=ri+1
        batch.append({"range":f"{col_letter(gmb_col)}{sr}","values":[[c]]})
        for cname,val in [("GMB Type",t),("GMB City",ci),("GMB Notes",no),("Last Month GMB Reviews","")]:
            if cname in col_idx:
                batch.append({"range":f"{col_letter(col_idx[cname])}{sr}","values":[[val]]})
        found+=1
        print(f"  Queued: {client}")
    print(f"\n  Sending {len(batch)} updates in one batch call...")
    ws.batch_update(batch)
    print(f"  Done — {found} clients updated")
    time.sleep(3)
    print("\nStep 2: Updating README...")
    ws_r=sheet.worksheet("00_README")
    rd=ws_r.get_all_values()
    lr=len(rd)+2
    ws_r.update(range_name=f"A{lr}",values=[[""],["=== GMB WORKFLOW ==="],["Type 1 (11)","Full GMB: Audit(odd months)+Blog Post+Offer Post+Review Tracker","Lancers x4, Estrela, Kelly, HappyLyfe, Ovation, Piovra, Brickroom, MJ"],["Type 2 (3)","Blog Post+Review Tracker+City Citation","Asset Thread, HRM Thread, Potential Engineering"],["Type 3 (1)","Review Tracker only","mPokket"],["No GMB (2)","Skip GMB tasks","EZ Lifestyle, Public69"],[""],["Rule 1","Image request Week 1. No image = no offer post."],["Rule 2","Every blog live = GMB post within 24hrs."],["Rule 3","Update Last Month GMB Reviews after sending client update."],["Rule 4","Audit: Type 1 only, odd months only."],["Rule 5","City Citation: Type 2 only, monthly."]])
    print(f"  README updated at row {lr}")
    print("\n"+"="*40+"\nDONE — 15 clients have GMB | 2 skipped")
    print(f"Sheet: https://docs.google.com/spreadsheets/d/{SHEET_ID}")
if __name__=="__main__": main()
