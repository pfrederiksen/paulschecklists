"""Independently compare original PDF text objects and every physical odds cell."""
import collections
import hashlib
import json
import re
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-heritage-baseball'
data = json.loads((ROOT / 'data/imports' / (SLUG + '.json')).read_text())
path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest() == data['sha256']
assert data['dedicatedParser'] == 'scripts/import_topps_heritage_baseball_2026.py'
assert len(data['rows']) == 1542 and len({r[0] for r in data['rows']}) == 40
source_rows = []
section = None
for pn, page in enumerate(PdfReader(path).pages, 1):
    objects = []

    def visitor(text, cm, tm, font, size):
        if text.strip():
            objects.append((text.strip(), 'Bold' in str((font or {}).get('/BaseFont', ''))))

    # pypdf retains separate original text objects even where its positional
    # callback loses the origins of name/team cells; object order is independent
    # of the importer’s pdfplumber glyph-origin slicing.
    page.extract_text(visitor_text=visitor)
    current = None

    def finish():
        if current is None:
            return
        family, number, cells = current
        assert 1 <= len(cells) <= 4
        source_rows.append([family, number, cells[0], cells[1] if len(cells) > 1 else '',
                            cells[2] if len(cells) > 2 else '', cells[3] if len(cells) > 3 else '', str(pn)])

    for text, bold in objects:
        if text in ['2026 TOPPS HERITAGE CHECKLIST', 'SUBJECT TO CHANGE*', '* - Denotes Short Print']:
            continue
        if bold:
            finish()
            current = None
            if text not in ['BASE', 'INSERT', 'AUTOGRAPH', 'AUTOGRAPH RELIC', 'RELIC']:
                section = text
        elif re.fullmatch(r'\d+|[A-Za-z0-9]+-[A-Za-z0-9]+', text):
            finish()
            current = [section, text, []]
        else:
            assert current, (pn, text)
            current[2].append(text)
    finish()
assert source_rows == data['originalSubjectRows'], 'Every original object, including mixed annotations, must match'
assert all(row[:4] + row[5:] == original and row[4] == ('Rookie' if original[4] == 'Rookie' else '')
           for row, original in zip(data['rows'], source_rows))
paper = ['BASE CARDS', 'LEAGUE LEADERS', 'RECORD BREAKERS', 'AL CHAMPIONS', 'NL CHAMPIONS',
         'WORLD SERIES HIGHLIGHTS', 'TURN BACK THE CLOCK', 'QUAD ROOKIES']
for suffix in ['', ' CHROME VARIATION']:
    rows = [r for r in data['rows'] if r[0] in [f + suffix for f in paper]]
    assert len(rows) == 456 and {int(r[1]) for r in rows} == set(range(1, 401))
    assert sum(r[4] == 'Rookie' for r in rows) == 108
    assert len([r for r in rows if r[1] == '372']) == 4
assert sum(r[4] == 'Rookie' for r in data['rows']) == 315
assert sum('*' in r[2] + r[3] for r in data['rows']) == 148
assert sum(not r[3] for r in data['rows']) == 10
back = [r for r in data['rows'] if r[6]]
assert len(back) == 2 and all(r[1] == '360' and r[6] == '*Back Variation' for r in back)
assert [r[2] for r in back] == ['Owen Caissie*', 'Owen Caissie']
assert next(r for r in data['rows'] if r[1] == 'ROA-BR')[5] == 'Base unnumbered autos are all red ink'
assert len([r for r in data['rows'] if r[1].startswith('77RO-')]) == 13
assert next(r for r in data['rows'] if r[0] == 'BASE CARDS' and r[1] == '359')[4] == 'Rookie'
assert not any(r[0] in ['Checklist', 'SUBJECT TO CHANGE*'] for r in data['rows'])
op = path.with_name(SLUG + '-odds.pdf')
assert hashlib.sha256(op.read_bytes()).hexdigest() == data['oddsSha256']
assert len(data['odds']) == 230 and len(data['formats']) == 12
assert data['formats'][0] == '6561 - MLB- HERITAGE 2026 FAT PACK EA'
with pdfplumber.open(op) as pdf:
    for pn, page in enumerate(pdf.pages, 1):
        words = page.extract_words()
        # Each printed SKU header and its ratios share a numeric right edge.
        # Validate values independently of the importer’s row crops and labels.
        edges = [w['x1'] for w in words if w['text'] == 'MLB-' and w['top'] < 105]
        assert len(edges) == 12
        top = min(w['top'] for w in words if re.fullmatch(r'\d[\d,]*(?::[\d,]+)+', w['text']))
        groups = collections.defaultdict(dict)
        for word in words:
            if word['top'] < top - .1 or not re.fullmatch(r'\d[\d,]*(?::[\d,]+)+|-', word['text']):
                continue
            column = min(range(12), key=lambda i: abs(edges[i] - word['x1']))
            assert abs(edges[column] - word['x1']) < 1
            cells = groups[round(word['top'], 1)]
            assert column not in cells
            cells[column] = None if word['text'] == '-' else word['text']
        expected = [o for o in data['odds'] if o['page'] == pn]
        assert len(groups) == len(expected)
        for (_, cells), odd in zip(sorted(groups.items()), expected):
            assert len(cells) == 12
            assert [cells[i] for i in range(12)] == [odd['values'][f] for f in data['formats']], (pn, odd['name'])
specs = json.loads((ROOT / 'data/parallel-specifications.json').read_text())['sets'][SLUG]
assert len(specs) == 9 and all(s['numbering'] == '/77' for s in specs)
assert sum(s['oddsName'].endswith(' COLOR OF THE YEAR') for s in specs) == 8
assert next(s for s in specs if s['family'] == 'REAL ONE AUTOGRAPHS')['oddsName'] == 'REAL ONE AUTOGRAPHS SPECIAL EDITION'
assert not any('CHROME' in s['oddsName'] for s in specs)
for spec in [*specs, *data['publishedSpecifications']]:
    assert hashlib.sha256((ROOT / spec['evidenceFile']).read_bytes()).hexdigest() == spec['evidenceSha256']
record = next(r for r in json.loads((ROOT / 'data/set-catalog.json').read_text())['sets'] if r['slug'] == SLUG)
assert record['releaseDate'] is None and record['releaseStatus'] == 'Released'
assert record['storeAvailabilityDate'] == '2026-03-18'
print('Verified 1542 original subject rows, 315 literal Rookie marks, both 400-number programs, mixed annotations, all 230 × 12 physical odds cells and nine exact /77 joins.')
