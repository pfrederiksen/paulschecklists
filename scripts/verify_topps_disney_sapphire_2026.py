"""Compare all Disney Sapphire columns against independent original PDF objects."""
import collections
import hashlib
import json
import logging
import re
from pathlib import Path
from pypdf import PdfReader

logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-disney-sapphire-edition'
data=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']
assert data['dedicatedParser']=='scripts/import_topps_disney_sapphire_2026.py'
assert data['headers']==['Checklist section','Card number','Player / subjects','Source page','Character','Subject','Property','First Name','Last Name','Character Name','Team','Division','Official unlabelled annotation']
assert data['originalSubjectRows']==data['rows']
assert len(data['rows'])==394 and len({r[0] for r in data['rows']})==15
norm=lambda s:re.sub(r'\s+','',s)
families={r[0] for r in data['rows']};family='BASE CARDS';source=[]
reader=PdfReader(path);assert len(reader.pages)==9
for pn,page in enumerate(reader.pages,1):
    groups=collections.defaultdict(list)
    def visit(t,cm,tm,font,size):
        if t.strip():groups[round(tm[5],2)].append((tm[4],t))
    page.extract_text(visitor_text=visit)
    for y,chunks in sorted(groups.items(),reverse=True):
        line=' '.join(''.join(t for _,t in chunks).split())
        if not line:continue
        if line.startswith(('Checklists provided','product at the time')):continue
        if any(t.startswith('Card Number') for _,t in chunks):continue
        if line in families:family=line;continue
        def cell(a,b):return ' '.join(''.join(t for x,t in chunks if a<=x<b).split())
        char=subject=prop=first=last=character=team=division=annotation='';number=cell(0,600)
        if pn<=5 and family=='BASE CARDS':char=cell(600,1300);prop=cell(1300,2250);annotation=cell(2250,10000)
        elif family=='MICKEY AND FRIENDS MLB HOME JERSEY SET':subject=cell(600,1300);team=cell(1300,2000);division=cell(2000,10000)
        elif pn<=7:subject=cell(600,1500);prop=cell(1500,10000)
        else:first=cell(600,1050);last=cell(1050,1390);character=cell(1390,1860);prop=cell(1860,10000)
        name=' '.join(c for c in [first,last] if c) or char or subject
        source.append([family,number,name,str(pn),char,subject,prop,first,last,character,team,division,annotation])
assert [[norm(c) for c in r] for r in source]==[[norm(c) for c in r] for r in data['rows']],'Original PDF object origins must retain every field in its row and column'
assert len({tuple(r[:2]) for r in data['rows']})==336
base=[r for r in data['rows'] if r[0]=='BASE CARDS'];assert {int(r[1]) for r in base}==set(range(1,201))
assert sum(r[12]=='DEBUT' for r in base)==20 and not any(r[12] for r in data['rows'] if r[0]!='BASE CARDS')
assert 'Rookie' not in data['headers'] and all(not r[10] and not r[11] for r in data['rows'] if r[0]!='MICKEY AND FRIENDS MLB HOME JERSEY SET')
mlb=[r for r in data['rows'] if r[0]=='MICKEY AND FRIENDS MLB HOME JERSEY SET'];assert len(mlb)==30 and {r[1] for r in mlb}=={f'MLBH-{i}' for i in range(31,61)}
assert next(r for r in mlb if r[1]=='MLBH-31')[5:]==['Goofy','','','','','Los Angeles Dodgers®','NL West','']
assert next(r for r in data['rows'] if r[1]=='DCA-RS')[7:10]==['Raven-Symoné','','Raven Baxter']
assert next(r for r in data['rows'] if r[1]=='AA-SLJ')[7:10]==['Samuel L.','Jackson','Frozone']
assert all(not r[6] for r in data['rows'] if r[0]=='BEAUTY AND THE BEAST 35TH ANNIVERSARY' or 'FACSIMILE' in r[0])
assert len([r for r in data['rows'] if r[1]=='QD-RMCT'])==4
assert {r[6] for r in data['rows'] if r[1]=='QD-RMCT'}=={'The Princess and the Frog','Brave','Moana','Raya and the Last Dragon'}
assert len(data['odds'])==54 and data['formats']==['Sapphire']
assert data['formatNamesPublished'] is True and data['oddsUnitsPublished'] is False
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==data['oddsSha256']
source_odds=[]
for pn,page in enumerate(PdfReader(op).pages,1):
    for line in page.extract_text(extraction_mode='layout').splitlines():
        m=re.fullmatch(r'\s*(.+?)\s+([\d,.]+(?::[\d,.]+)+|-)\s*',line)
        if m:source_odds.append((pn,norm(m[1]),None if m[2]=='-' else m[2]))
assert source_odds==[(o['page'],norm(o['name']),o['values']['Sapphire']) for o in data['odds']]
assert next(o for o in data['odds'] if o['name']=='Base Card White Sapphire')['values']['Sapphire']=='01:14:00'
assert next(o for o in data['odds'] if o['name']=='Quad Facsimile Autographs Padparadscha Sapphire')['values']['Sapphire']=='1:26854'
assert len([o for o in data['odds'] if 'Padpradascha' in o['name']])==4
assert all(o['family'] in families for o in data['odds'])
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text());assert not registry['sets'].get(SLUG)
conflicts=[c for c in registry['conflicts'] if c['slug']==SLUG];assert conflicts
for spec in conflicts:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert record['releaseDate'] is None and record['releaseStatus']=='Unverified'
assert record['checklistUrl']==data['source'] and record['oddsUrl']==data['oddsSource']
print('Verified all 394 original-column subject rows / 336 identities, 200 base numbers, 20 DEBUT annotations, 30 jersey teams and 54 literal Sapphire ratios. Numbering and release-date gaps retained.')
