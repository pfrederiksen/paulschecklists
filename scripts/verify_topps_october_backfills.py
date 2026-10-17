"""Check original physical IDs, source fields, signers, flags and scoped odds."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_october_backfills import CONFIG,SAPPHIRE,BOWMAN,BASKETBALL,DISNEY,ARTISTS
ROOT=Path(__file__).resolve().parents[1]
compact=lambda text:re.sub(r'\s+','',text)
for slug,cfg in CONFIG.items():
 d=json.loads((ROOT/'data/imports'/(slug+'.json')).read_text());p=ROOT/'data/catalog-sources/downloads'/(slug+'.pdf')
 assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']
 assert d['dedicatedParser']=='scripts/import_topps_october_backfills.py'
 assert len(d['rows'])==cfg['count'] and len({r[0] for r in d['rows']})==cfg['sections']
 original=collections.Counter();printed=collections.Counter()
 with pdfplumber.open(p) as pdf:
  for pn,page in enumerate(pdf.pages,1):
   if slug==BOWMAN and pn>16:continue
   number_lines=collections.defaultdict(list)
   for w in page.extract_words(x_tolerance=.1,extra_attrs=['fontname']):
    if 'Bold' in w['fontname'] or w['x1']>=cfg['origins'][0]-.05:continue
    if pn==1 and w['top']<cfg['skip']:continue
    if slug==DISNEY and (pn>8 or pn==8 and w['top']>593.8):continue
    number_lines[round(w['top'],1)].append(w)
   for y,words in number_lines.items():
    code=''.join(w['text'] for w in sorted(words,key=lambda w:w['x0']))
    if re.fullmatch(r'[A-Z0-9]+(?:[-&][A-Z0-9]+)*',code):
     original[(str(pn),code)]+=1
     text=''.join(c['text'] for c in page.chars if abs(c['top']-y)<2)
     printed[(str(pn),compact(text))]+=1
 assert original==collections.Counter((r[-1],r[1]) for r in d['rows'] if r[1]),(slug,list((original-collections.Counter((r[-1],r[1]) for r in d['rows'] if r[1])).items())[:5],list((collections.Counter((r[-1],r[1]) for r in d['rows'] if r[1])-original).items())[:5])
 assert printed==collections.Counter((r[-1],compact(''.join(r[1:-1]))) for r in d['rows'] if r[1]),(slug,'Every glyph in each numbered source row must survive in its original field')
 proof=d['productConfigurationEvidence'];assert hashlib.sha256((ROOT/proof['file']).read_bytes()).hexdigest()==proof['sha256']
 rows=d['rows']
 if slug==SAPPHIRE:
  assert [int(r[1]) for r in rows if r[0]=='BASE CARDS']==list(range(1,301))
  assert [int(r[1]) for r in rows if r[0]=='ROOKIE']==list(range(301,401))
  assert sum(r[4]=='Rookie' for r in rows)==252
  assert not any(r[1]=='1990' for r in rows)
  assert len([r for r in rows if r[0]=='1990 TOPPS FOOTBALL AUTOGRAPHS'])==31
  assert [r[2] for r in rows if r[1]=='DA-BW']==['Brock Bowers','Tyler Warren']
  assert [r[4] for r in rows if r[1]=='DA-HMA']==['',''],'Do not infer rookie marks from a name'
  scope=d['oddsScope'];assert len(d['odds'])==55 and d['formats']==[scope]
  assert len(d['officialOddsTable'])==505 and len(d['officialOddsFormats'])==14
  assert d['odds']==[{**o,'values':{scope:o['values'][scope]}} for o in d['officialOddsTable'] if o['values'][scope] is not None]
  assert next(o for o in d['odds'] if o['name']=='BASE GOLD SAPPHIRE')['values'][scope]=='1:6'
  assert next(o for o in d['odds'] if o['name']=='ROOKIE GOLD SAPPHIRE')['values'][scope]=='1:17'
  assert next(o for o in d['odds'] if o['name']=='SAPPHIRE SELECTIONS AUTOGRAPHS')['family']=='SAPPHIRE SELECTION AUTOGRAPHS'
  assert not any('REFRACTOR' in o['name'] for o in d['odds'])
  assert hashlib.sha256(p.with_name(slug+'-odds.pdf').read_bytes()).hexdigest()==d['oddsSha256']
 elif slug==BOWMAN:
  assert len({(r[0],r[1]) for r in rows})==676
  assert [int(r[1]) for r in rows if r[0]=='BASE CARDS']==list(range(1,101))
  assert len([r for r in rows if r[0]=='HEXAGON AUTOGRAPHS'])==18
  assert collections.Counter(r[1] for r in rows if r[0]=='HEXAGON AUTOGRAPHS')=={'HEX-DL':6,'HEX-QB':6,'HEX-RB':6}
  assert len([r for r in rows if r[0]=='QUAD AUTOGRAPHS'])==56
  assert 'Rookie' not in d['headers'] and not d.get('odds')
  assert [r[2] for r in rows if r[1]=='HEX-DL'][-1]=='Tyrique Tucker','Preserve the checklist spelling'
  assert [v['text'] for v in d['unassignedPhysicalText']]==['®','®']
  examples=[s for s in d['publishedSpecifications'] if 'Card number' in s['headers']]
  assert [(s['name'],s['rows'][0][:4]) for s in examples]==[
   ('BASE CARDS',['16','LaNorris Sellers','Red Refractor','Limited to only five copies']),
   ('BEST OF 2026 AUTOGRAPHS',['BOA-KT','Kamario Taylor','Not named in guide','Autographed card limited to only 10 copies']),
   ('BEST OF MASCOTS',['BM-OSU','Brutus Buckeye™','Red','Limited to only five copies'])]
  for spec in examples:
   assert len(spec['rows'])==1
   assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
   assert 'serial marking is not stated' in spec['rows'][0][4]
  assert not any(s['family']!='BASE CARDS' for s in d['parallelSpecifications']),'Named examples must never create family-wide limits'
 elif slug==BASKETBALL:
  assert len({(r[0],r[1]) for r in rows})==3244
  assert [int(r[1]) for r in rows if r[0]=='BASE CARDS']==list(range(1,301))
  assert sum(r[4]=='Rookie' for r in rows if r[0]=='BASE CARDS')==45
  assert sum(r[4]=='Rookie' for r in rows)==1210
  assert len([r for r in rows if r[0]=='FANATICS AUTHENTIC REDEMPTION'])==60
  assert [r[1] for r in rows if r[0]=='FANATICS AUTHENTIC REDEMPTION']==['FR-'+str(n) for n in range(1,61)]
  for caption in ['GENERATION NOW','QUEST FOR THE CROWN','STARS OF NBA','LEVEL UP SIGNATURES','FRANCHISE FABRICS']:assert any(r[0]==caption for r in rows)
  assert next(r for r in rows if r[0]=='BASE CARDS' and r[1]=='17')[3]=='Miami Heat'
  assert next(r for r in rows if r[0]=='BASE CARDS' and r[1]=='242')[3]=='Milwaukee Bucks'
  assert not d.get('odds')
 else:
  artists=[r for r in rows if r[0]==ARTISTS];assert len(artists)==68 and all(not r[1] for r in artists)
  assert any(r[2]=='ジェイソン (Jason)' for r in artists) and any(r[2]=='DYJ' for r in artists)
  assert any(r[2]=='Alex Mines' for r in artists) and any(r[2]=='Mathilde Machuel' for r in artists)
  paper=[r for r in rows if r[0] in ['BRONZE BASE CARDS','SILVER BASE CARDS','GOLD BASE CARDS','PLATINUM BASE CARDS']]
  chrome=[r for r in rows if r[0].endswith('BASE CARDS - CHROME VARIATION')]
  assert [int(r[1]) for r in paper]==list(range(1,126)) and [int(r[1]) for r in chrome]==list(range(1,126))
  assert [r[2:5] for r in rows if r[1]=='CA-TH']==[['Tom Hanks','Woody','Toy Story 3']]
  assert [r[2:5] for r in rows if r[1]=='CA-JD']==[['Johnny Depp','Jack Sparrow','Pirates of the Caribbean: On Str']]
  assert [r[0:5] for r in rows if r[1]=='CS-CN']==[['CLARENCE NASH DONALD DUCK CUT SIGNATURE','CS-CN','Clarence Nash','Donald Duck','']]
  assert [r[3] for r in rows if r[1]=='MM-PL']==['Mickey & Friends']
  assert [r[2] for r in rows if r[1]=='64']==['22','22']
  assert 'Team' not in d['headers'] and 'Rookie' not in d['headers'] and not d.get('odds')
 print('Verified',slug,len(rows),'physical subject rows, original fields and exact source hashes.')
