"""Reconcile the two official exports and every observed official family table."""
import collections
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
read = lambda path: json.loads((ROOT / path).read_text())
proof = read('data/official-panini/golf-2026-observations-20261020-2200.json')
record = next(r for r in read('data/set-catalog.json')['sets'] if r['slug'] == 'panini-2026-panini-par-three-liv-golf')
data = read(record['tableData'])
raw = (ROOT / record['sourceExport']).read_bytes()
assert hashlib.sha256(raw).hexdigest() == record['sha256'] == data['sha256'] == proof['exports'][0]['sha256']
rows = list(csv.reader(raw.decode('utf-8-sig').splitlines()))[1:]
assert len(rows) == 1935 and len({r[4] for r in rows}) == 91
assert sum(bool(r[9]) for r in rows) == 1920
assert all(r[9] == '' for r in rows if r[4] in ['Downtown', 'Downtown Tournament Champions'])
assert len([r for r in rows if not r[9]]) == 15
assert [r[4:] for r in rows] == [r[8:] for r in data['rows']]

def checked_file(ref):
    blob = (ROOT / ref['file']).read_bytes()
    assert hashlib.sha256(blob).hexdigest() == ref['sha256']
    return blob

norm = lambda text: ' '.join(text.upper().split())
def tuples(row, columns):
    parts = [row[i].split('/') for i in columns]
    assert len({len(p) for p in parts}) == 1
    return collections.Counter(tuple(norm(p) for p in values) for values in zip(*parts))

alternate = list(csv.reader(checked_file(proof['alternateExport']).decode().splitlines()))[1:]
assert len(alternate) == len(rows)
assert sum(a != b for a, b in zip(rows, alternate)) == 112
for a, b in zip(rows, alternate):
    assert a[:5] + a[8:] == b[:5] + b[8:]
    assert tuples(a, [5, 6, 7]) == tuples(b, [5, 6, 7])

tables = json.loads(checked_file(proof['tableObservation']))['tables']
assert len(tables) == 91 and {t['family'] for t in tables} == {r[4] for r in rows}
quad_rows = placeholders = 0
for table in tables:
    expected = [[norm(r[i]) for i in [8, 5, 6, 7, 9]] for r in rows if r[4] == table['family']]
    observed = [[norm(cell) for cell in row] for row in table['rows']]
    assert len(expected) == len(observed)
    for a, b in zip(expected, observed):
        if a[4] == '' and b[4] == '-':
            b[4] = ''
            placeholders += 1
        assert a[0] == b[0] and a[4] == b[4]
        if table['family'].startswith('Quad Team Swatches'):
            assert sum(tuples(a, [1, 2, 3]).values()) == 4
            assert sum(tuples(b, [1, 2, 3]).values()) == 2
            assert tuples(b, [1, 2, 3]) <= tuples(a, [1, 2, 3])
            quad_rows += 1
        else:
            assert tuples(a, [1, 2, 3]) == tuples(b, [1, 2, 3])
assert quad_rows == 78 and placeholders == 15
lookup = {(r[4], r[8]): r for r in rows}
assert lookup['Clubhouse Collection Signatures', '19'][5:10] == ['Matthew Wolff', 'RangeGoats GC', 'PL', '19', '19']
assert lookup['Tee Box Signatures', '2'][9] == lookup['Tee Box Signatures', '12'][9] == '75'
assert lookup['Tee Box Signatures', '3'][9] == '25'
assert lookup['Cleat Peek Brand Logo', '10'][9] == '4'
assert lookup['Base', '4'][5] == 'Byeong Hun An '
assert len(lookup['Quad Team Swatches', '1'][5].split('/')) == 4
assert record['releaseDate'] is None and not record['publishedOdds'] and not data.get('odds')
assert record['coverageComplete'] and proof['parallelAuditComplete'] is False
assert record['priorSourceOnlyEvidence']['sha256'] == hashlib.sha256((ROOT / record['priorSourceOnlyEvidence']['sourceExport']).read_bytes()).hexdigest()
checked_file(record['productGuideObservation'])
print('Verified 1,935 original rows / 91 families, 1,920 per-card SEQUENCE values, all official UI tables, both export hashes and complete quad subjects; release, odds and exhaustive parallel coverage remain unverified.')
