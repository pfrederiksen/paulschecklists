"""Independently compare every physical Update subject and original odds cell."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-update-series-baseball'
data = json.loads((ROOT / f'data/imports/{SLUG}.json').read_text())
rows = data['rows']
assert len(rows) == 3795 and len({r[0] for r in rows}) == 97
assert sum(r[4] == 'Rookie' for r in rows) == 661
assert collections.Counter(r[0] for r in rows if not r[1]) == {
    'FANATICS AUTHENTIC REDEMPTION CARDS': 87,
    'ICONIC BUYBACK REDEMPTIONS': 33, '75TH GIFTS REDEMPTIONS': 1}
base = ['VETERAN I', 'VETERANS II', 'ROOKIES', 'ROOKIE DEBUT', 'VETERAN COMBOS', 'SEASON HIGHLIGHTS']
assert {r[1] for r in rows if r[0] in base} == {'US' + str(i) for i in range(1, 351)}
assert [(r[2], r[4]) for r in rows if r[0] == 'VETERAN COMBOS' and r[1] == 'US26'] == [
    ('Gleyber Torres', ''), ('Kevin McGonigle', 'Rookie')]
assert [r[2] for r in rows if r[0] == 'MAJOR LEAGUE MATERIAL DUAL AUTOGRAPH CARDS' and r[1] == 'MLMDA-TJT'] == ['Trea Turner', 'J.T. Realmuto']
assert next(r for r in rows if r[1] == '75YTA-JE')[3:5] == ['', '']
assert rows[-1][1:4] == ['', 'Ketel Marte', 'Arizona Diamondbacks®']
compact = lambda value: re.sub(r'\s+', '', value)
path = ROOT / f'data/catalog-sources/downloads/{SLUG}.pdf'
assert hashlib.sha256(path.read_bytes()).hexdigest() == data['sha256']
with pdfplumber.open(path) as pdf:
    assert len(pdf.pages) == 100
    # Original draw order independently checks every complete number/name/team
    # sequence, including overlapping fields and repeated signer codes.
    text = [compact(p.extract_text(use_text_flow=True) or '') for p in pdf.pages[:73]]
    for row in rows:
        assert compact(''.join(row[1:4])) in text[int(row[5]) - 1], row
    flags = []
    for number, page in enumerate(pdf.pages[73:], 74):
        flags.extend((number - 73, w['top']) for w in page.extract_words() if w['text'] == 'Rookie')
    assert len(flags) == 661
    printed_flags = collections.Counter()
    for number, top in flags:
        page = pdf.pages[number - 1]
        line = [c for c in page.chars if abs(c['top'] - top) < .03]
        literal = compact(''.join(c['text'] for c in line))
        printed_flags[number, literal] += 1
    assert printed_flags == collections.Counter((int(r[5]), compact(''.join(r[1:4]))) for r in rows if r[4] == 'Rookie')
odds_path = path.with_name(SLUG + '-odds.pdf')
assert hashlib.sha256(odds_path.read_bytes()).hexdigest() == data['oddsSha256']
assert len(data['odds']) == 281 and len(data['formats']) == 9 and data['oddsUnitsPublished'] is False
with pdfplumber.open(odds_path) as pdf:
    literal = []
    for number, page in enumerate(pdf.pages, 1):
        table = page.find_tables()[0]
        header = table.extract()[0][0]
        assert collections.Counter(compact(header.removeprefix('Card'))) == collections.Counter(compact(''.join(data['formats'])))
        for row in table.rows[1:]:
            words = page.crop(row.bbox).extract_words(use_text_flow=True, x_tolerance=.1)
            values = [w for w in words if re.fullmatch(r'[\d,.]+(?::-?[\d,.]+)+|-', w['text'])]
            assert len(values) == 9, (number, row.bbox, words)
            name = ' '.join(w['text'] for w in words if w not in values)
            values.sort(key=lambda w:w['x1'])
            literal.append((name, number, {f: None if w['text'] == '-' else w['text'] for f, w in zip(data['formats'], values)}))
    assert [(o['name'], o['page'], o['values']) for o in data['odds']] == literal
for odd in data['odds']:
    assert 'numbering' not in odd
    if odd['name'].startswith('BASE CARDS '):
        assert odd['family'] == base[0] and odd['familyAliases'] == base[1:]
print('Verified 3,795 physical subjects, 661 original Rookie flags, 121 unnumbered redemptions, 350 base identities and every original cell in 281 nine-format odds rows.')
