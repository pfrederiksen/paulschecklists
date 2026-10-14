"""Validate literal dual pairings, the complete booklet and ruled odds cells."""
import collections, hashlib, json, re
from pathlib import Path
import pdfplumber

root = Path(__file__).resolve().parents[1]
slug = 'topps-bowman-2026-topps-dynamic-duals-baseball'
data = json.loads((root / f'data/imports/{slug}.json').read_text())
rows = data['rows']
assert len(rows) == 131 and len({r[1] for r in rows}) == 131
assert len({r[0] for r in rows}) == 7
by_number = {r[1]: r for r in rows}
assert by_number['4'][4:] == ['Paul Skenes', 'Jacob Misiorowski', 'Pittsburgh Pirates®', 'Milwaukee Brewers™']
assert by_number['6-A'][4:] == ['Shohei Ohtani', 'Mookie Betts', 'Los Angeles Dodgers®', 'Los Angeles Dodgers®']
assert by_number['FF-3'][4:] == ['Shohei Ohtani (Pitching)', 'Sandy Koufax', 'Los Angeles Dodgers®', 'Los Angeles Dodgers®']
assert by_number['16'][4:] == ['Carson Williams', 'Owen Caissie', 'Tampa Bay Rays™', 'Miami Marlins®']
expected_signers = ['Shohei Ohtani', 'Mike Trout', 'Albert Pujols', 'Cal Ripken Jr.', 'Paul Skenes', 'Ronald Acuña Jr.', 'Ichiro', 'Ken Griffey Jr.', 'Juan Soto', 'Derek Jeter', 'Aaron Judge', 'Mookie Betts']
assert [r[0] for r in data['bookletSigners']] == expected_signers
booklet = by_number['DDO-01']
assert booklet[2].split('; ') == expected_signers
assert booklet[4].split('; ') == expected_signers and booklet[5] == booklet[7] == ''
assert booklet[6].split('; ') == [r[1] for r in data['bookletSigners']]
assert all(r[2] == r[4] + ' / ' + r[5] for r in rows if r[1] != 'DDO-01')
assert data['teamColumns'] == [6, 7] and len(data['rowTeams']) == len(rows)
for row, teams in zip(rows, data['rowTeams']):
    expected = list(dict.fromkeys([r[1] for r in data['bookletSigners']])) if row[1] == 'DDO-01' else list(dict.fromkeys(row[6:8]))
    assert teams == expected
assert 'Rookie' not in data['headers'] and data['formats'] == ['Packs']
assert len(data['odds']) == len({o['name'] for o in data['odds']}) == 37
with pdfplumber.open(root / f'data/catalog-sources/downloads/{slug}-odds.pdf') as pdf:
    original = pdf.pages[0].extract_table()
    assert original[0] == ['Description', 'Packs']
    assert [(o['name'], o['values']['Packs']) for o in data['odds']] == [(name, value) for name, value in original[1:]]
assert hashlib.sha256((root / f'data/catalog-sources/downloads/{slug}.pdf').read_bytes()).hexdigest() == data['sha256']
assert all(o['family'] == 'Short Print' for o in data['odds'] if o['categoryName'].startswith('SHORT PRINT'))
assert all(o['family'] == 'Base Card Dual Autographs' for o in data['odds'] if o['categoryName'].startswith('BASE CARD DUAL AUTO'))
assert not any('numbering' in o for o in data['odds']), 'Do not infer serial limits from colors or pack odds'
catalog = json.loads((root / 'data/set-catalog.json').read_text())
record = next(s for s in catalog['sets'] if s['slug'] == slug)
assert record['dedicatedParser'] == 'scripts/import_topps_dynamic_duals_2026.py'
assert record['coverageComplete'] is False and record['formats'] == 1
print('Verified 131 literal pairings, all 12 booklet signers, both team columns and all 37 distinct Description/Packs odds cells.')
