"""Independently verify Museum's original text cells, centered codes and odds columns."""
import collections
import hashlib
import json
import re
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2025-26-topps-museum-uefa-club-competitions'
data=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
op=path.with_name(SLUG+'-odds.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']=='9501c7d842a2afbbc87483071a4bfe4350a7c38ece1857d364a93406356a7b2b'
assert hashlib.sha256(op.read_bytes()).hexdigest()==data['oddsSha256']=='c9fe6f6306c47b472cb7c1daf8d0e56aa9a2950677425e4cca3c0d4229f628b5'
assert data['originalSubjectRows']==data['rows']
assert len(data['rows'])==756 and len({tuple(r[:2]) for r in data['rows']})==686
assert sum(r[4]=='Rookie' for r in data['rows'])==102
families={r[0] for r in data['rows']};assert len(families)==35
multi={'ARCHIVAL DUAL AUTOGRAPHS':2,'HAT-TRICK TRIPLE AUTOGRAPHS':3,
       'SUPREME SCRIPT LEGENDARY AUTOGRAPHED BOOK':10,'SUPREME MATERIALS RELIC BOOK':10,
       'SUPREME SCRIPT LEGENDARY AUTOGRAPHED RELIC BOOK':10}
source=collections.defaultdict(list);codes=collections.defaultdict(list);family=None
for pn,page in enumerate(PdfReader(path).pages,1):
    groups=collections.defaultdict(list);anchor=[None]
    def visit(text,cm,tm,font,size):
        if text.strip():
            if tm[5]+cm[5]:anchor[0]=round(tm[5]+cm[5],2)
            assert anchor[0] is not None
            groups[anchor[0]].append(text.strip())
    page.extract_text(visitor_text=visit)
    for y,chunks in sorted(groups.items(),reverse=True):
        text=' '.join(chunks)
        if text in families:family=text;continue
        if text in {'BASE','INSERT','AUTOGRAPH','RELIC','AUTOGRAPH-RELIC'} or text.startswith(('Checklists provided','product at','EXCLUSIVE TO')):continue
        assert family,(pn,chunks)
        if family in multi:
            if len(chunks)==1 and re.fullmatch(r'[A-Z]+-[A-Z0-9]+',chunks[0]):
                codes[family].append(chunks[0]);continue
            assert len(chunks)==2,(pn,chunks)
            source[family].append([*chunks,'',str(pn)])
        else:
            assert len(chunks) in {3,4},(pn,chunks)
            number,name,team=chunks[:3];rookie=chunks[3] if len(chunks)==4 else ''
            assert rookie in {'','Rookie'}
            source[family].append([number,name,team,rookie,str(pn)])
norm=lambda value:re.sub(r'\s+','',value)
for family in families:
    actual=[r[1:] for r in data['rows'] if r[0]==family]
    if family in multi:
        actual_cells=[r[1:] for r in actual]
        printed=list(dict.fromkeys(codes[family]))
        expected_numbers=[n for n in printed for _ in range(multi[family])]
        assert [r[0] for r in actual]==expected_numbers,(family,'centered codes')
        assert len(printed)==len(actual)//multi[family]
    else:actual_cells=actual
    assert [[norm(c) for c in r] for r in actual_cells]==[[norm(c) for c in r] for r in source[family]],family
assert [r[1] for r in data['rows'] if r[0]=='BASE CARDS']==list(map(str,range(1,101)))
assert [r[2] for r in data['rows'] if r[1]=='HTA-AGC']==['Xabi Alonso','Steven Gerrard','Jamie Carragher']
assert [r[5] for r in data['rows'] if r[1]=='HTA-AGC']==['7','7','8']
assert data['rows'][-1]==['SUPREME SCRIPT LEGENDARY AUTOGRAPHED RELIC BOOK','SSAR-BC','Lionel Messi','FC Barcelona','','17']
# Independent PDF text flow retains both right-hand physical values for every row.
physical=[]
for pn,page in enumerate(PdfReader(op).pages,1):
    text=page.extract_text()
    for line in text.splitlines():
        m=re.fullmatch(r'(.+?)\s+([\d,:]+|-)\s+([\d,:]+|-)',line.strip())
        if m:
            name,hobby,hat=m.groups()
            physical.append({'name':name,'values':{'Hobby':None if hobby=='-' else hobby,'Hat-Trick':None if hat=='-' else hat},'page':pn})
assert len(physical)==147,len(physical)
assert physical==data['officialOddsTable']
assert [{k:o[k] for k in ['name','values','page']} for o in data['odds']]==physical
assert data['formats']==['Hobby','Hat-Trick'] and data['oddsUnitsPublished'] is False
assert data['odds'][0]['values']=={'Hobby':'4:1','Hat-Trick':None}
assert all(o['family'] in families for o in data['odds'])
proof_path=ROOT/data['sourceObservation']['file']
assert hashlib.sha256(proof_path.read_bytes()).hexdigest()==data['sourceObservation']['sha256']
proof=json.loads(proof_path.read_text());specs=data['publishedSpecifications']
assert len(specs)==4 and not data['parallelSpecifications']
assert [s['rows'][0][0] for s in specs[:3]]==['MRA-MD','ROH-1','MMJA-MO']
assert specs[1]['rows'][0][3]=='Limited to 25 copies'
assert 'serial marking are unstated' in specs[1]['rows'][0][4]
assert not json.loads((ROOT/'data/parallel-specifications.json').read_text())['sets'][SLUG]
record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert record['releaseDate'] is None and record['releaseStatus']=='Unverified'
print('Verified all 756 Museum physical subjects, 686 identities, 35 families, 102 Rookie flags, centered multi-signer/book codes and all 147 literal two-column odds; guide examples remain card-specific.')
