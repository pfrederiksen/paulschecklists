"""Independently compare every Star Wars Chrome glyph row and physical odds cell."""
import collections,hashlib,json,re,unicodedata
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-star-wars-chrome'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());p=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256'] and d['rows']==d['originalSubjectRows']
headings={norm(r[0]) for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH','AUTOGRAPHS'}
for pn,page in enumerate(PdfReader(p).pages,1):
    actual=[]
    for line in page.extract_text(extraction_mode='layout').splitlines():
        value=norm(line)
        if not value or value in headings or value.startswith(('Checklistsprovided','production,butactual','butactualcontents')):continue
        actual.append(value)
    expected=[norm(r[1]+''.join(r[4:7])) for r in d['rows'] if r[3]==str(pn)]
    assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b][:3])
assert len(d['rows'])==1502 and sum(bool(r[1]) for r in d['rows'])==1369
count=collections.Counter(r[0] for r in d['rows']);assert len(count)==29 and count['SKETCH ARTISTS']==133
for family,prefix in [('CHARACTERS',''),('CHARACTERS HOTHFRACTOR','HOTH-'),('CHARACTERS AUREBESH','AURE-'),('BASE PRINTING PLATE BOOK CARDS I','PLATE-')]:assert {r[1] for r in d['rows'] if r[0]==family}==({prefix+str(n) for n in range(1,201)}-({'PLATE-194'} if prefix=='PLATE-' else set()))|({'PALTE-194'} if prefix=='PLATE-' else set())
get=lambda f,n:next(r for r in d['rows'] if r[:2]==[f,n])
assert get('GALATIC MAXIMALISTS','GMAX-CHEWIE')[2]=='Chewbacca'
assert get('CHARACTERS AUTOGRAPHS','156')[4:7]==['Stephen McKinley Henderson','Gatori','DEBUT']
assert get('CHARACTERS AUTOGRAPHS','114')[4:6]==['Bronte Carmichael','Bronte Carmichael']
assert get('CHARACTERS','2')[4:7]==['Lezine','DEBUT','']
assert count['DUO AUTOGRAPHS']==44 and count['TRIPLE AUTOGRAPHS']==57
assert set(collections.Counter(r[1] for r in d['rows'] if r[0]=='DUO AUTOGRAPHS').values())=={2}
assert set(collections.Counter(r[1] for r in d['rows'] if r[0]=='TRIPLE AUTOGRAPHS').values())=={3}
assert d['rows'][-1][7]=='R. Goto' and d['rows'][-133][7]=='Aaron Laurich'
assert 'Team' not in d['headers'] and 'Rookie' not in d['headers']
op=p.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
expected=[];blank=[]
with pdfplumber.open(op) as pdf:
    for pn,page in enumerate(pdf.pages,1):
        for i,row in enumerate(page.find_tables()[0].extract()):
            cells=[' '.join((c or '').split()) for c in row]
            if i==0:assert cells==['Card',*d['formats']];continue
            if not cells[0]:assert all(v in {'','-'} for v in cells[1:]);blank.append([str(pn),*cells]);continue
            expected.append((pn,norm(cells[0]),[None if v in {'','-'} else v for v in cells[1:]]))
assert expected==[(o['page'],norm(o['name']),list(o['values'].values())) for o in d['odds']]
assert len(expected)==186 and len(blank)==11 and blank==d['oddsSourceNotes']
assert d['formats']==['HOBBY','DELIGHT','SAPPHIRE','VALUE BOX','CLUB SUPER BOX'] and d['oddsUnitsPublished'] is False
assert next(o for o in d['odds'] if o['name']=='CHARACTERS RAINBOW REFRACTOR')['values']['DELIGHT']=='3:1'
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text());specs=registry['sets'][SLUG]
assert len(specs)==1 and specs[0]['family']=='BASE PRINTING PLATE BOOK CARDS I' and specs[0]['numbering']=='1/1' and specs[0]['oddsName']=='PRINTING PLATE BOOK CARD'
assert hashlib.sha256((ROOT/specs[0]['evidenceFile']).read_bytes()).hexdigest()==specs[0]['evidenceSha256']
print('Verified all 1,369 coded subjects, 133 artists, four distinct 200-card programs, 22 duals / 19 triples, overlapping actor/character cells, literal DEBUT marks and all 930 physical odds values. Only the named Printing Plate Book program receives 1/1; other audits remain explicit.')
