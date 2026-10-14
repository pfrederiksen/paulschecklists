"""Independently reconcile every original Disneyland PDF entry and odds value."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2025-topps-disneyland-70th-anniversary'
d = json.loads((ROOT / 'data/imports' / (SLUG + '.json')).read_text())
p = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
assert hashlib.sha256(p.read_bytes()).hexdigest() == d['sha256']
assert d['dedicatedParser'] == 'scripts/import_topps_disneyland_2025.py'
assert len(d['rows']) == 866 and len({r[0] for r in d['rows']}) == 36
assert 'Team' not in d['headers'] and 'Rookie' not in d['headers']
original = []
with pdfplumber.open(p) as pdf:
    for pn, page in enumerate(pdf.pages, 1):
        lines = collections.defaultdict(list)
        for char in page.chars:
            # Independent baseline clustering joins different fonts within
            # the Japanese/Latin final artist cell without losing glyphs.
            key = next((y for y in lines if abs(y - char['top']) < 1), char['top'])
            lines[key].append(char)
        for y, chars in sorted(lines.items()):
            if all('Bold' in c['fontname'] for c in chars):
                continue
            original.append((pn, ''.join(c['text'] for c in chars)))
assert len(original) == len(d['rows'])
compact = lambda text: re.sub(r'\s+', '', text)
for (pn, text), row in zip(original, d['rows']):
    assert int(row[3]) == pn
    fields = ([row[1], *row[4:7]] if pn <= 6 else
              [row[1], row[4], row[7]] if pn <= 8 else
              [row[1], *row[8:12]] if pn == 9 else
              [row[1], row[10]] if pn == 10 else
              [row[1], row[4]] if pn <= 12 else [row[12]])
    assert compact(''.join(fields)) == compact(text), (pn, row, text)
    if pn == 9:
        assert row[2] == ' '.join(row[8:10])
for page_range in [(1, 2), (3, 4), (5, 6)]:
    rows = [r for r in d['rows'] if int(r[3]) in page_range]
    assert [int(r[1]) for r in rows] == list(range(1, 151))
assert sum(r[0] == 'SKETCH ARTISTS' for r in d['rows']) == 77
assert d['rows'][-1][12] == 'ジェイソン (Jason)'
assert next(r for r in d['rows'] if r[1] == 'O&O-P')[0:3] == ['THE ONE AND ONLY PARTNERS', 'O&O-P', 'Partners Statue']
assert next(r for r in d['rows'] if r[1] == 'T55A-ANR')[8:12] == ['Anika Noni', 'Rose', 'Tiana', "Tiana's Bayou Adventure"]
assert next(r for r in d['rows'] if r[1] == 'AA-MK')[8:12] == ['Margaret', 'Kerry', 'Tinker Bell', "Peter Pan's Flight & Nighttime Spectaculars"]
assert all(not r[6] for r in d['rows'] if r[1] == '100'), 'Blank Land cells must stay blank'
cosmic = [r for r in d['rows'] if r[0] == 'TOMORROWLAND COSMIC CHROME']
assert sum(r[1] == 'TCC-11' for r in cosmic) == 2 and not any(r[1] == 'TCC-2' for r in cosmic)
redemption = next(r for r in d['rows'] if r[0] == 'MAGICAL GRAND PRIZE REDEMPTION')
assert not redemption[1] and redemption[2] == 'Grand Prize Redemption'
op = p.with_name(SLUG + '-odds.pdf')
assert hashlib.sha256(op.read_bytes()).hexdigest() == d['oddsSha256']
assert len(d['odds']) == 133 and d['formats'] == ['Hobby', 'Value Box EA', 'Value Box SE', 'Disneyland Exclusive']
with pdfplumber.open(op) as pdf:
    source = collections.Counter(w['text'] for page in pdf.pages for w in page.extract_words() if re.fullmatch(r'[\d,.]+(?::[\d,.]+)+', w['text']))
imported = collections.Counter(v for o in d['odds'] for v in o['values'].values() if v)
assert source == imported, (source - imported, imported - source)
registry = json.loads((ROOT / 'data/parallel-specifications.json').read_text())['sets'][SLUG]
assert d.get('parallelSpecifications') == registry and len(registry) == 9
print('Verified 788 numbered entries, one unnumbered redemption, 77 artists, all original fields, 133 odds categories and 9 approved numbering specifications.')
