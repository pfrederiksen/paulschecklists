"""Import the official four-column Universe XLS and literal multi-format odds."""
import json,hashlib,re,urllib.request,xlrd
from datetime import date
import import_official_catalog as g
ROOT=g.ROOT;slug='topps-bowman-2026-topps-universe-wwe';page='https://www.topps.com/pages/topps-universe-wwe'
url='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/26UWWE_-_2026_Topps_Universe_WWE_Checklist_8700b54a-0ec9-4ab7-87b2-47b4e40862a0.xls?v=1786542209'
odd='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Universe_WWE_odds.pdf?v=1790191410'
blob=urllib.request.urlopen(url,timeout=30).read();s=xlrd.open_workbook(file_contents=blob).sheet_by_index(0);rows=[];section='Checklist';original=[]
for rn in range(s.nrows):
 vals=s.row_values(rn);original.append(vals)
 if not any(vals):continue
 if not vals[1]:
  if vals[0].startswith(('2026 Topps','Checklists provided')):continue
  section=vals[0];continue
 assert vals[0] and vals[3] in ['', 'Rookie']
 number=str(int(vals[0])) if isinstance(vals[0],float) and vals[0].is_integer() else str(vals[0])
 rows.append([section,number,vals[1],vals[2],vals[3],s.name,str(rn+1)])
assert len([r for r in rows if r[0].startswith('BASE CARDS')])==200
assert len([r for r in rows if r[0].startswith('PEAK PERFORMANCE')])==100
assert sum(r[4]=='Rookie' for r in rows)==40
op=g.CACHE/(slug+'-odds.pdf');ob=urllib.request.urlopen(odd,timeout=30).read();op.write_bytes(ob);entries,formats,raw,issues=g.odds_pdf(op);assert not issues,issues
payload={'title':'2026 Topps Universe WWE','headers':['Checklist section','Card number','Name','Published designation (source column 3)','Rookie','Source worksheet','Source row'],'rows':rows,'source':url,'sha256':hashlib.sha256(blob).hexdigest(),'importKind':'xls','sectionColumn':0,'rawWorksheet':original,'odds':entries,'formats':formats,'oddsRawPages':raw,'oddsSource':odd,'oddsSha256':hashlib.sha256(ob).hexdigest(),'oddsIssues':issues,'oddsUnitsPublished':False}
from import_topps_universe_wwe_specs_2026 import supplement
payload,guide_metadata=supplement(payload)
path='data/imports/'+slug+'.json';(ROOT/path).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
r={'title':payload['title'],'manufacturer':'Topps / Bowman','sport':'wrestling','year':'2026','slug':slug,'page':'sets/'+slug+'.html','sourcePage':page,'checklistUrl':url,'oddsUrl':odd,'tableData':path,'status':'Source table','importKind':'xls','dedicatedParser':'scripts/import_topps_universe_wwe_2026.py','rowCount':len(rows),'sections':len(set(r[0] for r in rows)),'odds':len(entries),'formats':len(formats),'parallelData':True,'publishedOdds':True,'releaseStatus':'Released','releaseDate':None,'sha256':payload['sha256'],'verified':date.today().isoformat(),'catalogEvidence':'Official product page labels this release available now. The workbook preserves 200 base rows and 100 Peak Performance rows plus inserts, autographs and relics. Printed WWE designations remain original source fields and are not inferred teams. Exact calendar release date is not verified.','dataAudit':'All populated card rows reconcile to the original four workbook columns; 40 printed Rookie flags verified. Physical odds columns validated with no alignment issues.'}
r.update(guide_metadata);r['oddsSourceReview']=payload['oddsSourceReview']
p=ROOT/'data/set-catalog.json';c=json.loads(p.read_text());c['sets']=[x for x in c['sets'] if x['slug']!=slug]+[r];p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'data/topps-product-official-catalog.json';inv=json.loads(p.read_text());inv=[x for x in inv if x['slug']!=slug]+[r];p.write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
print(r['title'],len(rows),'rows',len(entries),'odds',formats)
