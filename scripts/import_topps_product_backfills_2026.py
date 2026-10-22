"""Import the exact physical fields in two product-linked official PDFs."""
import sys,hashlib,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
from import_official_catalog import run,odds_pdf
from import_topps_tribute_2026 import acquire
PROOF=ROOT/'data/parallel-audit-sources/product-only-baseball-sapphire-ucc-20261022.json'
PARSER='scripts/import_topps_product_backfills_2026.py'
import pdfplumber,collections,re,json
from pathlib import Path

def read_cards(name):
 rows=[];notes=[];family=None
 with pdfplumber.open(ROOT/'data/catalog-sources/downloads'/(name+'.pdf')) as pdf:
  for pn,page in enumerate(pdf.pages,1):
   if name.startswith('bowman'):origins=[53.04,133.34,270.89,422.71]
   elif pn<=2:origins=[55.8,89.66,162.74,249.41]
   elif pn<=4:origins=[55.32,71.18,103.82,137.78]
   elif pn<=6:origins=[55.68,83.78,138.74,206.45]
   elif pn<=8:origins=[56.16,106.46,230.45,355.75]
   else:origins=[56.64,128.54,280.25,428.47]
   groups=[]
   for idx,c in sorted(enumerate(page.chars),key=lambda x:-x[1]['matrix'][5]):
    y=c['matrix'][5]
    if not groups or abs(groups[-1][0]-y)>.4:groups.append((y,[]))
    groups[-1][1].append((idx,c))
   for y,ordered in groups:
    chars=[c for idx,c in sorted(ordered)];line=' '.join(''.join(c['text'] for c in chars).split())
    if not line:continue
    if not any(abs(c['x0']-origins[1])<.04 for c in chars) or not any(abs(c['x0']-origins[2])<.04 for c in chars):
     if line.upper()==line and re.search('[A-Z]',line):family=line
     else:notes.append([str(pn),line])
     continue
    cells=[[],[],[],[]];col=0;started=set()
    for c in chars:
     matched=next((i for i in [1,2,3] if i not in started and abs(c['x0']-origins[i])<.04),None)
     if matched is not None:col=matched;started.add(matched)
     elif c['x0']<origins[1]-.1:col=0
     cells[col].append(c['text'])
    v=[' '.join(''.join(c).split()) for c in cells]
    if not re.fullmatch(r'(?:\d+|[A-Za-z0-9]+-[A-Za-z0-9]+)?',v[0]) or v[3] not in ['','Rookie']:raise ValueError((pn,line,v))
    assert family and v[1] and v[2],(pn,line,v)
    rows.append([family,*v,str(pn)])
 return rows,notes

