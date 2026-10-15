"""Compare every imported Heritage cell to independent PDF text-object reads."""
import collections
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-heritage-football'
data = json.loads((ROOT / 'data/imports' / (SLUG + '.json')).read_text())
path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest() == data['sha256']
assert data['dedicatedParser'] == 'scripts/import_topps_heritage_football_2026.py'
assert data['headers'] == ['Checklist section', 'Card number', 'Name', 'Team', 'Rookie', 'Published annotation', 'Source page']
assert len(data['rows']) == 1487 and len({r[0] for r in data['rows']}) == 30
source_rows = []
pdf = PdfReader(path)
assert len(pdf.pages) == 22
for pn, page in enumerate(pdf.pages, 1):
    # pypdf reads original text objects, independently of pdfplumber glyph slices.
    lines = collections.defaultdict(list)

    def visitor(text, cm, tm, font, size):
        if text.strip():
            lines[round(tm[5], 3)].append((round(tm[4] * cm[0] + cm[4], 2), text.strip()))

    page.extract_text(visitor_text=visitor)
    for y, items in sorted(lines.items(), reverse=True):
        if not any(x == 76.8 for x, text in items):
            continue
        cells = ['', '', '', '']
        for x, text in items:
            if x == 76.8:
                cells[1] += text
            elif x == 275.2:
                cells[2] += text
            elif x == 389.6:
                cells[3] += text
            elif x < 76:
                cells[0] += text
            else:
                raise ValueError((pn, y, items))
        assert re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+', cells[0]), (pn, y, items)
        source_rows.append([*cells, str(pn)])
assert source_rows == [r[1:] for r in data['originalSubjectRows']], 'Every original text cell must match, including overlapping redemptions'
assert all(row[:4] + row[5:] == original and row[4] == ('Rookie' if original[4] == 'Rookie' else '')
           for row, original in zip(data['rows'], data['originalSubjectRows']))
for family in ['BASE CARDS', 'BASE CARDS CHROME VARIATION']:
    rows = [r for r in data['rows'] if r[0] == family]
    expected_numbers = set(range(1, 401)) - ({259} if 'CHROME' in family else set())
    assert len(rows) == 408 and {int(r[1]) for r in rows} == expected_numbers
    assert sum(r[4] == 'Rookie' for r in rows) == 100
    assert collections.Counter(r[1] for r in rows)['201'] == 2
    assert len([r for r in rows if r[5].startswith('League Leaders')]) == 16
    assert len([r for r in rows if r[5].startswith('Team Cards')]) == 32
chrome = [r for r in data['rows'] if r[0] == 'BASE CARDS CHROME VARIATION']
assert [r[2] for r in chrome if r[1] == '142'] == ['Aidan Hutchinson', 'A.J. Terrell']
assert sum(r[4] == 'Rookie' for r in data['rows']) == 485
assert len([r for r in data['rows'] if not r[3]]) == 6
assert next(r for r in data['rows'] if r[0] == 'BASE CARDS' and r[1] == '383')[2:4] == ['Myles Garrett', 'Los Angeles Rams']
redemptions = [r for r in data['rows'] if r[0] == 'WALTER PAYTON ROOKIE REDEMPTION']
assert len(redemptions) == 34 and redemptions[0][2:4] == ['1976 Topps Walter Payton PSA 10 Redemption', 'Chicago Bears']
assert not data.get('odds') and not data.get('formats') and 'serialColumn' not in data
registry = json.loads((ROOT / 'data/parallel-specifications.json').read_text())
programs = registry['sets'][SLUG]
assert len(programs) == 19
numbered = [p for p in programs if p['numbering'] != 'Numbering not stated']
assert [(p['family'], p['name'], p['numbering']) for p in numbered] == [('HERITAGE ROOKIE AUTOGRAPHS', 'Gold', '/50')]
assert not any(p['family'] in ['CUT SIGNATURES', 'REAL ONE ROOKIE AUTOGRAPHS'] for p in programs)
assert {p['family'] for p in programs if 'Sparkle' in p['name']} == {'BASE CARDS CHROME VARIATION'}
assert any(p['name'] == 'Nickname' and 'equivalence is unverified' in p['qualification'] for p in programs)
cut = next(s for s in data['publishedSpecifications'] if s['name'] == 'CUT SIGNATURES')
assert cut['rows'][0][1] == 'Numbered to 1' and 'CA-WP1 through CA-WP5' in cut['rows'][0][2]
assert 'Published numbering' not in cut['headers'], 'An unresolved guide limit must not number the whole family'
guide_only = next(s for s in data['publishedSpecifications'] if s['name'].startswith('Guide-only autograph'))
assert guide_only['rows'][0][1] == 'Jack Lambert; Fred Biletnikoff'
assert not any('BUYBACK' in r[0] for r in data['rows']), 'Guide signers must not become an invented numbered roster'
assert {r[1] for r in data['rows'] if r[0] == 'CUT SIGNATURES'} == {f'CA-WP{n}' for n in range(1, 6)}
for spec in [*programs, *data['publishedSpecifications']]:
    assert hashlib.sha256((ROOT / spec['evidenceFile']).read_bytes()).hexdigest() == spec['evidenceSha256']
record = next(s for s in json.loads((ROOT / 'data/set-catalog.json').read_text())['sets'] if s['slug'] == SLUG)
assert record['releaseStatus'] == 'Upcoming' and record['releaseDate'] == '2026-10-21'
assert data['publishedSpecifications'][0]['rows'][2][2] == 'November 4, 2026'
print('Verified all 1487 original cells/IDs, 485 Rookie marks, paper numbers 1–400, Chrome repeated 142/missing 259, blank teams, overlapping redemption names and exact Gold /50 scope.')
