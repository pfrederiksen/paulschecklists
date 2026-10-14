"""Dedicated imports for verified 2026 catalog backfills; no inferred subjects."""
from pathlib import Path
import json,re,hashlib,urllib.request,collections
import pdfplumber,xlrd
import import_official_catalog as generic
ROOT=generic.ROOT;CACHE=generic.CACHE
PREFIX='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/'
CONFIG=[
 ('2026 Topps Brooklyn Collection','marvel','topps-brooklyn-collection','2026_Topps_Brooklyn_Collection_Checklist.pdf?v=1772572812','2026_Topps_Brooklyn_Collection_Odds.pdf?v=1772572812','brooklyn'),
 ('2026 Topps MLB x KAWS','baseball',None,'KAWs_Checklist.pdf?v=1784208798','KAWS_Odds.pdf?v=1784559267','kaws'),
 ('2026 Topps Chrome UFC','ufc','topps-chrome-ufc','FINAL_CheckList_2026_TOPPS_CHROME_UFC_V2.xls?v=1779204573','2026_UFC_Chrome_Odds.pdf?v=1779134050','xls'),
 ('2026 Topps Chrome UFC Sapphire Edition','ufc','topps-chrome-sapphire-ufc','FINAL_CheckList_2026_TOPPS_CHROME_SAPPHIRE_UFC.xls?v=1779982792','2026_Topps_Chrome_UFC_Sapphire.pdf?v=1781705060','xls'),
 ('2026 Topps Collector Kit','multi-sport',None,'Collector_Kit_1.pdf?v=1774449045',None,'collector'),
]
def acquire(url,path):
 path.write_bytes(urllib.request.urlopen(url,timeout=40).read());path.with_suffix(path.suffix+'.url').write_text(url);return hashlib.sha256(path.read_bytes()).hexdigest()
def lines(page):
 grouped=collections.defaultdict(list)
 for w in page.extract_words(x_tolerance=1):grouped[round(w['top'],1)].append(w)
 return [(y,sorted(ws,key=lambda w:w['x0'])) for y,ws in sorted(grouped.items())]
def parse_brooklyn(path):
 rows=[];raw=[];section='Checklist'
 with pdfplumber.open(path) as pdf:
  for pn,p in enumerate(pdf.pages,1):
   raw.append({'page':pn,'text':p.extract_text()})
   for y,ws in lines(p):
    text=' '.join(w['text'] for w in ws)
    if re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',ws[0]['text']):
     number=' '.join(w['text'] for w in ws if w['x0']<130);name=' '.join(w['text'] for w in ws if 130<=w['x0']<268);column=' '.join(w['text'] for w in ws if w['x0']>=268)
     assert name,(pn,text);rows.append([section,number,name,column,str(pn)])
    elif ws[0]['x0']<90 and text==text.upper():section=text
    elif section=='SKETCH CARD ARTISTS' and ws[0]['x0']>=130:rows.append([section,'',text,'',str(pn)])
    else:raise ValueError(('Unclassified Brooklyn line',pn,text))
 assert [int(r[1]) for r in rows if r[0]=='BASE CARDS']==list(range(1,51))
 return ['Checklist section','Card number','Name','Original third column (as printed)','Source page'],rows,raw

