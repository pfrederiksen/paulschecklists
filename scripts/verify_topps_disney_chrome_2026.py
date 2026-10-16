"""Independently reconcile every original glyph, artist, card ID and odds cell."""
import collections,hashlib,json,logging,re,unicodedata
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-disney'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_disney_chrome_2026.py' and d['rows']==d['originalSubjectRows']
headings={norm(r[0]) for r in d['rows']}
for pn,page in enumerate(PdfReader(path).pages,1):
    original=[];ids=[]
    for line in page.extract_text(extraction_mode='layout').splitlines():
        value=norm(line)
        if not value or value in headings or value.startswith(('CardNumber','ArtistName')):continue
        if pn==1 and ('Checklistsprovided' in value or 'productatthetime' in value):continue
        original.append(value)
        # Ignore extraction's spurious spaces within code cells. Restrict the
        # independent ID check to the first physical text column.
        first=re.split(r'\s{3,}',line.strip())[0]
        if pn not in {14,15,16} and re.fullmatch(r'\d+|[A-Z0-9&]+\s*-\s*[A-Z0-9]+',first):ids.append(norm(first))
    rows=[r for r in d['rows'] if r[3]==str(pn)]
    expected=[]
    for r in rows:
        values=[r[1],r[4],r[6],r[10]] if pn<=5 else [r[1],r[5],r[6]] if pn<=12 else [r[1],r[5],r[11],r[12]] if pn==13 else [r[13]] if pn<=16 else [r[1],r[7],r[8],r[9],r[6]]
        expected.append(norm(''.join(values)))
    assert collections.Counter(''.join(original))==collections.Counter(''.join(expected)),(pn,collections.Counter(''.join(original))-collections.Counter(''.join(expected)),collections.Counter(''.join(expected))-collections.Counter(''.join(original)))
    if 14<=pn<=16:assert original==expected,(pn,original,expected)
    else:
        # A few source text objects insert spaces inside a code. All normally
        # rendered IDs must appear once, including repeated signer identities.
        assert not collections.Counter(ids)-collections.Counter(r[1] for r in rows),(pn,ids)
assert len(d['rows'])==741 and sum(bool(r[1]) for r in d['rows'])==640
assert len({tuple(r[:2]) for r in d['rows'] if r[1]})==582
count=collections.Counter(r[0] for r in d['rows']);assert len(count)==42
assert count['BASE CARDS']==200 and {int(r[1]) for r in d['rows'] if r[0]=='BASE CARDS'}==set(range(1,201))
assert count['SKETCH CARDS']==90 and count['DISNEY & PIXAR STUDIO ARTIST SKETCH CARDS']==11
assert {r[1] for r in d['rows'] if r[0]=='DISNEY INK AND PAINT'}=={'I&P-'+str(n) for n in range(1,11)}
find=lambda number:next(r for r in d['rows'] if r[1]==number)
assert find('IM-9')[5:7]==["The Poison. The Poison for Kuzco. The Poison Chosen Specially to Kill Kuzco. Kuzco's Poison.","The Emperor's New Groove"]
assert find('14')[6]=='Pirates of the Caribbean: On Stranger Tides'
assert find('HX-3')[6]=='The Many Adventures of Winnie the Pooh'
assert find('I&P-7')[6]=='The Adventures of Ichabod and Mr. Toad'
assert find('DCA-VH')[7:10]==['Vanessa','Hudgens','Gabriella Montez']
assert find('AA-JV')[7:10]==['Jacques','Villeneuve','Jacques Villeneuve']
assert find('DCA-RS')[7:10]==['Raven-Symoné','','Raven Baxter']
assert [r[2] for r in d['rows'] if r[1]=='TR-BLS']==['Matthew Broderick','Nathan Lane','Ernie Sabella']
assert [r[9] for r in d['rows'] if r[1]=='QD-RMCT']==['Tiana','Merida','Moana','Raya']
assert find('AA-JC')[6]=='Mickey & Friends' and find('AA-JCM')[6]=='Mickey & Friends'
assert find('MLBH-31')[11:13]==['Los Angeles Dodgers®','NL West']
assert {r[1] for r in d['rows'] if r[0]=='MICKEY AND FRIENDS MLB HOME JERSEY SET'}=={'MLBH-'+str(n) for n in range(31,61)}
assert sum(r[10]=='DEBUT' for r in d['rows'])==20 and not any(h in {'Team','Rookie'} for h in d['headers'])
assert any(r[13]=='Jean-Christophe Poulain' and not r[1] for r in d['rows'])
assert any(r[13]=='ジェイソン (Jason)' for r in d['rows']) and any(r[13]=='Niño John Benitez' for r in d['rows'])
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
expected=[];formats=d['formats']
with pdfplumber.open(op) as pdf:
    for pn,page in enumerate(pdf.pages,1):
        tables=page.find_tables();assert len(tables)==1
        for i,row in enumerate(tables[0].extract()):
            cells=[' '.join((c or '').split()) for c in row]
            if i==0:assert cells==['Cards '+' '.join(formats)];continue
            assert len(cells)==1
            cells=cells[0].rsplit(' ',7)
            assert len(cells)==8 and cells[0] and all(c=='-' or re.fullmatch(r'1:[0-9,]+',c) for c in cells[1:])
            expected.append((pn,norm(cells[0]),[None if c in {'','-'} else c for c in cells[1:]]))
assert expected==[(o['page'],norm(o['name']),list(o['values'].values())) for o in d['odds']]
assert len(expected)==210 and len(formats)==7 and d['oddsUnitsPublished'] is False
assert all(o['family'] in count for o in d['odds'])
assert next(o for o in d['odds'] if o['name']=='Base')['family']=='BASE CARDS'
assert next(o for o in d['odds'] if o['name']=='Disney Ink and Paint')['family']=='DISNEY INK AND PAINT'
assert d['parallelSpecifications']==[] and not any(o.get('numbering') for o in d['odds'])
for table in d['publishedSpecifications']:assert hashlib.sha256((ROOT/table['evidenceFile']).read_bytes()).hexdigest()==table['evidenceSha256']
record=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['releaseDate']=='2026-06-17' and record['coverageComplete'] is True
print('Verified every physical source glyph, 640 numbered subjects / 582 identities, 101 artists, 42 sections, all 210 odds/seven columns, restored wrapped captions and signer IDs. Twenty DEBUTs remain source annotations; guide examples do not propagate numbering.')
