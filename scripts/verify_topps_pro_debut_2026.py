"""Independently compare every original Pro Debut PDF cell and repeated signer."""
import collections
import hashlib
import json
import re
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-pro-debut-baseball'
data = json.loads((ROOT / 'data/imports' / (SLUG + '.json')).read_text())
path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest() == data['sha256'] == '3f98609d8e9ac0eaecbc5edaf4a3bf0de370c865d08622b5dec4954a60ffc597'
assert data['headers'] == ['Checklist section', 'Card number', 'Name', 'Team', 'Source page']
assert data['originalSubjectRows'] == data['rows']
assert len(data['rows']) == 1044 and len({tuple(r[:2]) for r in data['rows']}) == 977
assert data['dedicatedParser'] == 'scripts/import_topps_pro_debut_2026.py'
families = {r[0] for r in data['rows']}
assert len(families) == 16
source, family = [], None
for pn, page in enumerate(PdfReader(path).pages, 1):
    groups = collections.defaultdict(list)
    anchor = [None]

    def visit(text, cm, tm, font, size):
        if text.strip():
            # This PDF writes each name and team as separate text chunks with
            # a zero reset matrix after the numbered row's anchored chunk.
            if tm[5] + cm[5]:
                anchor[0] = round(tm[5] + cm[5], 2)
            assert anchor[0] is not None
            groups[anchor[0]].append(text.strip())

    page.extract_text(visitor_text=visit)
    for y, chunks in sorted(groups.items(), reverse=True):
        text = ' '.join(' '.join(chunks).split())
        if pn == 1 and y > 725:
            continue
        if text in families:
            family = text
            continue
        if text in {'BASE', 'INSERT', 'AUTOGRAPH', 'AUTOGRAPH RELIC'}:
            continue
        cells = chunks
        assert len(cells) == 3, (pn, y, chunks)
        assert family and re.fullmatch(r'[A-Z]+-[A-Z0-9]+', cells[0]), (pn, y, chunks)
        assert cells[1] and cells[2], (pn, cells)
        source.append([family, *cells, str(pn)])
norm = lambda value: re.sub(r'\s+', '', value)
assert [[norm(c) for c in r] for r in source] == [[norm(c) for c in r] for r in data['rows']]
rows = data['rows']
for name, prefix in [('BASE CARDS', 'PD-'), ('BASE CARDS CHROME VARIATION', 'PDC-')]:
    assert [r[1] for r in rows if r[0] == name] == [prefix + str(i) for i in range(1, 201)]
for name, subjects, identities in [('PIPELINE PAIRINGS', 2, 24),
                                   ('PRO DEBUT DUAL AUTOGRAPHS', 2, 15),
                                   ('PRO DEBUT TRIPLE AUTOGRAPHS', 3, 14)]:
    counts = collections.Counter(r[1] for r in rows if r[0] == name)
    assert len(counts) == identities and set(counts.values()) == {subjects}
assert rows[-1] == ['PRO DEBUT JUMBO AUTOGRAPH RELIC', 'PDJAR-WJ', 'Walker Janek', 'Asheville Tourists®', '20']
assert any(r[1:4] == ['PD-28', 'Émilien Pitre', 'Bowling Green Hot Rods™'] for r in rows)
assert any(r[1:4] == ['PDJAR-KC', 'Kaelen Culpepper', 'Cedar Rapids Kernals™'] for r in rows)
assert any(r[1:4] == ['PDJAR-MS', 'Mike Sirota', 'Great Lake Loons™'] for r in rows)
assert not data['odds'] and not data['formats'] and not data['publishedSpecifications']
assert data['formatNamesPublished'] is False and data['oddsUnitsPublished'] is False
record = next(r for r in json.loads((ROOT / 'data/set-catalog.json').read_text())['sets'] if r['slug'] == SLUG)
assert record['releaseStatus'] == 'Upcoming' and record['releaseDate'] == '2026-11-18'
assert record['verifiedRelease']['url'] == 'https://www.topps.com/release-calendar'
assert 'not marked Pre-order' in record['verifiedRelease']['scope']
proof = json.loads((ROOT / data['sourceObservation']['file']).read_text())
assert proof['facts']['calendarEventLabel'] == 'Pre-order'
assert proof['facts']['generalReleaseDateVerified'] is False
assert not proof['approvedNumericMappings']
print('Verified all 1,044 original Pro Debut name/team cells, 977 identities, 16 families, repeated signers and preorder scope; unavailable odds/numbering stay explicit.')