def build():
 proof=json.loads(PROOF.read_text());cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text())
 for spec in proof['products']:
  key=spec['key'];slug=spec['slug'];src=proof[key+'-checklist'];op=proof[key+'-odds']
  path=ROOT/src['file'];assert acquire(src['url'],path)==src['sha256'];odds_path=ROOT/op['file'];assert acquire(op['url'],odds_path)==op['sha256']
  rows,notes=read_cards(key+'-checklist');odds,formats,raw,issues=odds_pdf(odds_path);assert not issues
  expected=(195,4,5,19) if key=='bowman-sapphire' else (950,37,106,270)
  assert (len(rows),len({r[0] for r in rows}),sum(r[4]=='Rookie' for r in rows),len(odds))==expected
  existing=next((r for r in catalog['sets'] if r['slug']==slug),None)
  record=existing or dict(title=spec['title'],manufacturer='Topps / Bowman',sport=spec['sport'],year=spec['year'],slug=slug,page='sets/'+slug+'.html',sourcePage=spec['source'],checklistUrl=src['url'],releaseStatus='Unverified',releaseDate=None,verified=proof['observed'])
  if not existing:record=run(record);assert record.get('tableData'),record
  families={r[0] for r in rows};prefixes={f:f for f in families}
  if key=='bowman-sapphire':prefixes['CHROME PROSPECTS']='CHROME PROSPECTS'
  else:
   prefixes.update({'BASE CARDS SHORT PRINTS':'BASE CARD SHORT PRINTS','BASE CARDS SUPER SHORT PRINTS':'BASE CARD SUPER SHORT PRINTS','BEST OF THE BEST AUTOS':'BEST OF THE BEST LEGENDARY NUMBERS AUTOGRAPH VARIATION','BEST OF THE BEST':'BEST OF THE BEST LEGENDARY NUMBERS','BASE AUTOS':'BASE CARD AUTOGRAPH VARIATION','FUTURE STARS AUTOS':'FUTURE STARS AUTOGRAPH VARIATION','TEAMMATES DUAL AUTOS':'TEAMMATES DUAL AUTOGRAPHS','ROOTS AUTOS':'ROOTS AUTOGRAPH VARIATION','UCC SKETCH CARDS':'TOPPS UCC SKETCH CARDS','TOPPS SUPERSTAR AUTO RELICS':'TOPPS SUPERSTAR AUTOGRAPHED RELICS','PREMIUM CLASS AUTO RELICS':'PREMIUM CLASS AUTOGRAPH RELICS','REGENCY CHROME AUTOGRAPH CARDS':'REGENCY CHROME CARDS AUTOGRAPH VARIATION','ULTIMATE STAGE CHROME AUTOGRAPH CARDS':'ULTIMATE STAGE CHROME CARDS AUTOGRAPH VARIATION','GRIEZMANN UCL MILESTONES AUTO RELIC':'GRIEZMANN UCL MILESTONE AUTOGRAPH RELIC CARD'})
   # Base-specific variation, regional-exclusive and 1955 Chrome captions
   # remain unjoined without an exact roster/family statement.
  joined=0
  for odd in odds:
   prefix=next((p for p in sorted(prefixes,key=len,reverse=True) if odd['name']==p or odd['name'].startswith(p+' ')),None)
   if prefix:odd['family']=prefixes[prefix];joined+=1
   else:odd['family']=odd['name'];odd['qualification']='The odds source publishes this category, but an exact roster-family join is unverified; no subject eligibility or numbering is inferred.'
  original_odds=copy.deepcopy(odds);original_formats=formats.copy()
  if key=='bowman-sapphire':
   source_format=formats[0];formats=['Published odds (format not named)']
   for odd in odds:odd['values']={formats[0]:odd['values'][source_format]}
  note=' '.join(spec['remainingGaps'])+' All original physical subjects, blank card numbers, repeated rows, teams and literal Rookie marks are preserved. Original odds columns and null cells remain unchanged; their headers do not name ratio units. Color names do not establish serial limits. The source product page is regional; title/product year is separate from calendar release.'
  data=dict(title=spec['title'],headers=['Checklist section','Card number','Name','Team','Rookie','Source page'],rows=rows,originalSubjectHeaders=['Card number','Name','Team','Rookie'],originalSubjectRows=[r[1:5] for r in rows],source=src['url'],sha256=src['sha256'],dedicatedParser=PARSER,importKind='topps-grid-pdf',sectionColumn=0,coverageComplete=True,sourceDocumentNotes=notes,unclassifiedLines=[],odds=odds,formats=formats,formatNamesPublished=key!='bowman-sapphire',oddsUnitsPublished=False,oddsSource=op['url'],oddsSha256=op['sha256'],oddsRawPages=raw,oddsIssues=issues,sourceSheets=[dict(name='Official source reconciliation',notes=[[note]])],publishedSpecifications=[dict(name='Qualified manufacturer box and checklist context',headers=['Published field','Published value','Official source'],rows=[[*r,spec['source']] for r in spec['facts']],source=spec['source'])])
  data.update(officialOddsFormats=original_formats,officialOddsHeader=['Cards' if key=='bowman-sapphire' else 'Card',*original_formats],officialOddsTable=original_odds)
  if key=='bowman-sapphire':data['sourceSheets'].append(dict(name='Original odds column header',notes=[[original_formats[0],'This literal SKU heading does not name a pack format or ratio unit; the shared unnamed-format presentation preserves every original value.']]))
  dp=ROOT/record['tableData'];dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
  record.update(status='Source table',rowCount=len(rows),sections=len(families),checklistUrl=src['url'],importKind='topps-grid-pdf',dedicatedParser=PARSER,sha256=src['sha256'],coverageComplete=True,verified=proof['observed'],catalogEvidence=note,dataAudit=note,odds=len(odds),formats=len(formats),oddsUrl=op['url'],oddsImportIssues=0,releaseDate=None,releaseStatus='Unverified',sourceObservation=dict(file=str(PROOF.relative_to(ROOT)),sha256=hashlib.sha256(PROOF.read_bytes()).hexdigest(),source=spec['source']))
  if existing:catalog['sets'][catalog['sets'].index(existing)]=record
  else:catalog['sets'].append(record)
  inventory=[r for r in inventory if r['slug']!=slug]+[record]
  print(spec['title'],len(rows),'physical subjects',len(families),'families',len(odds),'literal odds categories;',joined,'exact-caption joins')
 cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n');ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':build()
