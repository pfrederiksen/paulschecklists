"""Reconcile product-page Marvel PDFs, physical autograph columns and artist rosters."""
import json,re,sys
from pathlib import Path
import pdfplumber
import import_official_catalog as g
ROOT=g.ROOT
p=ROOT/'data/set-catalog.json';catalog=json.loads(p.read_text())
for r in catalog['sets']:
 if r['title'] not in ['2026 Topps Mint Marvel','2026 Topps Vault Marvel']:continue
 r.pop('dedicatedParser',None);r=g.run(r);d=json.loads((ROOT/r['tableData']).read_text());path=g.CACHE/(r['slug']+'.pdf')
 if 'Mint' in r['title']:
  rows=[];family='Checklist'
  with pdfplumber.open(path) as pdf:
   for pn,page in enumerate(pdf.pages,1):
    groups=[]
    for word in page.extract_words():
     if not groups or abs(word['top']-groups[-1][0]['top'])>3:groups.append([word])
     else:groups[-1].append(word)
    for words in groups:
     words=sorted(words,key=lambda w:w['x0']);line=' '.join(w['text'] for w in words)
     if line.startswith(('Checklists provided','at the time of production','Card Number')) or line=='Artist':continue
     if pn>=11:
      if line=='SKETCH CARDS & SKETCH CARDS: SPIDER-MAN VILLAINS EDITION':family=line;continue
      rows.append([family,'',line,str(pn),'','','','',line]);continue
     if line==line.upper() and not words[0]['text'].isdigit():family=line;continue
     number=words[0]['text'];assert re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number),(pn,line)
     desc=' '.join(w['text'] for w in words[1:]);name=character=prop=issue=''
     if pn==9:
      name=' '.join(w['text'] for w in words[1:] if w['x0']<253)
      character=' '.join(w['text'] for w in words[1:] if 253<=w['x0']<361)
      prop=' '.join(w['text'] for w in words[1:] if w['x0']>=361)
     elif pn==10:issue=desc
     else:character=desc
     rows.append([family,number,name or character or issue,str(pn),name,character,prop,issue,''])
  assert len([r for r in rows if r[0].startswith('BASE CARDS') and 'CHROME' not in r[0]])==125
  assert len([r for r in rows if r[0].startswith('BASE CARDS') and 'CHROME' in r[0]])==125
  assert len([r for r in rows if r[0]=='SPIDER-MAN COMIC CUTS'])==15
  assert any(r[8]=="Vincenzo D'ippolito" for r in rows)
  d.update(headers=['Checklist section','Card number','Player / subjects','Source page','Name','Character','Property','Issue','Artist'],rows=rows,dedicatedParser='scripts/import_marvel_2026.py')
  d['publishedSpecifications']=[{'name':'BASE CARDS – PLATINUM TIER','worksheet':'Official product page; numbering is not pack odds','headers':['Published tier','Published numbering qualifier','Source'],'rows':[['Platinum','Numbered to 99 or less',r['sourcePage']]]},{'name':'CEREBRO','worksheet':'Official product page; numbering is not pack odds','headers':['Published category','Published numbering qualifier','Source'],'rows':[['Cerebro','Numbered to 99 or less',r['sourcePage']]]}]
  r['catalogEvidence']='Official checklist physical rows reconciled: 125 base characters and 125 Chrome variations; original Name, Character, Property, Issue and Artist fields preserved. Unnumbered artist roster entries have no invented card numbers. Product-page numbering qualifiers are separate from the 76 published odds entries. Exact release date is unverified.'
 else:
  # Reconcile every numbered row to physical columns; keep ambiguous artist wraps literal.
  physical=[]
  with pdfplumber.open(path) as pdf:
   for pn,page in enumerate(pdf.pages,1):
    groups=[]
    for word in page.extract_words():
     if not groups or abs(word['top']-groups[-1][0]['top'])>3:groups.append([word])
     else:groups[-1].append(word)
    for words in groups:
     words=sorted(words,key=lambda w:w['x0'])
     if not re.fullmatch(r'[A-Z]+-[A-Z0-9]+',words[0]['text']):continue
     cells=[' '.join(w['text'] for w in words[1:] if lo<=w['x0']<hi) for lo,hi in [(120,275),(275,440),(440,1000)]]
     physical.append((words[0]['text'],pn,cells))
  assert len(physical)==len(d['rows'])==377
  rows=[]
  for original,(number,pn,cells) in zip(d['rows'],physical):
   assert original[1]==number,(original,number)
   family={'RELICS':'VAULT RELICS','SET':'FROM THE SET'}.get(original[0],original[0]);actor=character=relic=artist=''
   if family=='VAULT ORIGINALS':character,artist=cells[:2]
   elif family in ['VAULT RELICS','VAULT ARMORY','FROM THE SET']:character,relic=cells[:2]
   elif family in ['MARVEL DIAMONDS','TRUE GREATNESS']:character=cells[0]
   else:actor,character,relic=cells
   rows.append([family,number,' / '.join(x for x in [actor,character] if x),str(pn),actor,character,relic,artist])
  assert next(x for x in rows if x[1]=='AR-HF')[4:7]==['Harrison Ford','President Thaddeus Ross','Presidental Podium']
  family=None;artistrows=[]
  with pdfplumber.open(path) as pdf:
   for pn,page in enumerate(pdf.pages,1):
    if pn<8:continue
    for line in (page.extract_text() or '').splitlines():
     if line in ['GOLDEN SKETCHES','OVERSIZED PREMIERE SKETCHES','PREMIERE SKETCHES']:family=line;continue
     if family and line and line!='SKETCH':artistrows.append([family,'',line,str(pn),'','','',line])
  d.update(headers=['Checklist section','Card number','Player / subjects','Source page','Actor','Character','Relic / prop','Artist'],rows=rows+artistrows)
  r['coverageComplete']=False;d['coverageComplete']=False
  r['catalogEvidence']='All 377 numbered source rows are reconciled to physical Actor, Character, Relic / prop and Artist columns; repeated numbers for multiple signers are preserved. The literal sketch-artist lines are retained, but wrapped artist-name grouping remains unverified. Counts are source rows, not unique cards or artists. All 74 published odds entries are imported. Exact release date is unverified.'
 r['dataAudit']=r['catalogEvidence']
 r.update(dedicatedParser='scripts/import_marvel_2026.py',rowCount=len(d['rows']),sections=len(set(x[0] for x in d['rows'])),parallelData=True)
 d['unclassifiedLines']=[] if 'Mint' in r['title'] else d.get('unclassifiedLines',[])
 (ROOT/r['tableData']).write_text(json.dumps(d,ensure_ascii=False)+'\n')
 for i,old in enumerate(catalog['sets']):
  if old['slug']==r['slug']:catalog['sets'][i]=r
 print(r['title'],len(d['rows']),'source rows',len(d['odds']),'odds')
p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
