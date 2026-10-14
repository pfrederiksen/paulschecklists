"""Independently reconcile every original source glyph row and odds literal."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
SLUGS = ['topps-bowman-2025-star-wars-masterwork', 'topps-bowman-2025-topps-star-wars-smugglers-outpost']
compact = lambda text: re.sub(r'\s+', '', text)
for slug, numbered, artists, odds_count in zip(SLUGS, [660, 881], [208, 216], [90, 127]):
    d = json.loads((ROOT / 'data/imports' / (slug + '.json')).read_text())
    path = ROOT / 'data/catalog-sources/downloads' / (slug + '.pdf')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == d['sha256']
    assert d['dedicatedParser'] == 'scripts/import_topps_star_wars_backfills.py'
    assert len(d['rows']) == numbered + artists
    assert sum(bool(r[1]) for r in d['rows']) == numbered
    assert sum(bool(r[6]) for r in d['rows']) == artists
    assert 'Team' not in d['headers'] and 'Rookie' not in d['headers']
    source = []
    with pdfplumber.open(path) as pdf:
        for pn, page in enumerate(pdf.pages, 1):
            groups = collections.defaultdict(list)
            for char in page.chars:
                if 'Bold' in char['fontname']:
                    continue
                y = next((y for y in groups if abs(y-char['top']) < 2), char['top'])
                groups[y].append(char)
            for y, chars in sorted(groups.items()):
                text = ''.join(c['text'] for c in chars)
                if text.startswith(('Checklists provided by Topps', 'actual contents and odds')):
                    continue
                source.append((pn, text))
    assert len(source) == len(d['rows'])
    for (pn, text), row in zip(source, d['rows']):
        assert int(row[3]) == pn and compact(text) == compact(row[1]+row[2]+row[4]+row[5]), (pn, text, row)
    assert d['rows'][-1][6] == 'ジェイソン (Jason)'
    op = path.with_name(slug+'-odds.pdf')
    assert hashlib.sha256(op.read_bytes()).hexdigest() == d['oddsSha256']
    assert len(d['odds']) == odds_count and d['formats'] == ['SKU 1 Pack Rate']
    with pdfplumber.open(op) as pdf:
        literals = collections.Counter(w['text'] for p in pdf.pages for w in p.extract_words(use_text_flow=True) if re.fullmatch(r'[\d,.]+(?::[\d,.]+)+', w['text']))
        if 'masterwork' in slug:
            assert ['Skeleton Crew\nAuto Relic\nBlack', '1,249'] in pdf.pages[12].find_tables()[0].extract()
            literals.update(['1,249'])
    assert literals == collections.Counter(v for o in d['odds'] for v in o['values'].values() if v)
    if 'masterwork' in slug:
        assert [int(r[1]) for r in d['rows'] if r[0]=='CHARACTERS'] == list(range(1,101))
        assert next(r for r in d['rows'] if r[1]=='A-CAM')[2:5:2] == ['Carrie-Anne Moss', 'Jedi Master Indara']
        assert next(r for r in d['rows'] if r[1]=='ARC-LUNA')[4:6] == ['Cassian Andor', 'Missle: Andor']
        assert sum(r[1]=='DUO-AA' for r in d['rows']) == 2
        assert sum(r[1]=='UBC-456' for r in d['rows']) == 10
        assert sum(r[1]=='UBC-MAN' for r in d['rows']) == 10
        assert next(o for o in d['odds'] if o['name']=='Lothal Jedi Temple Mortis Gods Painting Puzzle')['values'] == {'SKU 1 Pack Rate':'1:160'}
        assert next(o for o in d['odds'] if o['name']=='Skeleton Crew Auto Relic Black')['values'] == {'SKU 1 Pack Rate':'1,249'}
    else:
        assert [r[1] for r in d['rows'] if r[0]=='Finest Base Set'] == [f'F-{n}' for n in range(1,76)]
        assert sum(r[1]=='ARS-25' for r in d['rows']) == 2
        assert not any(r[1]=='ARS-23' for r in d['rows'])
        assert next(r for r in d['rows'] if r[1]=='CB-AA')[2:5:2] == ['Adria Arjona', 'Bix Caleen']
        assert next(o for o in d['odds'] if o['name']=='Galactic Funk Gold Refractor Parallel')['family'] == 'Galactic Funk'
print('Verified 1,541 numbered subject rows, 424 sketch artists, separate original cells, literal SKU heading and all 217 odds categories including the unchanged malformed publisher value.')
