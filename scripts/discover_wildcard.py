"""Discover every 2026 official Wild Card entry, including entertainment."""
import json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
blob=subprocess.run(['curl','-sLf','--max-time','30','https://wildcardinc.com/checklists/'],capture_output=True,check=True).stdout
text=blob.decode();m=re.search(r'const\s+ITEMS\s*=\s*',text);assert m,'Official inventory unavailable'
items,_=json.JSONDecoder().raw_decode(text[m.end():]);records=[r for r in items if r.get('y')=='2026']
assert len(records)>=40,'Unexpected inventory contraction; preserve prior discovery'
p=ROOT/'data/wildcard-official-catalog.json';prior=json.loads(p.read_text());by={r['f']:r for r in prior};by.update({r['f']:r for r in records});p.write_text(json.dumps(list(by.values()),ensure_ascii=False,indent=2)+'\n')
print('Verified',len(records),'official 2026 entries across all published categories.')
