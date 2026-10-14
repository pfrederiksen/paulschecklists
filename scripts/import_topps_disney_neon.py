"""Preserve Disney Neon's original PDF text objects and tagged odds cells."""
import json,re,hashlib,collections,subprocess
from pathlib import Path
import pdfplumber
from pypdf import PdfReader
import import_official_catalog as generic
ROOT=generic.ROOT;SLUG='topps-bowman-2026-topps-disney-neon'
def parse_cards(path):
 reader=PdfReader(path);rows=[];notes=[];raw=[];family='Checklist'
 for pn,page in enumerate(reader.pages,1):
  grouped=collections.defaultdict(list)
  def visit(text,cm,tm,font,size):
   text=' '.join(text.split())
   if text:grouped[round(tm[5],2)].append((tm[4],text,str(font.get('/BaseFont','')) if font else ''))
  raw.append({'page':pn,'text':page.extract_text(visitor_text=visit)})
  for y,chunks in sorted(grouped.items(),reverse=True):
   if any(text=='Card Number' for x,text,font in chunks):continue
   if any(text.startswith('*') for x,text,font in chunks):notes.append([str(pn),' '.join(text for x,text,font in chunks)]);continue
   if len(chunks)==1 and 'Bold' in chunks[0][2]:family=chunks[0][1];continue
   cols=['']*5
   for x,text,font in chunks:
    # Text-matrix origins retain the source columns despite touching glyphs,
    # small page scaling, and names that overlap adjacent visible columns.
    ix=(0 if x<184 else 3 if x<361 else 4) if pn<3 else (0 if x<278 else 3 if x<461 else 4) if pn<5 else (0 if x<172 else 1 if x<251 else 2 if x<332 else 3 if x<471 else 4)
    assert not cols[ix],(pn,y,chunks,cols);cols[ix]=text
   assert re.fullmatch(r'\d+|[A-Za-z&]+-[A-Za-z0-9-]+',cols[0]),(pn,y,chunks)
   subject=' '.join(c for c in cols[1:3] if c) or cols[3]
   rows.append([family,cols[0],subject,str(pn),*cols[1:]])
 assert len(rows)==720
 assert [int(r[1]) for r in rows if r[0]=='BASE CARDS']==list(range(1,201))
 return rows,raw,notes
def parse_odds(path,source):
 odds=[];raw=[];formats=None
 with pdfplumber.open(path) as pdf:
  for pn,page in enumerate(pdf.pages,1):
   raw.append({'page':pn,'text':page.extract_text()});tagged=collections.defaultdict(list)
   for c in page.chars:
    if c.get('mcid') is not None:tagged[c['mcid']].append(c)
   tables=page.find_tables();assert len(tables)==1
   for row in tables[0].rows:
    cells=[]
    for box in row.cells:
     mids={c['mcid'] for c in page.chars if c.get('mcid') is not None and box[0]<(c['x0']+c['x1'])/2<box[2] and box[1]<(c['top']+c['bottom'])/2<box[3]}
     assert len(mids)==1,(pn,box,mids)
     text='';top=None
     # Original PDF draw order joins wrapped labels without nearby-row text.
     for c in tagged[next(iter(mids))]:
      if top is not None and abs(c['top']-top)>3 and text and not text.endswith(' '):text+=' '
      text+=c['text'];top=c['top']
     cells.append(' '.join(text.split()))
    if cells[0]=='Cards':
     if formats is None:formats=cells[1:]
     else:assert formats==cells[1:]
     continue
    assert all(v=='-' or re.fullmatch(r'[\d,]+:[\d,]+',v) for v in cells[1:])
    odds.append({'name':cells[0],'values':dict(zip(formats,[None if v=='-' else v for v in cells[1:]])),'page':pn})
 assert len(odds)==108 and len(formats)==7
 # These are exact source family aliases, not individual-card eligibility.
 aliases={'A Goofy Movie 30th Anniversary Auto Variation':'A GOOFY MOVIE AUTOGRAPH VARIATION','Mickey Shorts Dual Autograph':'MICKEY SHORTS SHORT PRINTS DUAL AUTOGRAPH VARIATION','Mickey Shorts Short Prints Auto Variation':'MICKEY SHORTS SHORT PRINTS AUTOGRAPH VARIATION','Phineas and Ferb Auto Variation':'PHINEAS AND FERB AUTOGRAPH VARIATION','Triple Booklet Superfractor':'TRIPLE BOOKLET SUPERFRACTOR AUTOGRAPH CARD','A Goofy Movie 30th Anniversary':'A GOOFY MOVIE','Magic Carpet Acetate Card':'MAGIC CARPET RIDE','Neon Villains':'NEON VILLAINS INSERT','Chrome Neon Etch Autos':'CHROME NEON ETCH AUTOGRAPHS'}
 for odd in odds:
  for prefix,family in aliases.items():
   if odd['name'].startswith(prefix):odd['family']=family;break
  if odd['name']=='Topps Neon Autographs PETG Pink 1/1 Parallel':
   odd['numbering']='1/1';odd['numberingSource']={'url':source,'qualification':'Numbering is explicitly printed in this category label; no other color limit is inferred.'}
 return odds,formats,raw
