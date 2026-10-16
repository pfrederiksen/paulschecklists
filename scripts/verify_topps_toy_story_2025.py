"""Independently verify every Toy Story row, repeated identity and physical odds cell."""
import collections,hashlib,json,logging,re,unicodedata
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-30-years-of-toy-story'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_toy_story_2025.py' and d['rows']==d['originalSubjectRows']
headings={norm(r[0]) for r in d['rows']}
for pn,page in enumerate(PdfReader(path).pages,1):
    actual=[]
    for line in page.extract_text(extraction_mode='layout').splitlines():
        value=norm(line)
        if not value or value in headings or value.startswith(('CardNumber','ArtistName')):continue
        if pn==1 and value.startswith(('Checklistsprovided','theintended','productatthetime','BASEactualcontents')):continue
        actual.append(value)
    expected=[norm(r[1]+(r[6]+r[7]+r[4] if r[6] else r[4]+r[5] if r[1] else r[8])) for r in d['rows'] if r[3]==str(pn)]
    assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b][:3])
assert len(d['rows'])==511 and sum(bool(r[1]) for r in d['rows'])==425
assert len({tuple(r[:2]) for r in d['rows'] if r[1]})==395
count=collections.Counter(r[0] for r in d['rows'])
assert len(count)==24 and count['BASE']==100 and count['30 YEARS AND BEYOND']==35
assert count['TOY STORY SKETCH CARDS']==76 and count['STUDIO CREATIONS SKETCH CARD']==8 and count['EXECUTIVE STUDIO CREATIONS SKETCH CARD']==2
assert {int(r[1]) for r in d['rows'] if r[0]=='BASE'}==set(range(1,101))
assert count['IMAGE VARIATIONS']==17 and sum(r[1]=='25' and r[0]=='IMAGE VARIATIONS' for r in d['rows'])==3
assert next(r for r in d['rows'] if r[1]=='88' and r[0]=='IMAGE VARIATIONS')[4:6]==['Tinny','Toy Story 2']
assert sum(bool(r[5]) for r in d['rows'])==225
assert sum(bool(r[6]) for r in d['rows'])==65
assert [r[2] for r in d['rows'] if r[1]=='YRT-TA']==['Tim Allen']
assert next(r for r in d['rows'] if r[1]=='YRT-EVD')[6:8]==['Erik','von Detten']
assert [r[2] for r in d['rows'] if r[1]=='YGF-HA']==['Tom Hanks','Tim Allen']
assert [r[4] for r in d['rows'] if r[1]=='YGF-HA']==['Woody','Buzz Lightyear']
assert [r[8] for r in d['rows'] if r[0]=='EXECUTIVE STUDIO CREATIONS SKETCH CARD']==['Andrew Stanton','Bob Peterson']
assert d['rows'][-1][8]=='ジェイソン (Jason)' and any(r[8]=='Niño John Benitez' for r in d['rows'])
assert all(r[1].startswith('30Y-') for r in d['rows'] if r[0]=='30 YEARS AND BEYOND') and not any(r[1]=='Yung-Han' for r in d['rows'])
assert 'Team' not in d['headers'] and 'Rookie' not in d['headers']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
expected=[]
with pdfplumber.open(op) as pdf:
    for pn,page in enumerate(pdf.pages,1):
        tables=page.find_tables();assert len(tables)==1
        for i,row in enumerate(tables[0].extract()):
            cells=[' '.join((c or '').split()) for c in row]
            if i==0:assert cells==['','Hobby'];continue
            assert len(cells)==2 and re.fullmatch('1:[0-9,]+',cells[1]),(pn,cells)
            expected.append((pn,norm(cells[0]),cells[1]))
assert expected==[(o['page'],norm(o['name']),o['values']['Hobby']) for o in d['odds']]
assert len(expected)==104 and d['formats']==['Hobby'] and d['formatNamesPublished'] is True and d['oddsUnitsPublished'] is False
assert all(o['family'] in count for o in d['odds'])
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text());specs=registry['sets'][SLUG]
assert len(specs)==47 and sum('oddsName' in s for s in specs)==42
assert all(s['family'] in count for s in specs)
for s in specs:
    assert hashlib.sha256((ROOT/s['evidenceFile']).read_bytes()).hexdigest()==s['evidenceSha256']
    if s.get('oddsName'):assert next(o for o in d['odds'] if o['name']==s['oddsName'])['family']==s['family']
assert collections.Counter(s['family'] for s in specs if not s.get('oddsName'))=={'SID HAS YOUR CARDS':3,"YOU'VE GOT A FRIEND IN ME DUAL AUTOGRAPH":2}
assert not any(s['family'] in {'IMAGE VARIATIONS','30 YEARS AND BEYOND','FALLING WITH STYLE','GOLDEN TOYS SHADOWBOX AUTOGRAPH','TOY STORY SKETCH CARDS'} for s in specs)
record=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['year']=='2025' and record['releaseDate'] is None and record['coverageComplete'] is True
print('Verified 425 numbered subjects / 395 identities, 86 artists, all 24 sections and 104 physical Hobby odds cells. Guide scopes retain 42 joined limits and five specification-only parallels; source spelling/property differences, unnamed units and release-date gaps remain explicit.')
