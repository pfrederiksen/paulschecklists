"""Preserve the physical columns in Midnight UFC and Royalty WWE checklists."""
import collections,hashlib,json,re,subprocess
from pathlib import Path
import pdfplumber
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1]
PARSER='scripts/import_topps_combat_backfills.py'
UFC_PAGE='https://www.topps.com/pages/topps-midnight-ufc'
UFC_ODDS='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_UFC_Midnight_Odds_44ec7b6e-a24d-419f-9fa1-5d04003c62aa.pdf?v=1779223098'
CONFIG={
 'topps-bowman-2026-topps-midnight-ufc':{'origins':[100.10,273.29],'skip':80,'pages':6,'count':484,'sections':15,'columns':['Name','Rookie']},
 'topps-bowman-2025-topps-royalty-wwe':{'origins':[96.86,173.42,258.41],'skip':75,'pages':9,'count':739,'sections':34,'columns':['Name','Published designation','Rookie']},
}
def read_cards(path,config):
 rows=[];raw=[];section=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==config['pages']
  for pn,page in enumerate(pdf.pages,1):
   raw.append({'page':pn,'text':page.extract_text()});lines=collections.defaultdict(list)
   for c in page.chars:lines[round(c['top'],1)].append(c)
   for y,chars in sorted(lines.items()):
    if pn==1 and y<config['skip']:continue
    first=''.join(c['text'] for c in chars if c['x0']<config['origins'][0]-.1).strip();text=''.join(c['text'] for c in chars).strip()
    if re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9-]+',first):
     starts=[]
     for col,x in enumerate(config['origins'],1):
      indices=[i for i,c in enumerate(chars) if abs(c['x0']-x)<.03]
      if indices:starts.append((max(indices),col))
     assert starts and starts[0][1]==1,(pn,y,text)
     cols=[first]+['']*len(config['origins'])
     # Original drawing sequence prevents long names from being merged with
     # designation cells. A printed WWE designation is never a team field.
     for i,(idx,col) in enumerate(starts):
      end=starts[i+1][0] if i+1<len(starts) else len(chars)
      cols[col]=''.join(c['text'] for c in chars[idx:end]).strip()
     assert section and cols[1] and cols[-1] in ['', 'Rookie'],(pn,y,cols)
     rows.append([section,*cols,str(pn)])
    elif text:
     assert text==text.upper() and re.search('[A-Z]',text),(pn,y,'Unclassified',text)
     if text not in ['BASE','AUTOGRAPHS','RELICS','AUTOGRAPH RELICS','INSERTS']:section=text
 assert len(rows)==config['count'] and len({r[0] for r in rows})==config['sections']
 base=[r for r in rows if r[0]=='BASE CARDS'];assert [int(r[1]) for r in base]==list(range(1,101))
 return rows,raw

def build():
 catalog_path=ROOT/'data/set-catalog.json';catalog=json.loads(catalog_path.read_text());replacements={}
 for slug,config in CONFIG.items():
  record=next(s for s in catalog['sets'] if s['slug']==slug);path=ROOT/'data/catalog-sources/downloads'/f'{slug}.pdf'
  subprocess.run(['curl','-sLf','--retry','2','--max-time','30',record['checklistUrl'],'-o',str(path)],check=True)
  rows,raw=read_cards(path,config);data_path=ROOT/record['tableData'];data=json.loads(data_path.read_text())
  data.update(headers=['Checklist section','Card number',*config['columns'],'Source page'],rows=rows,rawPages=raw,unclassifiedLines=[],sha256=hashlib.sha256(path.read_bytes()).hexdigest(),sectionColumn=0,importKind='topps-grid-pdf',dedicatedParser=PARSER)
  if slug=='topps-bowman-2026-topps-midnight-ufc':
   op=path.with_name(slug+'-odds.pdf')
   if data.get('oddsSource')!=UFC_ODDS:
    prior={'source':data.get('oddsSource'),'sha256':data.get('oddsSha256'),'reason':'Previously imported global-catalog PDF identifies 2025 and different insert families; replaced by the official 2026 product-page-linked document.','odds':data.get('odds',[]),'formats':data.get('formats',[])}
    data.setdefault('supersededOddsSources',[]).append(prior)
    if op.exists():op.with_name(slug+'-superseded-2025-odds.pdf').write_bytes(op.read_bytes())
   subprocess.run(['curl','-sLf','--retry','2','--max-time','30',UFC_ODDS,'-o',str(op)],check=True)
   odds,formats,oraw,issues=physical_odds_pdf(op)
   assert len(odds)==86 and formats==['Hobby'] and not issues
   assert oraw[0]['text'].startswith('2026 Topps Midnight UFC')
   for odd in odds:
    if odd['name'].startswith(('Celestial Combo ', 'Celstial Combos ', 'Celestial Combos ')):odd['family']='CELESTIAL COMBOS'
   data.update(odds=odds,formats=formats,oddsRawPages=oraw,oddsIssues=issues,oddsSource=UFC_ODDS,oddsSha256=hashlib.sha256(op.read_bytes()).hexdigest(),oddsParser='scripts/official_odds_layout.py')
   evidence=ROOT/'data/parallel-audit-sources/midnight-ufc-product-20261014.txt'
   data['publishedSpecifications']=[{'name':'FIGHT GLOVE RELIC AUTOGRAPHS','worksheet':'Official 2026 product page; limits are not assigned to named parallels','headers':['Manufacturer published field','Published value','Official source'],'rows':[['Family print limits (parallels not named)','Limited to 8 and 1',UFC_PAGE]],'evidenceFile':str(evidence.relative_to(ROOT)),'evidenceSha256':hashlib.sha256(evidence.read_bytes()).hexdigest()}]
   record.update(sourcePage=UFC_PAGE,oddsUrl=UFC_ODDS,odds=len(odds),formats=1,oddsImportIssues=0,oddsParser=data['oddsParser'])
   note='The 2026 product-page-linked odds PDF replaces a global-catalog link to a document identifying 2025 with different insert families. Original Celestial Combos spelling variants are preserved. The product page lists Fight Glove Relic Autographs as limited to 8 and 1, but does not assign those limits to named parallels or state serial numbering.'
   if note not in record['catalogEvidence']:record['catalogEvidence']+=' '+note
  data_path.write_text(json.dumps(data,ensure_ascii=False)+'\n')
  record.update(rowCount=len(rows),sections=config['sections'],sha256=data['sha256'],importKind=data['importKind'],dedicatedParser=PARSER,dataAudit=f"All {len(rows)} physical card rows and base numbers 1–100 reconciled to original glyph cell origins. Published names and rookie fields retained."+(' Raw/Smackdown/NXT/Legend/WWE designations and apparent source spelling errors remain separate from teams. Repeated printed card numbers are retained.' if 'royalty' in slug else ' Teams are not separately published.'))
  replacements[slug]=record
  print(record['title'],len(rows),'rows and all 100 printed base numbers.')
 for name in ['set-catalog.json','topps-product-official-catalog.json']:
  p=ROOT/'data'/name;c=json.loads(p.read_text());items=c['sets'] if isinstance(c,dict) else c;existing={r['slug'] for r in items}
  items[:]=[replacements.get(r['slug'],r) for r in items]
  items.extend(r for slug,r in replacements.items() if slug not in existing)
  p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':build()
