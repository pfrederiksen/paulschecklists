"""Verify all original Venezuela championship rosters and conservative limit scope."""
import hashlib
import json
from pathlib import Path
import import_official_catalog as generic
from import_topps_now_venezuela_champions_2026 import SLUG,TITLE,PAGE,EVIDENCE,BASE,PARALLEL,IMAGE,AUTO,FAMILIES,CONFIG,FOILS

root=Path(__file__).resolve().parents[1];proof=json.loads((root/EVIDENCE).read_text());ph=hashlib.sha256((root/EVIDENCE).read_bytes()).hexdigest()
data=json.loads((root/'data/imports'/(SLUG+'.json')).read_text())
assert data['source']==PAGE and data['sha256']==ph and data['sourceProducts'][0]['sha256']==ph
assert data['headers']==['Checklist section','Card number','Player / subjects','Published subject','Official source']
assert len(data['rows'])==27 and all(len(r)==5 and r[1]=='' and r[2]==r[3] and r[4]==PAGE for r in data['rows'])
expected={BASE:['Ronald Acuña Jr.','Luis Arraez','William Contreras','Jackson Chourio','Salvador Perez','Eugenio Suárez','Willson Contreras','Wilyer Abreu','Gleyber Torres','Maikel Garcia','Miguel Cabrera','Ezequiel Tovar','Eduardo Rodriguez','Daniel Palencia','Team Venezuela'],PARALLEL:['Ronald Acuña Jr.','Luis Arraez','Eugenio Suárez','Maikel Garcia'],IMAGE:['Ronald Acuña Jr.','Luis Arraez','Jackson Chourio','Eugenio Suárez'],AUTO:['Ronald Acuña Jr.','Luis Arraez','Jackson Chourio','Wilyer Abreu']}
for family,names in expected.items():assert [r[2] for r in data['rows'] if r[0]==family]==names
lines=[s.strip() for s in proof['description'].splitlines() if s.strip()]
assert lines==[s.strip() for s in proof['descriptionParagraphs'] if s.strip()]
assert lines[1:-1]==[cell for family,names in expected.items() for cell in [family,*names]]
assert not data.get('odds') and not data.get('formats') and not data.get('serialColumn')
assert not any('team' in h.lower() or 'rookie' in h.lower() for h in data['headers']) and proof['documentLinks']==[] and proof['title']==TITLE
terms=next(s for s in data['publishedSpecifications'] if s['name']=='Unjoined product foil numbering')
assert [r[:2] for r in terms['rows']]==[[name,n] for name,n in FOILS]+[['Image Variation Short print','Not stated']]
assert terms['name'] not in FAMILIES and json.loads((root/'data/parallel-specifications.json').read_text())['sets'][SLUG]==[]
assert all('subject/color' in r[2] for r in terms['rows'][:6])
for family in FAMILIES:
 table=next(s for s in data['publishedSpecifications'] if s['name']==family);assert table['rows'][0][0]==str(len(expected[family]))+' separately published subjects'
 assert not any('/99' in cell or '/1' in cell for r in table['rows'] for cell in r)
fields={r[0]:r[1] for r in next(s for s in data['publishedSpecifications'] if s['name'].startswith('Set-wide'))['rows']}
assert fields['Published bundle contents']==CONFIG and fields['Published bundle print run']=='1084'
assert fields['Available From']=='Mar 18, 2026' and fields['Available Until']=='Mar 25, 2026'
assert fields['Product Year']=='2026' and fields['Printed card numbers']==fields['Team assignments / rookie flags']=='Not published'
record=next(s for s in json.loads((root/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['releaseDate'] is None and record['releaseStatus']=='Unverified' and record['coverageComplete'] is False
assert generic.run(record.copy())==record
assert not any(p['source']==PAGE for p in json.loads((root/'data/topps-now-observations.json').read_text()))
assert not json.loads((root/'data/topps-now-archive-index.json').read_text())['coverageComplete']
print('Verified all 27 literal Venezuela championship entries and four exact rosters, blank IDs, six unjoined foil limits, unstated SP numbering, bundle-only PR1084 and separate sale dates; no team/rookie/autograph limits inferred.')
