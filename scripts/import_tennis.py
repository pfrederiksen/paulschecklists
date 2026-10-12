"""Refresh official tennis imports, preserving workbook and physical PDF fields."""
import json,re,hashlib,subprocess
from pathlib import Path
import pdfplumber,xlrd
import import_official_catalog as g
ROOT=g.ROOT

def build():
 catalog=json.loads((ROOT/'data/set-catalog.json').read_text());inventory=json.loads((ROOT/'data/topps-product-official-catalog.json').read_text())
 for record in inventory:
  if record.get('sport')!='tennis':continue
  slug=record['slug'];xls='.xls?' in record['checklistUrl'];path=g.CACHE/(slug+('.xls' if xls else '.pdf'))
  subprocess.run(['curl','-sLf','--retry','2','--max-time','30',record['checklistUrl'],'-o',str(path)],check=True);path.with_suffix(path.suffix+'.url').write_text(record['checklistUrl'])
  baseline=None
  if not xls:
   record.pop('dedicatedParser',None);record=g.run(record);baseline=json.loads((ROOT/record['tableData']).read_text())
  rows=[];section='Checklist';raw=[];unclassified=[]
  if xls:
   book=xlrd.open_workbook(str(path));sheet=book.sheet_by_index(0);assert sheet.ncols==4
   raw_values=[]
   for rn in range(sheet.nrows):
    values=sheet.row_values(rn);raw_values.append(values)
    number=values[0];number=str(int(number)) if isinstance(number,float) and number.is_integer() else str(number)
    if not any(values):continue
    if values[1]:
     assert not values[2] and values[3] in ('','Rookie'),values
     rows.append([section,number,str(values[1]),str(values[3]),sheet.name,str(rn+1)])
    elif number.isupper() and len(number)<100:section=number
    else:unclassified.append(values)
   raw=[{'worksheet':sheet.name,'rows':raw_values}];assert [int(r[1]) for r in rows if r[0].startswith('BASE CARDS')]==list(range(1,201))
   headers=['Checklist section','Card number','Name','Rookie','Source worksheet','Source row']
  else:
   name_x=120 if 'Triumphant' in record['title'] else 132;rookie_x=421
   with pdfplumber.open(path) as pdf:
    for pn,page in enumerate(pdf.pages,1):
     raw.append({'page':pn,'text':page.extract_text()});lines={}
     for w in page.extract_words():lines.setdefault(round(w['top'],1),[]).append(w)
     for y,ws in sorted(lines.items()):
      ws.sort(key=lambda w:w['x0']);text=' '.join(w['text'] for w in ws)
      if text=='Card No. Player Name' or text=='*SUBJECT TO CHANGE*':continue
      if re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',ws[0]['text']):
       number=' '.join(w['text'] for w in ws if w['x0']<name_x);name=' '.join(w['text'] for w in ws if name_x<=w['x0']<rookie_x);rookie=' '.join(w['text'] for w in ws if w['x0']>=rookie_x)
       assert name and rookie in ('','Rookie'),text
       if '(RC)' in name:rookie='Rookie'
       rows.append([section,number,name,rookie,str(pn)])
      elif text==text.upper() and re.search('[A-Z]',text):section=text
      elif rows and ws[0]['x0']>=name_x and 'Triumphant' in record['title']:
       rows[-1][2]+=' / '+text
       if '(RC)' in text:rows[-1][3]='Rookie'
      elif text:unclassified.append({'page':pn,'text':text})
   assert len(rows)==len(baseline['rows'])
   headers=['Checklist section','Card number','Name','Rookie','Source page']
   if 'Triumphant' in record['title']:assert rows[-1][2].endswith('Iga Świątek');assert len(rows)==120
  payload={**(baseline or {}),'title':record['title'],'headers':headers,'rows':rows,'source':record['checklistUrl'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rawPages':raw,'unclassifiedLines':unclassified,'importKind':'pdf','sectionColumn':0}
  odds=g.ODDS.get(g.norm(record['title']))
  if odds:
   op=g.CACHE/(slug+'-odds.pdf');blob=g.fetch(odds['url'],op);entries,formats,text,issues=g.odds_pdf(op);assert not issues,issues
   # The Graphite heading explicitly names Hobby; preserve it without the Card label.
   if 'Graphite' in record['title']:
    original=formats[0];formats=['2026 TOPPS GRAPHITE TENNIS HOBBY']
    for entry in entries:entry['values']={formats[0]:entry['values'][original]}
   payload.update(odds=entries,formats=formats,oddsSource=odds['url'],oddsSha256=hashlib.sha256(blob).hexdigest(),oddsRawPages=text,oddsIssues=issues)
   record.update(odds=len(entries),formats=len(formats),oddsUrl=odds['url'],oddsImportIssues=0)
  specs=[]
  if 'Graphite' in record['title']:specs=[('BASE CARDS',['Purple /99','Gold /25','White /10','Red Crystalline Refractor 1/1']),('Hobby box contents',['4 autographs per box','2 relic cards per box'])]
  elif 'Triumphant' in record['title']:specs=[('BASE',['Serial-numbered to 99 or less']),('Autograph box contents',['3 serial-numbered autographs /99 or less per box']),('GRAND SLAM QUAD AUTOGRAPHS',['1/1'])]
  elif 'Sapphire' in record['title']:specs=[('Sapphire box contents',['4 cards per pack','8 packs per box','3 exclusive Sapphire parallels per box','1 autograph card per box'])]
  else:
   specs=[('Hobby box contents',['2 Chrome autograph cards per box'])]
   record['catalogEvidence']='Official workbook lists 200 base cards across BASE CARDS and BASE CARDS II, while the product overview says 300. Workbook entries govern this checklist. Original Hobby SKU, Breaker SKU and Value SKU odds headings are preserved. Exact release date is not verified.'
  payload['publishedSpecifications']=[{'name':name,'worksheet':'Official product page','headers':['Published specification','Official source'],'rows':[[v,record['sourcePage']] for v in values]} for name,values in specs]
  dest='data/imports/'+slug+'.json';(ROOT/dest).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
  record.update(tableData=dest,status='Source table',importKind='pdf',dedicatedParser='scripts/import_tennis.py',rowCount=len(rows),sections=len(set(r[0] for r in rows)),parallelData=bool(payload.get('odds') or specs),publishedOdds=bool(payload.get('odds')),dataAudit='Original player and rookie fields preserved. Multi-player card names include every printed continuation. Published odds retain original values and source headings; no teams inferred.')
  catalog['sets']=[r for r in catalog['sets'] if r['slug']!=slug]+[record]
  print(record['title'],len(rows),'rows',len(payload.get('odds',[])),'odds',payload.get('formats',[]))
 (ROOT/'data/topps-product-official-catalog.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n');(ROOT/'data/set-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':build()
