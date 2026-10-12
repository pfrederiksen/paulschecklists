"""Import MLS Sapphire's official player/team/rookie columns and pack odds."""
import json,re,subprocess
from pathlib import Path
import pdfplumber
import import_official_catalog as generic
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-mls-sapphire'
URL='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/Topps-Chrome-Sapphire-MLS-2026-Checklist-Subject-to-Change.pdf?v=1791312276'
ODDS='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/Topps-Chrome-Sapphire-MLS-2026-Odds-Subject-to-Change.pdf?v=1791312256'
PAGE='https://jp.topps.com/pages/topps-chrome-sapphire-mls';TITLE='2026 Topps Chrome MLS Sapphire'
def build():
 p=ROOT/'data/topps-official-odds.json';registry=json.loads(p.read_text());registry=[r for r in registry if r['title']!=TITLE]+[{'title':TITLE,'url':ODDS}];p.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n');generic.ODDS[generic.norm(TITLE)]={'title':TITLE,'url':ODDS}
 record={'title':TITLE,'manufacturer':'Topps / Bowman','sport':'soccer','year':'2026','slug':SLUG,'page':f'sets/{SLUG}.html','sourcePage':PAGE,'checklistUrl':URL,'releaseStatus':'Unverified','releaseDate':None,'verified':'2026-10-11'}
 for suffix,url in [('.pdf',URL),('-odds.pdf',ODDS)]:
  path=ROOT/'data/catalog-sources/downloads'/f'{SLUG}{suffix}';subprocess.run(['curl','-sLf','--retry','2','--max-time','30',url,'-o',str(path)],check=True);path.with_suffix('.pdf.url').write_text(url)
 record=generic.run(record);dest=ROOT/record['tableData'];data=json.loads(dest.read_text());rows=[];section='Checklist'
 with pdfplumber.open(ROOT/'data/catalog-sources/downloads'/f'{SLUG}.pdf') as pdf:
  assert len(pdf.pages)==6
  for pn,page in enumerate(pdf.pages,1):
   lines={}
   for w in page.extract_words():lines.setdefault(round(w['top'],1),[]).append(w)
   for y,ws in sorted(lines.items()):
    ws.sort(key=lambda w:w['x0']);text=' '.join(w['text'] for w in ws)
    if re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',ws[0]['text']) and len(ws)>2:
     cols=[' '.join(w['text'] for w in ws if lo<=w['x0']<hi) for lo,hi in [(0,132),(132,284),(284,425),(425,page.width)]]
     assert all(cols[:3]) and cols[3] in ('','Rookie'),cols
     rows.append([section,*cols,str(pn)])
    elif text=='EXCLUSIVE TO SAPPHIRE CONFIGURATION':continue
    elif text==text.upper() and re.search('[A-Z]',text):section=text
 assert len(rows)==290
 # The standalone configuration qualifier is a note, not a card family.
 baseline=[(r[0].replace('EXCLUSIVE TO SAPPHIRE CONFIGURATION','INFINITE SAPPHIRE'),r[1],r[-1]) for r in data['rows']]
 assert [(r[0],r[1],r[-1]) for r in rows]==baseline
 assert [int(r[1]) for r in rows if r[0]=='BASE CARDS']==list(range(1,201))
 assert len(data['odds'])==15 and data['formats']==['Sapphire'] and not data['oddsIssues']
 assert next(o for o in data['odds'] if o['name']=='Infinite Sapphire Padparadscha')['values']['Sapphire']=='1:4,056'
 data.update(headers=['Checklist section','Card number','Name','Team','Rookie','Source page'],rows=rows)
 dest.write_text(json.dumps(data,ensure_ascii=False)+'\n')
 record.update(sections=3,parallelData=True,publishedOdds=True,dedicatedParser='scripts/import_topps_mls_sapphire_2026.py',sha256=data['sha256'],catalogEvidence='Official Topps Japan product page publishes both checklist and Sapphire odds. All 290 rows retain names, teams and rookie markers. Infinite Sapphire is explicitly exclusive to the Sapphire configuration. Sources are marked subject to change; subject inclusion does not guarantee every parallel. Exact release date has not been verified.',dataAudit='All physical-column rows reconciled against the catalog importer. Base numbers 1–200 and all 15 single-column odds values validated.')
 for name in ['topps-product-official-catalog.json','set-catalog.json']:
  p=ROOT/'data'/name;c=json.loads(p.read_text());items=c['sets'] if isinstance(c,dict) else c;items[:]=[r for r in items if r['slug']!=SLUG]+[record];p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 print('Imported 290 cards, 3 families and 15 Sapphire odds rows.')
if __name__=='__main__':build()