def parse_kaws(path):
 rows=[];raw=[];section='Checklist';headers={'Base Cards:':'BASE CARDS','KAWS Creation:':'KAWS CREATION','KAWS Companion SPS:':'KAWS COMPANION SPS','KAWS Companion SSP AUTOS:':'KAWS COMPANION SSP AUTOS','Autographs':'AUTOGRAPHS','On-Card Autographs':'ON-CARD AUTOGRAPHS'}
 with pdfplumber.open(path) as pdf:
  for pn,p in enumerate(pdf.pages,1):
   raw.append({'page':pn,'text':p.extract_text()});ls=lines(p)
   anchors=[]
   for y,ws in ls:
    text=' '.join(w['text'] for w in ws)
    if text in headers:section=headers[text]
    # Number-column glyphs anchor physical cells; wrapped names may begin
    # above their number, so ordinary line-by-line continuation is unsafe.
    left=[w for w in ws if w['x0']<100]
    if left and re.fullmatch(r'\d+|\d+-A|KC-\d+|SP-K\d+|SSP-K\d+',left[0]['text']):anchors.append((y,left[0]['text'],section))
   for i,(y,number,sec) in enumerate(anchors):
    lo=(anchors[i-1][0]+y)/2 if i else y-12
    hi=(y+anchors[i+1][0])/2 if i+1<len(anchors) else y+13
    words=[w for w in p.extract_words(x_tolerance=1) if 100<=w['x0'] and lo<=w['top']<hi]
    # Column-free section headings cannot leak into a final player cell.
    name=' '.join(w['text'] for w in sorted(words,key=lambda w:(round(w['top'],1),w['x0'])) if not any(abs(yy-w['top'])<1 and ww[0]['x0']<100 and not re.fullmatch(r'\d+|\d+-A|KC-\d+|SP-K\d+|SSP-K\d+',ww[0]['text']) for yy,ww in ls))
    rows.append([sec,number,name,str(pn)])
 assert [int(r[1]) for r in rows if r[0]=='BASE CARDS']==list(range(1,61))
 assert len([r for r in rows if r[0]=='KAWS CREATION'])==25
 assert len([r for r in rows if r[0]=='KAWS COMPANION SPS' and not r[2]])==10
 assert next(r[2] for r in rows if r[1]=='9-A')=='Gunnar Henderson'
 assert next(r[2] for r in rows if r[1]=='32-A')=='Vladimir Guerrero Jr.'
 assert next(r[2] for r in rows if r[1]=='14-A')=='Yoshinobu Yamamoto'
 return ['Checklist section','Card number','Name','Source page'],rows,raw

def parse_xls(path):
 sheet=xlrd.open_workbook(str(path)).sheet_by_index(0);rows=[];section='Checklist';raw=[];notes=[]
 for i in range(sheet.nrows):
  v=sheet.row_values(i);v=[str(int(x)) if isinstance(x,float) and x.is_integer() else str(x) for x in v];raw.append(v)
  if not any(v):continue
  if v[1]:assert v[0],v;rows.append([section,*v,sheet.name,str(i+1)])
  elif v[0].startswith('Checklists provided'):notes.append(v[0])
  elif v[0].isupper():section=v[0]
  elif v[0].startswith('2026 Topps Chrome Sapphire UFC Checklist'):pass
  else:raise ValueError(('Unclassified workbook row',i+1,v))
 assert [int(r[1]) for r in rows if r[0] in ['BASE CARDS I','BASE CARDS II']]==list(range(1,201))
 return ['Checklist section','Card number','Name','Original third column','Rookie','Source worksheet','Source row'],rows,[{'worksheet':sheet.name,'rows':raw,'notes':notes}]

