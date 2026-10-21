"""Importa promociones de Walgreens Photo sin afirmar canje verificado en Puerto Rico."""
import json,re,datetime,pathlib,requests
from bs4 import BeautifulSoup
URL="https://photo.walgreens.com/store/deals"
out=pathlib.Path("offers.json")
previous=json.loads(out.read_text()) if out.exists() else {"offers":[]}
try:
    response=requests.get(URL,timeout=25,headers={"User-Agent":"Mozilla/5.0 (compatible; PeseteandoPR/1.0)"})
    response.raise_for_status()
    soup=BeautifulSoup(response.text,"html.parser")
    lines=[x.strip() for x in soup.get_text("\n").splitlines() if x.strip()]
    today=datetime.date.today()
    offers=[]
    for i,line in enumerate(lines):
        if not line.startswith("Expires:"):continue
        title=next((lines[j] for j in range(i-1,max(-1,i-5),-1) if not lines[j].startswith(("Expires:","Coupon code:"))),None)
        code=next((lines[j].split(":",1)[1].strip() for j in range(i+1,min(i+5,len(lines))) if lines[j].startswith("Coupon code:")),None)
        m=re.search(r"([A-Za-z]+)\s+(\d{1,2})",line)
        if not (m and code and title):continue
        try: expiry=datetime.datetime.strptime(f"{m.group(1)} {m.group(2)} {today.year}","%B %d %Y").date()
        except ValueError:continue
        if expiry<today:continue
        offers.append({"id":"photo-"+code+"-"+re.sub("[^a-z0-9]+","-",title.lower()),"store":"Walgreens","category":"Fotografía","title":title,"code":code,"expires":expiry.isoformat(),"source":URL,"pr_status":"Sin confirmar","kind":"code","image":""})
    # Fail closed: never retain stale offers, and do not publish unverified scraped data as PR confirmed.
    unique={o["id"]:o for o in offers}
    data={"updated":datetime.datetime.now(datetime.timezone.utc).isoformat(),"offers":list(unique.values()),"source_status":"ok" if offers else "sin_ofertas_verificables"}
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    print("Ofertas encontradas:",len(offers))
except Exception as e:
    print("Fuente no disponible:",e)
    # Retain only unexpired offers, never invent new ones.
    previous["offers"]=[o for o in previous.get("offers",[]) if o.get("expires","")>=datetime.date.today().isoformat()]
    previous["source_status"]="error"
    out.write_text(json.dumps(previous,ensure_ascii=False,indent=2)+"\n")
