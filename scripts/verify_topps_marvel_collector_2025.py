"""Independently reconcile every Collector row, wrapped caption and odds cell."""
import collections,hashlib,json,logging,re,unicodedata
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-marvel-the-collector'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFC',s))
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_marvel_collector_2025.py'
assert d['rows']==d['originalSubjectRows']
headings={'INSERT','AUTOGRAPH','MCU PERFECTION','MARVEL TOMORROW','VILLAINY','SHOW STOPPERS','INFINITY GAUNTLET','DUAL AUTOGRAPHS','TREASURES OF','ASGARD','THE COLLECTORS','MUSEUM','VARIATION','SKETCH CARDS','MILLER','MAGNIFICENCE','MARVEL ARTHOUSE','MCU PERFECTION CHARACTER PROPERTY'}
for pn,page in enumerate(PdfReader(path).pages,1):
    actual=[]
    for line in page.extract_text(extraction_mode='layout').splitlines():
        line=' '.join(line.split())
        if not line or line in headings:continue
        if line=='Victorious':
            assert actual[-1]==norm('ST-8 Black Widow Emerges');actual[-1]+=norm(line)
        else:actual.append(norm(line))
    expected=[norm(r[1]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)]
    assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b][:3])
assert len(d['rows'])==296 and sum(bool(r[1]) for r in d['rows'])==262
assert len({tuple(r[:2]) for r in d['rows'] if r[1]})==257
assert collections.Counter(r[0] for r in d['rows'])=={'MCU PERFECTION':85,'MARVEL TOMORROW':25,'VILLAINY':25,'SHOW STOPPERS':25,'INFINITY GAUNTLET':6,'MCU PERFECTION AUTOGRAPH VARIATION':40,'DUAL AUTOGRAPHS':10,'TREASURES OF ASGARD':10,'INFINITY GAUNTLET AUTOGRAPH VARIATION':6,'THE COLLECTORS MUSEUM':30,'MILLER MAGNIFICENCE':1,'MARVEL ARTHOUSE':33}
assert {int(r[1]) for r in d['rows'] if r[0]=='MCU PERFECTION'}==set(range(1,86))
get=lambda n:next(r for r in d['rows'] if r[1]==n)
assert get('ST-8')[2]=='Black Widow Emerges Victorious'
assert get('MP-AO')[4:6]==['Aaron Taylor-Johnson','Pietro Maximoff']
assert get('TM-DT')[4:6]==['Dominique Thorne','Riri Williams'] and get('MP-DT')[5]=='Ironheart'
assert get('MT-2')[2]=='M’Baku' and get('1')[6:8]==['Mister Fantastic','The Fantastic Four: First Steps']
assert get('63')[7]=='Doctor Strange in the Multiverse of Madness'
assert sum(bool(r[7]) for r in d['rows'])==110
assert all(not r[7] for r in d['rows'] if r[0] not in {'MCU PERFECTION','MARVEL TOMORROW'})
assert [r[8] for r in d['rows'] if r[0]=='MILLER MAGNIFICENCE']==['Frank Miller']
assert [r[8] for r in d['rows'] if r[0]=='MARVEL ARTHOUSE'][-1]=='Vicente Moavero'
assert set(collections.Counter(r[1] for r in d['rows'] if r[0]=='DUAL AUTOGRAPHS').values())=={2}
assert 'Team' not in d['headers'] and 'Rookie' not in d['headers']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
original=[]
for pn,page in enumerate(PdfReader(op).pages,1):
    lines=page.extract_text(extraction_mode='layout').splitlines()
    assert any(norm(line)=='Card2025MarvelTheCollector' for line in lines)
    for line in lines:
        match=re.fullmatch(r'\s*(.+?)\s+(1:[\d,]+)\s*',line)
        if match:original.append((pn,' '.join(match[1].split()),match[2]))
assert original==[(o['page'],o['name'],o['values']['2025 Marvel The Collector']) for o in d['officialOddsTable']]
assert len(original)==59
assert d['formats']==['Published odds (format not named)'] and d['formatNamesPublished'] is False and d['oddsUnitsPublished'] is False and d['formatHeaderIsProductTitle'] is True
assert [v[2] for v in original]==[o['values'][d['formats'][0]] for o in d['odds']]
assert all(o['family'] in {r[0] for r in d['rows']} for o in d['odds'])
assert len([o for o in d['odds'] if o['family']=='THE COLLECTORS MUSEUM'])==6
assert not d.get('parallelSpecifications')
for spec in d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
record=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['year']=='2025' and record['releaseDate'] is None and record['coverageComplete'] is True
print('Verified 262 numbered subjects / 257 family-card identities, 34 artists, all 12 complete captions, wrapped ST-8, original text columns, five dual signers and every one of 59 literal odds. Product-title header is not a pack format; numbering, unit and release-date gaps remain explicit.')
