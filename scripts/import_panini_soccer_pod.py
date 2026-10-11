"""Import official Soccer Player of the Day physical PDF columns without OCR."""
import json,re,hashlib,subprocess
from pathlib import Path
import pdfplumber
ROOT=Path(__file__).resolve().parents[1]
URL='https://paninipod.com/wp-content/uploads/2026/04/2026-SOCCER-POD-checklist.pdf'
SLUG='panini-2026-panini-soccer-player-of-the-day'
def build():
 path=ROOT/'data/catalog-sources/downloads'/f'{SLUG}.pdf';subprocess.run(['curl','-sLf','--retry','2','--max-time','30',URL,'-o',str(path)],check=True);blob=path.read_bytes()
 rows=[];specs={'BASE SET':[],'GREATS':[]};raw=[]
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==1 and abs(pdf.pages[0].width-720)<1
  page=pdf.pages[0]
  for left,right,country_x in [(0,195,136),(195,365,302),(365,530,466),(530,720,631)]:
   col=page.crop((left,0,right,page.height));raw.append(col.extract_text());lines=[]
   for word in sorted(col.extract_words(),key=lambda w:(w['top'],w['x0'])):
    target=next((line for line in lines if abs(line[0]['top']-word['top'])<3),None)
    if target is None:lines.append([word])
    else:target.append(word)
   for line in lines:
    words=sorted(line,key=lambda w:w['x0']);text=' '.join(w['text'] for w in words)
    if text.startswith(('Base Set ','Rookies ')):
     match=re.fullmatch(r'(.+?)(?: \(# to (\d+)\))?',text);assert match
     family='BASE SET' if text.startswith('Base Set ') else 'GREATS'
     specs[family].append([match[1],f'# to {match[2]}' if match[2] else 'Not published','Not published']);continue
    if not re.match(r'^[\uf0a3□] ',text):continue
    code=words[1]['text'];assert re.fullmatch(r'\d+|[A-Z]+',code)
    name=' '.join(w['text'] for w in words[2:] if w['x0']<country_x)
    country=' '.join(w['text'] for w in words[2:] if w['x0']>=country_x)
    assert name and country,(code,name,country)
    family='BASE SET' if code.isdigit() and int(code)<=90 else 'GREATS' if code.isdigit() else 'AUTOGRAPHS' if left>=530 and words[0]['top']>310 else 'MARKETING INSERT'
    rows.append([family,code,name,country,'1'])
 assert len(rows)==136,len(rows)
 assert sorted(int(r[1]) for r in rows if r[1].isdigit())==list(range(1,101))
 assert sum(r[0]=='MARKETING INSERT' for r in rows)==18
 assert sum(r[0]=='AUTOGRAPHS' for r in rows)==18
 assert [len(specs[k]) for k in specs]==[7,7]
 rows.sort(key=lambda r:(['BASE SET','GREATS','MARKETING INSERT','AUTOGRAPHS'].index(r[0]),int(r[1]) if r[1].isdigit() else 0))
 payload={'title':'2026 Panini Soccer Player of the Day','headers':['Checklist section','Card number','Player / subjects','Published country','Source page'],'rows':rows,'source':URL,'sha256':hashlib.sha256(blob).hexdigest(),'importKind':'panini-pdf','sectionColumn':0,'rawPages':[{'page':1,'text':'\n\n'.join(raw)}],'publishedSpecifications':[{'name':family,'headers':['Parallel / variation','Published numbering','Pack odds'],'rows':values} for family,values in specs.items()]}
 dest=f'data/imports/{SLUG}.json';(ROOT/dest).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
 r={'title':payload['title'],'manufacturer':'Panini','sport':'soccer','year':'2026','slug':SLUG,'page':f'sets/{SLUG}.html','checklistUrl':URL,'sourcePage':'https://paninipod.com/','releaseStatus':'Released','releaseDate':None,'catalogEvidence':'Official Player of the Day program update says Soccer promotional kits began shipping May 4, 2026. This is a hobby-shop promotional set. The GREATS section prints parallel labels beginning Rookies; labels and spelling are preserved without inferring rookie status. Marketing code CP is printed for both Cole Palmer and Christian Pulisic; both rows remain present. Pack odds are not published.','verified':'2026-10-11','status':'Source table','tableData':dest,'rowCount':136,'sections':4,'parallelData':True,'publishedOdds':False,'importKind':'panini-pdf','sha256':payload['sha256'],'dataAudit':'All 136 printed rows and 14 published parallel/numbering entries imported using physical column alignment.'}
 for f in ['data/panini-official-catalog.json','data/set-catalog.json']:
  p=ROOT/f;value=json.loads(p.read_text());records=value['sets'] if isinstance(value,dict) else value;records[:]=[x for x in records if x['slug']!=SLUG]+[r];p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
 print('Imported 136 cards and 14 published numbering entries.')
if __name__=='__main__':build()
