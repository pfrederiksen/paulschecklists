"""Verify every Mars Christmas row and the newly discovered physical odds source."""
import collections,hashlib,json,re,unicodedata
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-mars-attacks-christmas'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_mars_christmas_2026.py' and d['rows']==d['originalSubjectRows']
headings={norm(r[0]) for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH','RELIC','SKETCH'}
for pn,page in enumerate(PdfReader(path).pages,1):
    actual=[]
    for line in page.extract_text(extraction_mode='layout').splitlines():
        value=norm(line)
        if not value or value in headings:continue
        if pn==1 and value.startswith(('Checklistsprovided','atthetimeofproduction')):continue
        if pn==7 and value=='Gumbrell':assert actual[-1]==norm('Jordan "Slippa Chervascus"');actual[-1]+=value
        else:actual.append(value)
    expected=[norm(r[1]+r[2]) for r in d['rows'] if r[3]==str(pn)]
    assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b][:3])
assert len(d['rows'])==316 and sum(bool(r[1]) for r in d['rows'])==239
assert len({tuple(r[:2]) for r in d['rows'] if r[1]})==239
count=collections.Counter(r[0] for r in d['rows'])
assert len(count)==16 and count['BASE CARDS']==50 and count['BASE CARDS CHARACTERS A']==25 and count['BASE CARDS CHARACTERS B']==25 and count['SKETCH CARD ARTISTS']==77
assert {int(r[1]) for r in d['rows'] if r[0]=='BASE CARDS'}==set(range(1,51))
for prefix in ['A','B']:assert {r[1] for r in d['rows'] if r[0]=='BASE CARDS CHARACTERS '+prefix}=={prefix+'-'+str(n) for n in range(51,76)}
get=lambda code:next(r for r in d['rows'] if r[1]==code)
assert get('LC')[:3]==['LUMP OF COAL DIE CUT','LC','Lump of Coal']
assert get('CCA-GTA')[2]=='George Takei' and get('CCA-MRO')[2]=='Mark Rolston'
assert get('IWR-5')[2]==get('IWR-18')[2]=='Martian Suit'
assert get('PM-21')[2]=='Bezerka Bubble Gum' and get('MIC-13')[2]=='Jozz KRAK'
artists=[r[4] for r in d['rows'] if not r[1]]
assert artists[0]=='Aaron Laurich' and artists[-1]=='ジェイソン (Jason)' and 'Jordan "Slippa Chervascus" Gumbrell' in artists and 'Gumbrell' not in artists
assert 'Team' not in d['headers'] and 'Rookie' not in d['headers']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
expected=[]
with pdfplumber.open(op) as pdf:
    for pn,page in enumerate(pdf.pages,1):
        tables=page.find_tables();assert len(tables)==1
        for i,row in enumerate(tables[0].extract()):
            value=' '.join(' '.join(c or '' for c in row).split())
            if i==0:assert value=='Cards Hobby';continue
            matches=list(re.finditer(r'(?<!\S)(1:[0-9,]+|-)(?!\S)',value));assert len(matches)==1,(pn,value)
            match=matches[0];name=value[:match.start()]+value[match.end():]
            expected.append((pn,norm(name),None if match[1]=='-' else match[1]))
assert expected==[(o['page'],norm(o['name']),o['values']['Hobby']) for o in d['odds']]
assert len(expected)==70 and sum(v is None for p,n,v in expected)==5
assert d['formats']==['Hobby'] and d['formatNamesPublished'] is True and d['oddsUnitsPublished'] is False
assert all(o['family'] in count and not o.get('familyAliases') for o in d['odds'])
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text());specs=registry['sets'][SLUG]
assert {(s['oddsName'],s['numbering'],s['family']) for s in specs}=={('Base Cards Candy Cane Parallel','/299','BASE CARDS'),('Base Cards Snowcaps Parallel','/5','BASE CARDS')}
for s in specs:assert hashlib.sha256((ROOT/s['evidenceFile']).read_bytes()).hexdigest()==s['evidenceSha256']
assert not any(s['family'] in {'BASE CARDS CHARACTERS A','BASE CARDS CHARACTERS B','BATTLE READY','CRYPTIDS ALLIANCE','INVASION WORN RELIC CARDS'} for s in specs)
record=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['releaseDate'] is None and record['coverageComplete'] is True and record['oddsUrl']==d['oddsSource']
assert any(r['url']==d['oddsSource'] and r['discoverySource']==record['sourcePage'] for r in json.loads((ROOT/'data/entertainment-topps-odds.json').read_text()))
print('Verified 239 coded subjects, LC Lump of Coal, 77 artists with wrapped Gumbrell, all 16 sections and 70 physical Hobby categories (65 ratios, five nulls). Only two exact base limits are joined; extended-character and illustrated-example scopes stay qualified, with no inferred ratio units or release date.')
