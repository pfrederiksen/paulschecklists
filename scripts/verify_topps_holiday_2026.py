"""Independently verify source IDs, physical columns, original flags and guide scope."""
import collections
import hashlib
import json
import re
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-holiday-baseball'
data = json.loads((ROOT / 'data/imports' / (SLUG + '.json')).read_text())
path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest() == data['sha256']
assert data['dedicatedParser'] == 'scripts/import_topps_holiday_2026.py'
assert data['headers'] == ['Checklist section', 'Card number', 'Name', 'Team', 'Rookie', 'Source page']
assert len(data['rows']) == 640 and len({r[0] for r in data['rows']}) == 12
source_rows = []
with pdfplumber.open(path) as pdf:
    for pn, page in enumerate(pdf.pages, 1):
        # Independent spatial bands, rather than the importer's original draw-order slices.
        lines = collections.defaultdict(list)
        for word in page.extract_words(x_tolerance=.1):
            if word['x0'] < 130:
                lines[round(word['top'], 1)].append(word)
        for y, words in sorted(lines.items()):
            number = ''.join(w['text'] for w in sorted(words, key=lambda w: w['x0']))
            if not re.fullmatch(r'H\d+|HC\d+|[A-Z]+-[A-Z0-9]+', number):
                continue
            cells = []
            for left, right in [(136, 274), (274, 426), (426, 600)]:
                chars = sorted([c for c in page.chars if abs(c['top'] - y) < .2 and left <= c['x0'] < right], key=lambda c: c['x0'])
                cells.append(''.join(c['text'] for c in chars).strip())
            source_rows.append([number, *cells, str(pn)])
assert source_rows == [r[1:] for r in data['rows']], 'Every printed ID and original physical cell must match'
for family, prefix in [('BASE CARDS', 'H'), ('BASE CARDS CHROME VARIATION', 'HC')]:
    rows = [r for r in data['rows'] if r[0] == family]
    assert [r[1] for r in rows] == [prefix + str(n) for n in range(1, 201)]
    assert sum(r[4] == 'Rookie' for r in rows) == 51
assert sum(r[4] == 'Rookie' for r in data['rows']) == 191
faux = [r for r in data['rows'] if r[0] == 'HOLIDAY FAUX RELICS']
assert len(faux) == 5 and all(r[3:5] == ['', ''] for r in faux)
assert next(r for r in data['rows'] if r[0] == 'HOLIDAY VARIATION SHORT PRINT' and r[1] == 'H202')[2:5] == ['Jordan Walker', 'St. Louis Cardinals®', '']
assert next(r for r in data['rows'] if r[1] == 'H6')[2:4] == ['Nolan Arenado', 'Arizona Diamondbacks®']
assert len({r[2] for r in data['rows'] if r[0] == 'HIDDEN ELF'}) == 25
assert not any('AUTOGRAPH' in r[0] for r in data['rows'])
assert data['formats'] == ['MEGA BOX', 'COLLECTOR TIN', 'ADVENT CALENDAR']
assert data['oddsUnitsPublished'] is False and data['formatNamesPublished'] is True
assert 'serialColumn' not in data and len(data['odds']) == 66
odds_path = path.with_name(SLUG + '-odds.pdf')
assert hashlib.sha256(odds_path.read_bytes()).hexdigest() == data['oddsSha256'] == '64f07778a144e3671b802a061dba56f7e1fa81540be41928bbb1fe8201d9bb5b'
physical_odds = []
with pdfplumber.open(odds_path) as pdf:
    for pn, page in enumerate(pdf.pages, 1):
        # Independently group literal words inside fixed physical column bands.
        # The importer uses ruled table cells instead of these word positions.
        lines = collections.defaultdict(list)
        for word in page.extract_words(x_tolerance=.1):
            if word['top'] > 91.44:
                lines[round(word['top'], 1)].append(word)
        for y, words in sorted(lines.items()):
            cells = [' '.join(w['text'] for w in sorted(words, key=lambda w: w['x0']) if left <= w['x0'] < right)
                     for left, right in [(14, 314), (314, 612.6667), (612.6667, 911.3333), (911.3333, 1210)]]
            assert cells[0] and all(v == '—' or re.fullmatch(r'\d+:[\d,.]+', v) for v in cells[1:]), (pn, y, cells)
            physical_odds.append((pn, cells))