def build():
 catalog=json.loads((ROOT/'data/set-catalog.json').read_text());record=next(r for r in catalog['sets'] if r['slug']==SLUG)
 for suffix,url in [('.pdf',record['checklistUrl']),('-odds.pdf',record['oddsUrl'])]:
  path=generic.CACHE/(SLUG+suffix);subprocess.run(['curl','-sLf','--retry','2','--max-time','45',url,'-o',str(path)],check=True);path.with_suffix('.pdf.url').write_text(url)
 cp=generic.CACHE/(SLUG+'.pdf');op=generic.CACHE/(SLUG+'-odds.pdf')
 rows,raw,notes=parse_cards(cp);odds,formats,oraw=parse_odds(op,record['oddsUrl'])
 data={'title':record['title'],'headers':['Checklist section','Card number','Player / subjects','Source page','First Name','Last Name','Character','Property'],'rows':rows,'rawPages':raw,'sourceSheets':[{'name':'Official checklist notes','notes':notes}],'source':record['checklistUrl'],'sha256':hashlib.sha256(cp.read_bytes()).hexdigest(),'importKind':'pdf','sectionColumn':0,'dedicatedParser':'scripts/import_topps_disney_neon.py','odds':odds,'formats':formats,'oddsRawPages':oraw,'oddsSource':record['oddsUrl'],'oddsSha256':hashlib.sha256(op.read_bytes()).hexdigest(),'oddsIssues':[],'unclassifiedLines':[]}
 Path(record['tableData']).write_text(json.dumps(data,ensure_ascii=False)+'\n')
 record.update(rowCount=len(rows),sections=len(set(r[0] for r in rows)),odds=len(odds),formats=len(formats),dedicatedParser=data['dedicatedParser'],sha256=data['sha256'],coverageComplete=False,parallelData=True,publishedOdds=True,dataAudit='All 720 printed source entries reconciled using original PDF text-matrix columns, including 200 base numbers and repeated autograph signers. All 108 tagged odds rows and seven formats imported; eight categories have no published odds in any format. Exhaustive parallel numbering review remains pending.',catalogEvidence='Original First Name, Last Name, Character and Property fields are retained as printed; the Property column contains companion characters in some families and is not reinterpreted. Source-entry counts are not unique cards or subjects. Pack ratios retain their original units. Exact release date is unverified.')
 (ROOT/'data/set-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 p=ROOT/'data/topps-product-official-catalog.json';items=json.loads(p.read_text());old=next((r for r in items if r['slug']==SLUG),None)
 if old:old.update(record)
 else:items.append(record)
 p.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
 print('Imported 720 original-column checklist entries, 200 base cards and all 108 tagged odds categories.')
if __name__=='__main__':build()
