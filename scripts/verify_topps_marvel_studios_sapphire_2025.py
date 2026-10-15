"""Independently compare the complete MCU Sapphire glyphs and physical columns."""
import collections,hashlib,json,re,unicodedata
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-marvel-studios-chrome-sapphire'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFC',s))
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_marvel_studios_sapphire_2025.py'
assert d['rows']==d['originalSubjectRows'] and d['headers']==d['originalSubjectHeaders']
families={r[0] for r in d['rows']}
for pn,page in enumerate(PdfReader(path).pages,1):
    actual=[]
    for line in page.extract_text(extraction_mode='layout').splitlines():
        line=' '.join(line.split())
        if not line or line.startswith(('Card Number','Artist Name')) or line in families:continue
        actual.append(norm(line))
    expected=[]
    for row in d['rows']:
        if row[3]!=str(pn):continue
        indices=[1,4,5,7,8,9] if row[0]=='BASE' else [1,6,7] if row[0]=='SAPPHIRE SELECTIONS' else [13] if row[0]=='SKETCH CARDS' else [1,10,11,12,7,9]
        expected.append(norm(''.join(row[i] for i in indices)))
    assert actual==expected,(pn,'Every independent printed row must be retained',[(a,b) for a,b in zip(actual,expected) if a!=b][:3])
assert collections.Counter(r[0] for r in d['rows'])=={'BASE':200,'SAPPHIRE SELECTIONS':10,'SKETCH CARDS':118,'SINGLE AUTOGRAPHS':63,'DUAL AUTOGRAPHS':40,'TRIO AUTOGRAPHS':21}
assert len({tuple(r[:2]) for r in d['rows'] if r[1]})==300
assert {int(r[1]) for r in d['rows'] if r[0]=='BASE'}==set(range(1,201))
assert sum(r[9]=='DEBUT' for r in d['rows'])==36 and 'Rookie' not in d['headers'] and 'Team' not in d['headers']
assert sum(bool(r[5]) for r in d['rows'])==53
assert all(r[4] and r[7] and re.fullmatch(r'Phase (One|Two|Three|Four|Five|Six)',r[8]) for r in d['rows'] if r[0]=='BASE')
assert all(r[10] and r[11] and r[12] and r[7] for r in d['rows'] if r[0].endswith('AUTOGRAPHS'))
get=lambda family,number:next(r for r in d['rows'] if r[:2]==[family,number])
assert get('BASE','110')[7:9]==['Shang-Chi and the Legend of the Ten Rings','Phase Four']
assert get('BASE','131')[7]=='Doctor Strange in the Multiverse of'
assert get('BASE','161')[4:10]==['Death','Rio Vidal','','Agatha All Along','Phase Five','DEBUT']
assert get('SINGLE AUTOGRAPHS','AA-EO')[9:13]==['DEBUT','Elizabeth','Olsen','The Scarlet Witch']
assert get('TRIO AUTOGRAPHS','TA-OTB')[12]=='Wanda Maxmioff'
artists=[r[13] for r in d['rows'] if r[0]=='SKETCH CARDS']
assert artists[0]=='A jhay' and artists[-1]=='ジェイソン (Jason)' and 'Niño John Benitez' in artists
for family,multiplicity in [('DUAL AUTOGRAPHS',2),('TRIO AUTOGRAPHS',3)]:
    assert set(collections.Counter(r[1] for r in d['rows'] if r[0]==family).values())=={multiplicity}
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
with pdfplumber.open(op) as pdf:
    original=[]
    for pn,page in enumerate(pdf.pages,1):
        table=page.find_tables()[0].extract();assert table[0]==['Cards','Sapphire Pack Rate']
        original.extend((pn,' '.join(row[0].split()),row[1]) for row in table[1:])
assert original==[(o['page'],o['name'],o['values']['Sapphire Pack Rate']) for o in d['odds']]
assert len(original)==28 and d['formats']==['Sapphire Pack Rate'] and d['oddsUnitsPublished'] is True
assert collections.Counter(o['family'] for o in d['odds'])=={'BASE':8,'SINGLE AUTOGRAPHS':5,'DUAL AUTOGRAPHS':3,'TRIO AUTOGRAPHS':3,'SAPPHIRE SELECTIONS':7,'SKETCH CARDS':2}
assert not d.get('parallelSpecifications'),'Unscoped product-level 1/1 must not number every family'
for spec in d['publishedSpecifications']:
    assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
record=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['year']=='2025' and record['releaseDate'] is None and record['coverageComplete'] is True
print('Verified all 334 numbered rows / 300 family-card identities, 118 sketch artists, 53 aliases, 36 DEBUT fields, all original physical columns and 28 complete Sapphire Pack Rate ratios. Unscoped numbering and release-date gaps remain explicit.')
