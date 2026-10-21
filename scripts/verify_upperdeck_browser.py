"""Independently reconcile every imported cell with retained official DOM markup."""
import gzip
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = 'data/official-upperdeck/backfill-observations-20261021-2200.json'


class TableCells(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag in ['td', 'th']:
            self.cell = []
        elif tag in ['br', 'p', 'div'] and self.cell is not None:
            self.cell.append(' ')

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ['td', 'th'] and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def unpack(spec, file_key, hash_key):
    archive = (ROOT / spec[file_key]).read_bytes()
    assert hashlib.sha256(archive).hexdigest() == spec['archiveSha256']
    raw = gzip.decompress(archive)
    assert hashlib.sha256(raw).hexdigest() == spec[hash_key]
    return raw


review = json.loads((ROOT / REVIEW).read_text())
catalog = json.loads((ROOT / 'data/set-catalog.json').read_text())['sets']
total = 0
expected = [2610, 4728, 2231, 2911, 82, 3426, 100, 378, 3340, 291, 267, 4775, 3061]
for source, count in zip(review['sources'], expected, strict=True):
    facts = json.loads(unpack(source, 'factsFile', 'factsSha256'))
    assert len(facts['tables']) == len(source['domTables']) == 1
    parser = TableCells()
    parser.feed(unpack(source['domTables'][0], 'file', 'sha256').decode())
    assert parser.rows == facts['tables'][0]['rows'], source['url']
    original = parser.rows
    header_index = next(i for i, row in enumerate(original) if any(row))
    headers, cards = original[header_index], original[header_index + 1:]
    assert len(cards) == count and all(len(row) == len(headers) for row in cards)
    record = next(r for r in catalog if r.get('sourcePage') == source['url'])
    payload = json.loads((ROOT / record['tableData']).read_text())
    assert record['dedicatedParser'] == 'scripts/import_upperdeck_browser.py'
    assert record['rowCount'] == len(cards) == len(payload['rows'])
    assert record['releaseDate'] is None and record['releaseStatus'] == 'Unverified'
    assert payload['sha256'] == source['factsSha256']
    assert payload['originalHeaders'] == headers
    assert payload['sourcePreambleRows'] == original[:header_index]
    assert set(payload['originalColumnMap']) == set(range(len(headers)))
    for actual, row in zip(payload['rows'], cards, strict=True):
        assert actual == [row[i] for i in payload['originalColumnMap']]
        assert actual[0] == row[headers.index('Set Name')]
        number = headers.index('Card') if 'Card' in headers else headers.index('Card #')
        assert actual[1] == row[number]
    for column in [payload['oddsColumn'], payload['serialColumn']]:
        if column is not None:
            original_column = payload['originalColumnMap'][column]
            assert [r[column] for r in payload['rows']] == [r[original_column] for r in cards]
    assert 'formats' not in payload and 'odds' not in payload
    assert payload['importKind'] == 'html' and payload['sectionColumn'] == 0
    if 'AEW' in record['title']:
        assert headers[0] == '1' and payload['headers'][0] == 'Set Name'
        assert cards[-1][3] == 'Best Friends'
    if 'CFL' in record['title']:
        assert header_index == 1 and not any(original[0])
        assert payload['rows'][-1][1] == 'CDA-WW'
    if 'Horton' in record['title']:
        assert 'Decription' in payload['headers'] and '#"d' in payload['headers']
        assert cards[-1][-2] == '1:13,428,000 Packs'
    total += count
assert total == 28200
print('Verified 13 complete Upper Deck browser imports /28,200 rows against independent DOM markup,')
print('all original cells, source/archive hashes, exact card/family joins, literal odds/numbering,')
print('AEW/event column order, CFL blank preamble, Tim Horton spelling and unverified release dates.')