def build():
 catalog=json.loads((ROOT/'data/set-catalog.json').read_text());inventory=json.loads((ROOT/'data/topps-product-official-catalog.json').read_text())
 for title,sport,page,cl,od,kind in CONFIG:
  slug='topps-bowman-'+re.sub('[^a-z0-9]+','-',title.lower()).strip('-');source='https://www.topps.com/pages/'+page if page else 'https://www.topps.com/pages/checklists'
  if 'Sapphire' in title:source='https://uk.topps.com/pages/'+page
  suffix='.xls' if kind=='xls' else '.pdf';path=CACHE/(slug+suffix);ch=acquire(PREFIX+cl,path)
  if kind=='brooklyn':headers,rows,raw=parse_brooklyn(path)
  elif kind=='kaws':headers,rows,raw=parse_kaws(path)
  elif kind=='xls':headers,rows,raw=parse_xls(path)
  else:
   rows=[];raw=[];section='Checklist'
   with pdfplumber.open(path) as pdf:
    for pn,p in enumerate(pdf.pages,1):
     raw.append({'page':pn,'text':p.extract_text()})
     for y,ws in lines(p):
      text=' '.join(w['text'] for w in ws)
      if re.fullmatch(r'(?:MLB|NBA)-\d+',ws[0]['text']):
       values=[' '.join(w['text'] for w in ws if a<=w['x0']<b) for a,b in [(0,130),(130,268),(268,421),(421,1000)]]
       assert values[3] in ('','Rookie'),values;rows.append([section,*values,str(pn)])
      else:section=text
   headers=['Checklist section','Card number','Name','Team','Rookie','Source page'];assert len(rows)==10
  payload={'title':title,'headers':headers,'rows':rows,'source':PREFIX+cl,'sha256':ch,'importKind':'xls' if kind=='xls' else 'pdf','sectionColumn':0,'dedicatedParser':'scripts/import_topps_october_inventory.py'}
  payload['sourceSheets' if kind=='xls' else 'rawPages']=raw
  if od:
   op=CACHE/(slug+'-odds.pdf');oh=acquire(PREFIX+od,op)
   if kind=='brooklyn':
    odds=[];oraw=[]
    with pdfplumber.open(op) as pdf:
     for pn,p in enumerate(pdf.pages,1):
      oraw.append({'page':pn,'text':p.extract_text()})
      for t in p.extract_tables():
       for row in t:
        if row[0]=='Cards':continue
        assert len(row)==2 and re.fullmatch(r'[\d,]+:[\d,]+',row[1]),row
        odds.append({'name':' '.join(row[0].split()),'values':{'Hobby':row[1]},'page':pn})
    formats=['Hobby'];issues=[]
   elif kind=='kaws':
    odds=[];oraw=[];formats=['Pack'];issues=[]
    with pdfplumber.open(op) as pdf:
     for pn,p in enumerate(pdf.pages,1):
      oraw.append({'page':pn,'text':p.extract_text()})
      for y,ws in lines(p):
       ratio=[w for w in ws if re.fullmatch(r'[\d,]+:[\d,]+',w['text'])]
       if not ratio:continue
       assert len(ratio)==1
       label=' '.join(w['text'] for w in ws if w is not ratio[0]);assert label.startswith('26TNKB - '),label
       family=next((family for prefix,family in [('BASE CARDS','BASE CARDS'),('KAWS CREATION INSERT','KAWS CREATION'),('BASE AUTOGRAPHS','AUTOGRAPHS'),('COMPANION SP','KAWS COMPANION SPS'),('KAWS AUTOGRAPHS SSP','KAWS COMPANION SSP AUTOS')] if label.removeprefix('26TNKB - ').startswith(prefix)),None);assert family,label
       odds.append({'name':label,'family':family,'values':{'Pack':ratio[0]['text']},'page':pn})
    assert len(odds)==22
   else:odds,formats,oraw,issues=generic.odds_pdf(op)
   assert not issues,issues
   if title=='2026 Topps Chrome UFC':
    base_end=next(i for i,o in enumerate(odds) if o['name'].startswith('FrozenFractors('))+1
    for odd in odds[:base_end]:
     odd['family']='BASE CARDS I';odd['familyAliases']=['BASE CARDS II']
     if odd['name'].startswith('FrozenFractors('):
      odd['numbering']=odd['name'].split('(',1)[1].rstrip(')');odd['numberingSource']={'url':PREFIX+od,'qualification':'Printed negative card numbers; no /5 serial limit is inferred.'}
   payload.update(odds=odds,formats=formats,oddsSource=PREFIX+od,oddsSha256=oh,oddsRawPages=oraw,oddsIssues=issues)
  dest='data/imports/'+slug+'.json';(ROOT/dest).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
  notes='Dedicated physical rows preserve blank names, wrapped player cells and unnumbered artist entries. Original source fields and odds units are retained; parallel numbering is not inferred.'
  record={'title':title,'slug':slug,'page':'sets/'+slug+'.html','manufacturer':'Topps / Bowman','sport':sport,'year':'2026','sourcePage':source,'checklistUrl':PREFIX+cl,'releaseStatus':'Unverified','releaseDate':None,'verified':'2026-10-13','status':'Source table','tableData':dest,'rowCount':len(rows),'sections':len(set(r[0] for r in rows)),'importKind':payload['importKind'],'dedicatedParser':payload['dedicatedParser'],'sha256':ch,'coverageComplete':False,'parallelData':bool(od),'publishedOdds':bool(od),'catalogEvidence':'Official 2026 checklist verified against its product page or manufacturer catalog. Release date is not inferred from checklist availability. Printed roster and available odds are imported; additional parallel numbering specifications still require reconciliation for every family.','dataAudit':notes}
  if od:record.update(odds=len(odds),formats=len(formats),oddsUrl=PREFIX+od)
  for data in [catalog['sets'],inventory]:
   old=next((r for r in data if r.get('slug')==slug),None)
   if old:old.update(record)
   else:data.append(record)
  print(title,len(rows),'rows;',len(payload.get('odds',[])),'odds',flush=True)
 (ROOT/'data/topps-product-official-catalog.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n');(ROOT/'data/set-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':build()
