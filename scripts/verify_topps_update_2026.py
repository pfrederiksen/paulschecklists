"""Independently compare every physical Update subject and original odds cell."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-update-series-baseball'
data = json.loads((ROOT / f'data/imports/{SLUG}.json').read_text())
rows = data['rows']
assert len(rows) == 3870 and len({r[0] for r in rows}) == 99
assert sum(r[4] == 'Rookie' for r in rows) == 1570
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
assert sum(not r[3] for r in rows) == 7
assert [r[1] for r in rows if r[0] == 'WORLD BASEBALL CLASSIC HIGHLIGHTS'] == ['WBCH-' + str(i) for i in range(1, 51)]
assert [r[1] for r in rows if r[0] == 'STRIKE ZONE HEROES'] == ['SZH-' + str(i) for i in range(1, 26)]
assert next(r for r in rows if r[1] == 'WBCH-1')[2:5] == ['Shohei Ohtani', 'Japan', '']
assert next(r for r in rows if r[1] == 'WBCH-50')[2:5] == ['Luis Arraez', 'Venezuela', '']
assert next(r for r in rows if r[1] == 'SZH-25')[2:5] == ['Mason Miller', 'San Diego Padres™', '']
compact = lambda value: re.sub(r'\s+', '', value)
path = ROOT / f'data/catalog-sources/downloads/{SLUG}.pdf'
assert hashlib.sha256(path.read_bytes()).hexdigest() == data['sha256']
pdf = PdfReader(path)
assert len(pdf.pages) == 67
printed_rookie_words = 0
disclaimer = {
    compact('Checklists provided by Topps reflect the intended configuration of that product'),
    compact('at the time of production, but actual contents and odds may vary.'),
    compact('2026 Topps Update Series Baseball'), compact('BASE SET')}
for number, page in enumerate(pdf.pages, 1):
    # Independent pypdf draw order compares complete original lines, rather
    # than reusing the importer's glyph bands or rectangular cell boundaries.
    # It preserves both overlapping buyback titles and their separate flags.
    text = page.extract_text()
    printed_rookie_words += len(re.findall(r'\bRookie\b', text))
    captions = {compact(c['text']) for c in data['sourceCaptions'] if c['page'] == number}
    actual = collections.Counter(compact(line) for line in text.splitlines()
                                 if compact(line) and compact(line) not in captions | (disclaimer if number == 1 else set()))
    expected = collections.Counter(compact(''.join(r[1:5])) for r in rows if int(r[5]) == number)
    assert actual == expected, (number, actual - expected, expected - actual)
assert printed_rookie_words == 1572
assert sum(len(re.findall(r'\bRookie\b', r[2])) for r in rows) == 2
assert printed_rookie_words - 2 == sum(r[4] == 'Rookie' for r in rows)
assert [r[2] for r in rows if r[0] == 'ICONIC BUYBACK REDEMPTIONS' and r[4]] == [
    '1982 Topps Cal Ripken Rookie Stars #21 Graded',
    '2018 Bowman Chrome Rookie Autograph Shohei Ohtani #BCRA-SO Graded']
revision = data['checklistRevision']
assert hashlib.sha256((ROOT / revision['file']).read_bytes()).hexdigest() == revision['sha256']
proof = json.loads((ROOT / revision['file']).read_text())
assert proof['currentDocument']['sha256'] == data['sha256']
previous_path = path.with_name(SLUG + '-10-12.pdf')
assert hashlib.sha256(previous_path.read_bytes()).hexdigest() == proof['previousDocument']['sha256']
assert len(proof['addedSubjectIdentities']) == 75 and not proof['removedSubjectIdentities']
assert len(proof['addedPrintedRookieFields']) == 909 and not proof['removedPrintedRookieFields']
assert len(data['publishedSpecifications']) == 5
for spec in data['publishedSpecifications'][:2]:
    assert spec['rows'] == [['Source caption', 'JAPAN EXCLUSIVE', spec['name']]]
    assert spec['evidenceFile'] == revision['file'] and spec['evidenceSha256'] == revision['sha256']
education = data['educationSource']
assert hashlib.sha256(path.with_name(SLUG + '-education.pdf').read_bytes()).hexdigest() == education['sha256']
assert hashlib.sha256((ROOT / education['evidenceFile']).read_bytes()).hexdigest() == education['evidenceSha256']
guide = json.loads((ROOT / education['evidenceFile']).read_text())
guide_text = PdfReader(path.with_name(SLUG + '-education.pdf')).pages[1].extract_text()
assert collections.Counter(re.findall(r'/\d+\b', guide_text)) == collections.Counter(
    value for cells in guide['facts']['parallelColumns'].values() for name, value in cells)
registry = json.loads((ROOT / 'data/parallel-specifications.json').read_text())['sets'][SLUG]
assert [(m['name'], m['numbering']) for m in registry] == [tuple(r) for r in guide['facts']['parallelColumns']['BASE PARALLELS']]
assert len(registry) == 6 and all(m['family'] == base[0] for m in registry)
assert all(m['evidenceFile'] == education['evidenceFile'] and m['evidenceSha256'] == education['evidenceSha256'] for m in registry)
for spec, heading in zip(data['publishedSpecifications'][2:4], ['INSERT PARALLELS', 'AUTOGRAPH PARALLELS']):
    assert [r[:2] for r in spec['rows']] == guide['facts']['parallelColumns'][heading]
    assert all('No exact checklist-family eligibility' in r[2] for r in spec['rows'])
assert data['publishedSpecifications'][-1]['rows'] == guide['facts']['boxConfigurations']
assert data['publishedSpecifications'][-1]['rows'][1][-1] == '1 AUTO AND RELIC PER BOX'
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
print('Verified 3,870 physical subjects, 1,570 original Rookie flags, both Japan-exclusive additions, six base limits, fourteen unjoined guide terms, original box units and all 281 nine-format odds rows.')
