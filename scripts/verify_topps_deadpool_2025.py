"""Independently verify original Deadpool subjects, every odds cell and guide scope."""
import collections,hashlib,json,logging,re,unicodedata
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-chrome-deadpool'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_deadpool_2025.py' and d['rows']==d['originalSubjectRows']
headings={r[0] for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH','SKETCH'}
for pn,page in enumerate(PdfReader(path).pages,1):
    actual=[]
    for line in page.extract_text(extraction_mode='layout').splitlines():
        line=' '.join(line.split())
        if not line or line in headings or line.startswith('Checklists provided'):continue
        actual.append(norm(line))
    expected=[norm(r[1]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)]
    # Two first-page number/name baselines differ in the layout renderer;
    # the complete original glyph stream must still match without loss.
    assert ''.join(actual)==''.join(expected),pn
    if pn>1:assert actual==expected,pn
assert len(d['rows'])==462 and sum(bool(r[1]) for r in d['rows'])==314
assert len({tuple(r[:2]) for r in d['rows'] if r[1]})==304
count=collections.Counter(r[0] for r in d['rows'])
assert len(count)==24 and count['COMIC ACCURATE']==20 and count['CHARACTERS']==26 and count['MULTIVERSE AND MORE']==54
assert count['DEADPOOL SKETCH CARDS']==146 and count['MARVEL COMIC BOOK ARTIST SKETCH CARDS']==2
assert {int(r[1]) for r in d['rows'] if r[0] in {'COMIC ACCURATE','CHARACTERS','MULTIVERSE AND MORE'}}==set(range(1,101))
assert 'NC-7' not in {r[1] for r in d['rows']} and 'FO-8' not in {r[1] for r in d['rows']}
assert [r[2] for r in d['rows'] if r[1]=='TH-TA']==['Aaron Stanford','Tyler Mane']
assert [r[5] for r in d['rows'] if r[1]=='TH-TA']==['Pyro','Sabretooth']
assert [r[2] for r in d['rows'] if r[1]=='TC-D']==['Peggy the Dog']
artists=[r[6] for r in d['rows'] if not r[1]]
assert all(a in artists for a in ['IQ','John-Paul Howard','Mike McKone','Whilce Portacio','ジェイソン (Jason)'])
assert artists[-1]=='ジェイソン (Jason)' and not any(r[1] in {'10005','John-Paul'} for r in d['rows'])
assert 'Team' not in d['headers'] and 'Rookie' not in d['headers']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
expected=[];formats=['HOBBY','VALUE SE','VALUE BOX EA','VALUE BOX CEE']
with pdfplumber.open(op) as pdf:
    for pn,page in enumerate(pdf.pages,1):
        for table in page.find_tables():
            for row in table.extract():
                cells=[' '.join((c or '').split()) for c in row]
                if not any(cells) or cells[0]=='SUBJECT TO CHANGE':continue
                if cells[0]=='CARDS':assert cells[1:]==formats;continue
                assert len(cells)==5 and all(c=='-' or re.fullmatch('1:[0-9,]+',c) for c in cells[1:]),(pn,cells)
                expected.append((pn,norm(cells[0]),[None if c=='-' else c for c in cells[1:]]))
assert expected==[(o['page'],norm(o['name']),list(o['values'].values())) for o in d['odds']]
assert len(expected)==161 and d['formats']==formats and d['formatNamesPublished'] is True and d['oddsUnitsPublished'] is False
assert all(o['family'] in count for o in d['odds'])
assert all(o['familyAliases']==['CHARACTERS','MULTIVERSE AND MORE'] for o in d['odds'] if o['name'].startswith('Base Cards'))
odd=lambda n:next(o for o in d['odds'] if o['name']==n)
assert odd('Marvel Comic Book Ar^st Autographs Refractor Parallel')['values']==dict(zip(formats,['1:201','1:5,612','1:5,612','1:5,613']))
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text());specs=registry['sets'][SLUG]
assert len(specs)==60 and sum('oddsName' in s for s in specs)==59
assert all(s['family'] in count for s in specs)
for s in specs:
    assert hashlib.sha256((ROOT/s['evidenceFile']).read_bytes()).hexdigest()==s['evidenceSha256']
    if s.get('oddsName'):assert odd(s['oddsName'])['family']==s['family']
assert next(s for s in specs if s['name']=='TBC Parallel')['numbering']=='1/1'
assert not any(s.get('oddsName')=='Deadpool Reﬂec^ons Superfractor' for s in specs)
assert not any(s['family'] in {'TOPPS CHROME DUAL AUTOGRAPHS','COVER STARS','DEADPOOL AUTOGRAPHS','DEADPOOL SKETCH CARDS'} for s in specs)
record=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['year']=='2025' and record['releaseDate'] is None and record['coverageComplete'] is True
print('Verified 314 numbered subjects / 304 identities, 148 artists, all 24 sections and 644 physical odds cells. Exact guide scopes retain 59 joined limits and distinct TBC 1/1; checklist discrepancies, unspecified units and release date remain explicit.')
