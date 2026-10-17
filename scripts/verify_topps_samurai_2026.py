"""Check recovered SP rows, original column fidelity and exact odds-family scope."""
import collections, hashlib, json
from pathlib import Path
import pdfplumber

root = Path(__file__).resolve().parents[1]
slug = 'topps-bowman-2026-topps-chrome-baseball-team-samurai-japan-collection'
data = json.loads((root / f'data/imports/{slug}.json').read_text())
rows = data['rows']
assert len(rows) == 124 and len({r[1] for r in rows}) == 124
assert collections.Counter(r[0] for r in rows) == {
    'Base Cards': 74, 'Base Card Short Prints': 6,
    'Sensational Samurai Insert': 10, 'Generational Greats Insert': 5,
    'Neon Nights Insert': 10, 'Samurai Spirit Insert': 5,
    'Base Card Autograph Parallel': 13, 'Generational Great Dual Autograph Parallel': 1,
}
by_number = {r[1]: r for r in rows}
assert by_number['75SP'][2:] == ['Shohei Ohtani', 'Samurai Japan', 'P/DH', '3']
assert by_number['79SP'][2:] == ['Sadaharu Oh', 'Samurai Japan', 'Mgr.', '3']
assert by_number['80SP'][2:] == ['Shohei Ohtani', 'Samurai Japan', 'P/DH', '3']
assert by_number['36'][2:] == ['Ukyo Shuto', 'Samurai Japan', 'OF', '2']
assert by_number['SAM-3'][0] == 'Samurai Spirit Insert'
assert by_number['GG-1A'][2:] == ['Shohei Ohtani / Sadaharu Oh', 'Samurai Japan', '', '4']
assert all(r[4] == '' for r in rows if r[0].startswith(('Generational', 'Samurai Spirit')))
assert 'Rookie' not in data['headers']
# Compare every complete imported record to its literal printed line. This also
# detects clipped names, misplaced team/position cells and lost dual subjects.
with pdfplumber.open(root / f'data/catalog-sources/downloads/{slug}.pdf') as pdf:
    texts = [page.extract_text().splitlines() for page in pdf.pages]
    for row in rows:
        assert ' '.join(v for v in row[1:5] if v) in texts[int(row[5]) - 1], row
assert hashlib.sha256((root / f'data/catalog-sources/downloads/{slug}.pdf').read_bytes()).hexdigest() == data['sha256']
assert data['formats'] == ['ONE PACK', 'COLLECTORS BOX']
assert data['oddsUnitsPublished'] is False
assert len(data['odds']) == 48
odds = {o['name']: o for o in data['odds']}
assert odds['BASE CARD SHORT PRINT']['values'] == {'ONE PACK': '1:5', 'COLLECTORS BOX': '1:5'}
assert odds['BASE CARD SHORT PRINT GOLD REFRACTOR PARALLEL']['family'] == 'Base Card Short Prints'
assert odds['AUTOGRAPH RED REFRACTOR PARALLEL']['family'] == 'Base Card Autograph Parallel'
assert odds['SENSATIONAL SAMURAI']['family'] == 'Sensational Samurai Insert'
assert all('family' not in o for o in data['odds'] if o['name'].startswith(('TOKYO NEON NIGHTS', 'DUAL AUTOGRAPHS')))
assert odds['BASE CARD BLACK REFRACTOR PARALLEL']['values'] == {'ONE PACK':'1:193','COLLECTORS BOX':'1:194'}
assert odds['BASE CARD SHORT PRINT SUPERFRACTOR PARALLEL']['values'] == {'ONE PACK':'1:21,250','COLLECTORS BOX':'1:27,000'}
with pdfplumber.open(root/f'data/catalog-sources/downloads/{slug}-odds.pdf') as pdf:
    cells=pdf.pages[0].find_tables()[0].extract()
    assert cells[0]==['Card','ONE PACK','COLLECTORS BOX']
    assert [[o['name'],*o['values'].values()] for o in data['odds']]==cells[1:]
assert not any('numbering' in o for o in data['odds']), 'Colors are not numbering evidence'
catalog = json.loads((root / 'data/set-catalog.json').read_text())
set_record = next(s for s in catalog['sets'] if s['slug'] == slug)
assert set_record['dedicatedParser'] == 'scripts/import_topps_samurai_2026.py'
assert set_record['rowCount'] == 124 and set_record['coverageComplete'] is False
print('Verified all 124 literal source records and 96 literal revised odds values across two named formats, with unstated ratio units and exact family scopes.')
