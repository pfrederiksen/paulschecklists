"""Compare all Holiday Football physical cells independently with pypdf."""
import collections
import hashlib
import json
import re
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-holiday-football'
data = json.loads((ROOT / 'data/imports' / (SLUG + '.json')).read_text())
path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest() == data['sha256'] == '667a525e9cf75dc472f46901dafd301f0c1b0482d1968598f49afabc1f78481f'
assert data['headers'] == ['Checklist section', 'Card number', 'Name', 'Team', 'Rookie', 'Source page']
assert data['originalSubjectRows'] == data['rows']
assert len(data['rows']) == len({tuple(r[:2]) for r in data['rows']}) == 763
assert data['dedicatedParser'] == 'scripts/import_topps_holiday_football_2026.py'
families = {r[0] for r in data['rows']}
assert len(families) == 15
source, family = [], None
for pn, page in enumerate(PdfReader(path).pages, 1):
    groups = collections.defaultdict(list)
    anchor = [None]

    def visit(text, cm, tm, font, size):
        if text.strip():
            if tm[5] + cm[5]:
                anchor[0] = round(tm[5] + cm[5], 2)
            assert anchor[0] is not None
            groups[anchor[0]].append(text.strip())

    page.extract_text(visitor_text=visit)
    for y, chunks in sorted(groups.items(), reverse=True):
        text = ' '.join(' '.join(chunks).split())
        if pn == 1 and y > 680:
            continue
        if text in families:
            family = text
            continue
        if text in {'BASE', 'INSERT', 'AUTOGRAPHS'}:
            continue
        assert len(chunks) in {3, 4}, (pn, y, chunks)
        assert family and re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+', chunks[0])
        cells = chunks + ([''] if len(chunks) == 3 else [])
        assert cells[3] in {'', 'Rookie'}
        source.append([family, *cells, str(pn)])
assert source == data['rows']
rows = data['rows']
for name, start, end in [('BASE CARDS', 1, 150), ('ROOKIES', 151, 200),
                         ('BASE CARDS CHROME VARIATION', 1, 150), ('ROOKIES CHROME VARIATION', 151, 200)]:
    assert [r[1] for r in rows if r[0] == name] == [str(i) for i in range(start, end + 1)]
assert sum(r[4] == 'Rookie' for r in rows) == 188
assert ['DEAR SANTA', 'DS-BT', 'Brenen Thompson', 'Los Angeles Chargers', '', '15'] in rows
assert rows[-1] == ['DEAR SANTA', 'DS-ZT', 'Zavion Thomas', 'Chicago Bears', 'Rookie', '16']
for number, player, team in [('4', 'Tua Tagovailoa', 'Atlanta Falcons'), ('62', 'Jaylen Waddle', 'Denver Broncos'),
                              ('96', 'Mike Evans', 'San Francisco 49ers'), ('119', 'Myles Garrett', 'Los Angeles Rams')]:
    assert any(r[:5] == ['BASE CARDS', number, player, team, ''] for r in rows)
assert not data['odds'] and not data['formats'] and not data['publishedSpecifications']
assert not data['formatNamesPublished'] and not data['oddsUnitsPublished']
proof_path = ROOT / data['sourceObservation']['file']
proof = json.loads(proof_path.read_text())
assert hashlib.sha256(proof_path.read_bytes()).hexdigest() == data['sourceObservation']['sha256']
assert hashlib.sha256(json.dumps(proof['facts'], ensure_ascii=False, sort_keys=True).encode()).hexdigest() == proof['factsSha256']
assert proof['checklistSha256'] == data['sha256']
assert not proof['approvedNumericMappings']
record = next(r for r in json.loads((ROOT / 'data/set-catalog.json').read_text())['sets'] if r['slug'] == SLUG)
assert record['releaseStatus'] == 'Upcoming' and record['releaseDate'] == '2026-10-23'
assert record['verifiedRelease']['url'] == 'https://www.topps.com/release-calendar'
assert 'not marked Pre-order' in record['verifiedRelease']['scope']
print('Verified 763 original Holiday Football cells, all 15 sections, two 200-card base programs, 188 literal Rookie flags and the blank DS-BT flag; odds/serial limits remain unverified.')