assert [(o['page'], [o['name'], *[o['values'][f] or '—' for f in data['formats']]]) for o in data['odds']] == physical_odds
assert sum(v is None for o in data['odds'] for v in o['values'].values()) == 121
reader = PdfReader(odds_path)
for pn, page in enumerate(reader.pages, 1):
    body = page.extract_text().split('ADVENT CALENDAR', 1)[1]
    assert ' '.join(body.split()) == ' '.join(' '.join(cells) for page_number, cells in physical_odds if page_number == pn)
by_name = {o['name']: o for o in data['odds']}
assert by_name['BASE CARDS HOLIDAY LIGHTS']['values']['COLLECTOR TIN'] == '4:1'
assert by_name['BASE CARDS BLUE METALLIC HOLIDAY LIGHTS']['values']['COLLECTOR TIN'] == '2:1'
assert by_name['MAKING THE NICE LIST']['values']['ADVENT CALENDAR'] == '1:1.3'
assert by_name['BASE CHROME VARIATION SUPERFRACTOR']['values']['MEGA BOX'] == '1:29,776'
assert by_name['BASE CHROME VARIATION SUPERFRACTOR']['family'] == 'BASE CARDS CHROME VARIATION'
assert by_name['HOLIDAY VARIATION BACKS SSP']['family'] == 'HOLIDAY VARIATION BACKS SUPER SHORT PRINT'
autographs = [o for o in data['odds'] if 'AUTOGRAPH' in o['name']]
assert len(autographs) == 7 and all(o['family'].endswith('(roster not published)') for o in autographs)
assert not any('AUTOGRAPH' in o['name'] for o in data['odds'] if o['family'] in {r[0] for r in data['rows']})
assert hashlib.sha256((ROOT / data['oddsEvidence']['file']).read_bytes()).hexdigest() == data['oddsEvidence']['sha256']
registry = json.loads((ROOT / 'data/parallel-specifications.json').read_text())
programs = registry['sets'][SLUG]
assert len(programs) == 14 and all(s['numbering'] == 'Numbering not stated' for s in programs)
assert len([s for s in programs if s.get('oddsName')]) == 7
for spec in programs:
    if spec.get('oddsName'):
        assert by_name[spec['oddsName']]['family'] == spec['family']
assert {p['family'] for p in programs if p['name'] in ['Refractor', 'Sparkle', 'Refractor Plaid']} == {'BASE CARDS CHROME VARIATION'}
assert not any(p['name'] in ['Green Refractor Plaid', 'Red Refractor Plaid', 'Light Blue Glitter Holiday', 'White Glitter Holiday'] for p in programs)
for spec in [*programs, *data['publishedSpecifications']]:
    assert hashlib.sha256((ROOT / spec['evidenceFile']).read_bytes()).hexdigest() == spec['evidenceSha256']
assert {c['family'] for c in registry['conflicts'] if c['slug'] == SLUG} == {'HIDDEN ELF', 'AUTOGRAPHS'}
record = next(s for s in json.loads((ROOT / 'data/set-catalog.json').read_text())['sets'] if s['slug'] == SLUG)
assert record['releaseStatus'] == 'Upcoming' and record['releaseDate'] == '2026-10-21'
assert 'case' in str(data['publishedSpecifications']) and 'three tins' in str(data['publishedSpecifications'])
print('Verified every Holiday source ID/cell, 640 rows, 191 literal flags, all 66 three-column odds and 121 null cells by independent physical words and full pypdf text flow. Literal 4:1 / 2:1 / 1:1.3 values, isolated autograph programs and unstated ratio units retained.')
