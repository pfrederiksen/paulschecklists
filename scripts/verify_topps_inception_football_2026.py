"""Independently verify every Inception Football source cell and shared adapter scope."""
import collections
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-inception-football'
d = json.loads((ROOT / 'data/imports' / (SLUG + '.json')).read_text())
path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest() == d['sha256']
assert len(d['rows']) == 538 and len({tuple(r[:2]) for r in d['rows']}) == 523
assert len({r[0] for r in d['rows']}) == 17
assert sum(r[4] == 'Rookie' for r in d['rows']) == 340
assert d['rows'] == d['originalSubjectRows'] and d['headers'] == d['originalSubjectHeaders']
heads = {r[0] for r in d['rows']} | {'BASE', 'INSERT', 'AUTOGRAPH', 'AUTOGRAPH RELIC'}
compact = lambda text: re.sub(r'\s+', '', text)
for pn, page in enumerate(PdfReader(path).pages, 1):
    # A second PDF engine reads the original cell objects in draw order.
    tokens = []
    page.extract_text(visitor_text=lambda text, *args: tokens.append(' '.join(text.split()))
                      if text.strip() else None)
    actual, current = [], None
    for token in tokens:
        if token in heads:
            continue
        if re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+', token):
            if current:
                actual.append(current)
            current = [token]
        elif current:
            current.append(token)
    if current:
        actual.append(current)
    expected = [[r[1], r[2], r[3], *([r[4]] if r[4] else [])]
                for r in d['rows'] if r[5] == str(pn)]
    # The production disclaimer follows the page-one card stream in draw order.
    if pn == 1:
        assert actual[-1][:3] == expected[-1]
        assert all('Checklists' in t or 'product' in t or 'vary.' in t
                   for t in actual[-1][3:]), actual[-1]
        actual[-1] = actual[-1][:3]
    assert actual == expected, (pn, [(a, b) for a, b in zip(actual, expected) if a != b])
assert [int(r[1]) for r in d['rows'] if r[0] in {'BASE CARDS', 'ROOKIE'}] == list(range(1, 201))
assert all(r[4] == '' for r in d['rows'] if r[0] == 'BASE CARDS')
assert all(r[4] == 'Rookie' for r in d['rows'] if r[0] == 'ROOKIE')
assert next(r for r in d['rows'] if r[0] == 'BASE CARDS' and r[1] == '95')[2:5] == [
    'Jaylen Waddle', 'Denver Broncos', '']
assert next(r for r in d['rows'] if r[1] == 'DGA-EC')[2:5] == ['Earl Campbell', 'Houston Oilers', '']
for family, expected_count in [('DUAL ROOKIE AUTOGRAPHS', 7), ('DUAL ROOKIE RELIC AUTOGRAPHED BOOK', 8)]:
    counts = collections.Counter(r[1] for r in d['rows'] if r[0] == family)
    assert len(counts) == expected_count and set(counts.values()) == {2}
assert [(r[2], r[5]) for r in d['rows'] if r[1] == 'DRA-KS'] == [('Kenyon Sadiq', '8'), ('Cade Klubnik', '9')]
assert [(r[2], r[5]) for r in d['rows'] if r[1] == 'DRRA-PL'] == [('Makai Lemon', '11'), ('Cole Payton', '12')]
assert d['rows'][-1] == ['NFL FIRST MILESTONE AUTOGRAPH RELIC', 'FMRA-TS', 'Ty Simpson',
                         'Los Angeles Rams', 'Rookie', '12']
assert not d['odds'] and not d['formats'] and not d['parallelSpecifications']
assert d['formatNamesPublished'] is False and d['oddsUnitsPublished'] is False
r = next(r for r in json.loads((ROOT / 'data/set-catalog.json').read_text())['sets'] if r['slug'] == SLUG)
assert r['dedicatedParser'] == 'scripts/import_topps_inception_football_2026.py'
assert r['releaseDate'] == '2026-11-06' and r['releaseStatus'] == 'Upcoming'
assert r['verifiedRelease']['url'] == 'https://www.topps.com/release-calendar'
assert hashlib.sha256((ROOT / r['sourceObservation']['file']).read_bytes()).hexdigest() == r['sourceObservation']['sha256']
from import_official_catalog import run
assert run(dict(r)) == r, 'Generic refresh must preserve the dedicated physical parser'
print('Verified all538 original Name/Team/Rookie cells, 523 identities, 17 families, '
      '340 marks and15 two-signer cards, including both page-break continuations. '
      'Unpublished odds/limits and the separate November6 schedule remain scoped.')
