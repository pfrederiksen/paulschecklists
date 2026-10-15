"""Independently verify source IDs, physical columns, original flags and guide scope."""
import collections
import hashlib
import json
import re
from pathlib import Path

import pdfplumber

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
assert not data.get('odds') and not data.get('formats') and 'serialColumn' not in data
registry = json.loads((ROOT / 'data/parallel-specifications.json').read_text())
programs = registry['sets'][SLUG]
assert len(programs) == 14 and all(s['numbering'] == 'Numbering not stated' for s in programs)
assert {p['family'] for p in programs if p['name'] in ['Refractor', 'Sparkle', 'Refractor Plaid']} == {'BASE CARDS CHROME VARIATION'}
assert not any(p['name'] in ['Green Refractor Plaid', 'Red Refractor Plaid', 'Light Blue Glitter Holiday', 'White Glitter Holiday'] for p in programs)
for spec in [*programs, *data['publishedSpecifications']]:
    assert hashlib.sha256((ROOT / spec['evidenceFile']).read_bytes()).hexdigest() == spec['evidenceSha256']
assert {c['family'] for c in registry['conflicts'] if c['slug'] == SLUG} == {'HIDDEN ELF', 'AUTOGRAPHS'}
record = next(s for s in json.loads((ROOT / 'data/set-catalog.json').read_text())['sets'] if s['slug'] == SLUG)
assert record['releaseStatus'] == 'Upcoming' and record['releaseDate'] == '2026-10-21'
assert 'case' in str(data['publishedSpecifications']) and 'three tins' in str(data['publishedSpecifications'])
print('Verified every Holiday source ID/cell, 640 rows, 191 literal flags, H202, blank faux-relic teams, qualified parallel programs and original distribution units.')
