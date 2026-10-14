"""Independently compare Galaxy rows with physical words and source glyphs."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-star-wars-chrome-galaxy'
d = json.loads((ROOT / 'data/imports' / (SLUG + '.json')).read_text())
p = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
assert hashlib.sha256(p.read_bytes()).hexdigest() == d['sha256']
assert d['dedicatedParser'] == 'scripts/import_topps_star_wars_galaxy_2026.py'
assert len(d['rows']) == 584 and len({r[0] for r in d['rows']}) == 15
assert 'Team' not in d['headers'] and 'Rookie' not in d['headers']
numbers, source_rows = [], []
with pdfplumber.open(p) as pdf:
    for pn, page in enumerate(pdf.pages, 1):
        # Number glyphs occupy a separate left column, including the Arial
        # production addition GA-BDH. No heading or artist is a card number.
        for word in page.extract_words(x_tolerance=.1):
            if word['top'] >= 52 and word['x0'] < 122 and re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9-]+', word['text']):
                numbers.append(word['text'])
        groups = collections.defaultdict(list)
        for char in page.chars:
            if char['top'] < 52 or 'Bold' in char['fontname']:
                continue
            # Use baselines from a separate clustering pass, so mixed font
            # cells and the Japanese/Latin last name remain whole rows.
            key = next((y for y in groups if abs(y - char['top']) < 2), char['top'])
            groups[key].append(char)
        for y, chars in sorted(groups.items()):
            source_rows.append((pn, ''.join(c['text'] for c in chars)))
assert collections.Counter(numbers) == collections.Counter(r[1] for r in d['rows'] if r[1])
assert len(source_rows) == 584
compact = lambda text: re.sub(r'\s+', '', text)
for (pn, text), row in zip(source_rows, d['rows']):
    assert int(row[3]) == pn
    fields = row[1] + row[2] + row[4] if row[1] else row[5]
    assert compact(fields) == compact(text), (pn, row, text)
assert [int(r[1]) for r in d['rows'] if r[0] == 'BASE CARDS'] == list(range(1, 101))
assert sum(r[0] == 'SKETCH CARD ARTISTS' for r in d['rows']) == 218
assert d['rows'][-1][5] == 'ジェイソン (Jason)'
assert d['rows'][0][2:5] == ["The Mandalorian's Escape", '1', 'Claudio Aboy']
assert next(r for r in d['rows'] if r[1] == 'GA-BDH')[2:5] == ['Bryce Dallas Howard', '8', 'Director']
assert next(r for r in d['rows'] if r[1] == 'GA-AD')[2:5] == ['Adam Driver', '8', 'Kylo Ren']
assert next(r for r in d['rows'] if r[1] == 'CLOUD-1')[4] == 'Chrstian Benavides', 'Retain printed spelling'
assert next(r for r in d['rows'] if r[1] == 'LAY-1')[4] == 'Doug Chaing', 'Retain printed spelling'
assert sum(r[1] == 'Q-ANDOR' for r in d['rows']) == 4
assert sum(r[1] == 'T-SOLO' for r in d['rows']) == 3
assert sum(r[1] == 'D-FO' for r in d['rows']) == 2
op = p.with_name(SLUG + '-odds.pdf')
assert hashlib.sha256(op.read_bytes()).hexdigest() == d['oddsSha256']
assert len(d['odds']) == 110 and d['formats'] == ['Hobby']
assert next(o for o in d['odds'] if o['name'] == 'Art of Knights of the Old Republic')['family'] == 'ART OF KNIGHTS OF THE REPUBLIC'
assert next(o for o in d['odds'] if o['name'] == 'Chrome Layers Original Art')['family'] == 'TOPPS CHROME LAYERS ORIGINAL ART'
with pdfplumber.open(op) as pdf:
    source = collections.Counter(w['text'] for page in pdf.pages for w in page.extract_words() if re.fullmatch(r'[\d,.]+(?::[\d,.]+)+', w['text']))
assert source == collections.Counter(v for o in d['odds'] for v in o['values'].values() if v)
proof = d['productConfigurationEvidence']
assert hashlib.sha256((ROOT / proof['file']).read_bytes()).hexdigest() == proof['sha256']
assert proof['source'] == 'https://www.topps.com/products/2026-star-wars-chrome%C2%AE-galaxy-hobby-box'
assert not d.get('parallelSpecifications'), 'No unverified guide numbering may be imported'
print('Verified all 366 printed numbered subject rows, 218 sketch artists, separate physical text cells, 110 literal odds categories and qualified product configuration evidence.')
