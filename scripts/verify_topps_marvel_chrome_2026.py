"""Compare all printed content with independent pypdf text-object reads."""
import collections
import hashlib
import json
import logging
import re
from pathlib import Path

from pypdf import PdfReader

logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-chrome-marvel-comics'
data = json.loads((ROOT / 'data/imports' / (SLUG + '.json')).read_text())
path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest() == data['sha256']
assert data['dedicatedParser'] == 'scripts/import_topps_marvel_chrome_2026.py'
assert data['headers'] == ['Checklist section', 'Card number', 'Name', 'Published additional text', 'Source page']
assert len(data['rows']) == 764 and len({r[0] for r in data['rows']}) == 31
assert data['originalSubjectRows'] == data['rows']
headers = {r[0] for r in data['rows']} | set(data['originalArtistRosters'])
norm = lambda text: re.sub(r'\s+', '', text)
source = collections.defaultdict(str)
expected = collections.defaultdict(str)
source_extra = collections.defaultdict(list)
expected_extra = collections.defaultdict(list)
family = None
reader = PdfReader(path)
assert len(reader.pages) == 22
for pn, page in enumerate(reader.pages, 1):
    groups = []

    def visitor(text, cm, tm, font, size):
        if not text.strip():
            return
        y = tm[5] * cm[3] + cm[5]
        x = tm[4] * cm[0] + cm[4]
        objects = next((objects for baseline, objects in groups if abs(y - baseline) < .6), None)
        if objects is None:
            objects = []
            groups.append((y, objects))
        objects.append((x, text.strip()))

    page.extract_text(visitor_text=visitor)
    for y, objects in sorted(groups, reverse=True):
        # Original text objects are independent of the importer’s character
        # slicing. Physical x order also validates the shifted artist/year cells.
        compact = norm(' '.join(t for x, t in sorted(objects)))
        heading = next((h for h in headers if norm(h) == compact), None)
        if heading:
            family = heading
            continue
        if compact in ['BASE', 'INSERT', 'RELIC', 'AUTOGRAPH', 'SKETCH'] or pn == 1 and y > 710:
            continue
        if pn == 16 and compact in ['MARVEL', 'FACSIMILE', 'QUAD', 'AUTOGRAPHS']:
            family = 'MARVEL FACSIMILE QUAD AUTOGRAPHS'
            continue
        assert family
        source[(pn, family)] += compact
        additional = norm(' '.join(t for x, t in sorted(objects) if x >= 350))
        if additional:
            source_extra[(pn, family)].append(additional)
for family, number, name, additional, pn in data['rows']:
    key = (int(pn), family)
    expected[key] += norm(number + name + additional)
    if additional:
        expected_extra[key].append(norm(additional))
for family, rows in data['originalArtistRosters'].items():
    for name, pn in rows:
        expected[(int(pn), family)] += norm(name)
assert source == expected, 'Every printed character must belong to its numbered row or named unnumbered artist roster'
assert source_extra == expected_extra, 'Every original extra column must retain its own complete field'
assert sum(len(v) for v in expected_extra.values()) == 38
for family in ['CHARACTERS I', 'CHARACTERS II', 'CHARACTERS I CLAWED CHROME VARIATION', 'CHARACTERS II CLAWED CHROME VARIATION']:
    rows = [r for r in data['rows'] if r[0] == family]
    expected_numbers = set(range(1, 101) if family.startswith('CHARACTERS I ') or family == 'CHARACTERS I' else range(101, 201))
    assert len(rows) == 100 and {int(r[1]) for r in rows} == expected_numbers
for family in ['60 YEARS OF BLACK PANTHER', '65 FANTASTIC YEARS', 'X-FORCE 35TH ANNIVERSARY']:
    assert len([r for r in data['rows'] if r[0] == family]) == 10
assert next(r for r in data['rows'] if r[:2] == ['CHARACTERS II', '136'])[2] == 'Mary Jane'
assert next(r for r in data['rows'] if r[:2] == ['CHARACTERS II', '137'])[2] == 'Misery'
quad = [r for r in data['rows'] if r[0] == 'MARVEL FACSIMILE QUAD AUTOGRAPHS']
assert len(quad) == 8 and collections.Counter(r[1] for r in quad) == {'MFQ-DNSG': 4, 'MFQ-SGDV': 4}
assert [r[2] for r in quad if r[1] == 'MFQ-DNSG'] == ['Doctor Doom', 'Silver Surfer', 'Galactus', 'Namor']
assert next(r for r in data['rows'] if r[1] == 'CC-10')[2:] == ['Peter Parker, The Spectacular Spider-Man #107', '', '14']
assert next(r for r in data['rows'] if r[1] == 'TP-01')[3] == '1961'
assert next(r for r in data['rows'] if r[1] == 'CE-01')[3] == '1985'
assert all(r[3] == 'Bella Rachlin' for r in data['rows'] if r[0] == 'VARIED VISAGE AUTOGRAPHS')
assert data['originalArtistRosters']['ARTIST ORIGINALS'] == [['Kevin Eastman', '19'], ['Adi Granov', '19']]
artists = data['originalArtistRosters']['SKETCH CARD ARTISTS']
assert len(artists) == 124 and ['IQ', '21'] in artists and artists[-1] == ['ジェイソン (Jason)', '22']
assert not any(r[0] in ['IQ', 'AUTOGRAPHS'] for r in data['rows'])
assert len(data['odds']) == 179 and len(data['formats']) == 7
odds_path = path.with_name(SLUG + '-odds.pdf')
assert hashlib.sha256(odds_path.read_bytes()).hexdigest() == data['oddsSha256']
assert data['oddsParser'] == 'scripts/official_odds_layout.py'
assert next(o for o in data['odds'] if o['name'] == 'The One and Only: Stan Lee & Steve Ditko Superfractor')['family'] == 'THE ONE AND ONLY STAN LEE AND STEVE DITKO'
assert next(o for o in data['odds'] if o['name'] == 'The One and Only Superfractor')['family'] == 'THE ONE AND ONLY'
registry = json.loads((ROOT / 'data/parallel-specifications.json').read_text())['sets'][SLUG]
assert len(registry) == 2 and not any(p['family'] in ['CHARACTERS I', 'CHARACTERS II', 'THE ONE AND ONLY', 'SKETCH CARD ARTISTS'] for p in registry)
for spec in registry:
    assert hashlib.sha256((ROOT / spec['evidenceFile']).read_bytes()).hexdigest() == spec['evidenceSha256']
assert not any(h in data['headers'] for h in ['Team', 'Rookie'])
record = next(r for r in json.loads((ROOT / 'data/set-catalog.json').read_text())['sets'] if r['slug'] == SLUG)
assert record['releaseDate'] is None
print('Verified all 764 subject rows, 38 unlabelled cells, both 200-card programs, inline 136/137, retail inserts, quad signers, 126 artist entries and exact one-of-one guide scope.')
