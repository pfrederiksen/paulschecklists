"""Reapply hash-checked, complete official browser table observations."""
import gzip
import hashlib
import json
import re
from pathlib import Path

from import_official_catalog import run as import_official

ROOT = Path(__file__).resolve().parents[1]
REVIEW = 'data/official-upperdeck/backfill-observations-20261021-2200.json'


def read_source(source):
    archive = (ROOT / source['factsFile']).read_bytes()
    assert hashlib.sha256(archive).hexdigest() == source['archiveSha256']
    raw = gzip.decompress(archive)
    assert hashlib.sha256(raw).hexdigest() == source['factsSha256']
    return json.loads(raw)


def adapt(source, observed):
    facts = read_source(source)
    assert facts['url'] == source['url'] and len(facts['tables']) == 1
    original = facts['tables'][0]['rows']
    assert not facts['tables'][0]['spans']
    first = next(i for i, row in enumerate(original) if any(row))
    headers, rows = original[first], original[first + 1:]
    assert rows and all(len(row) == len(headers) for row in rows)
    family = headers.index('Set Name')
    card = next(i for i, h in enumerate(headers) if h in ['Card', 'Card #'])
    # Shared family joins use columns zero and one. Keep every original field,
    # including AEW's literal "1" heading and the event tables' Card # column.
    order = [family, card] + [i for i in range(len(headers)) if i not in [family, card]]
    normalized_headers = [headers[i] for i in order]
    normalized_rows = [[row[i] for i in order] for row in rows]
    if headers[card] == 'Card #':
        normalized_headers.insert(1, 'Card number')
        normalized_rows = [[row[0], row[1], *row[1:]] for row in normalized_rows]
        column_map = [order[0], order[1], *order[1:]]
    else:
        column_map = order
    title = facts['title'].removesuffix(' Checklist')
    year = re.search(r'20\d\d(?:[-/]\d{2,4})?', title)
    slug = 'upper-deck-' + re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    table_path = 'data/imports/' + slug + '.json'
    serial = next((i for i, h in enumerate(normalized_headers)
                   if h in ["Serial #'d", "#'d", '#"d']), None)
    odds = next((i for i, h in enumerate(normalized_headers) if 'odds' in h.lower()), None)
    payload = {
        'title': title, 'headers': normalized_headers, 'rows': normalized_rows,
        'source': facts['url'], 'sha256': source['factsSha256'],
        'sourceHashKind': 'Normalized complete official browser table snapshot; not raw HTML',
        'sourceObservation': REVIEW, 'sourceFactsFile': source['factsFile'],
        'originalHeaders': headers, 'originalColumnMap': column_map,
        'sourcePreambleRows': original[:first], 'sectionColumn': 0,
        'serialColumn': serial, 'oddsColumn': odds,
    }
    record = {
        'title': title, 'slug': slug, 'page': 'sets/' + slug + '.html',
        'manufacturer': 'Upper Deck', 'sport': facts['categories'][0],
        'year': year.group(0) if year else 'Unspecified',
        'sourcePage': facts['url'], 'checklistUrl': facts['url'],
        'releaseStatus': 'Unverified', 'releaseDate': None,
        'verified': observed, 'firstObserved': observed,
        'checklistAvailabilityObserved': observed,
        'discoverySource': 'https://upperdeck.com/checklists/',
        'sourceObservation': REVIEW, 'tableData': table_path,
        'status': 'Source table', 'rowCount': len(rows),
        'catalogEvidence': 'Complete original official checklist table cells retained from '
            'a fresh browser read. The product year is preserved where printed; directory '
            'filter year and first checklist observation do not establish a general release '
            'date. Odds, numbering, SPs and distribution wording retain their original '
            'units and qualifiers. Exhaustive product-guide/parallel eligibility remains unverified.',
    }
    (ROOT / table_path).write_text(json.dumps(payload, ensure_ascii=False) + '\n')
    # Use the established official-catalog HTML adapter without refetching or
    # substituting blocked HTTP pages for the reviewed browser evidence.
    record = import_official(record)
    payload = json.loads((ROOT / table_path).read_text())
    payload['serialColumn'] = serial
    (ROOT / table_path).write_text(json.dumps(payload, ensure_ascii=False) + '\n')
    record['dedicatedParser'] = 'scripts/import_upperdeck_browser.py'
    return record


def main():
    review = json.loads((ROOT / REVIEW).read_text())
    catalog_path = ROOT / 'data/set-catalog.json'
    inventory_path = ROOT / 'data/upperdeck-official-catalog.json'
    catalog = json.loads(catalog_path.read_text())
    inventory = json.loads(inventory_path.read_text())
    records = [adapt(source, review['observed']) for source in review['sources']]
    replacements = {r['sourcePage']: r for r in records}
    for current in [catalog['sets'], inventory]:
        seen = set()
        for i, row in enumerate(current):
            if row.get('sourcePage') in replacements:
                current[i] = replacements[row['sourcePage']]
                seen.add(row['sourcePage'])
        current.extend(r for r in records if r['sourcePage'] not in seen)
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    print('Imported', len(records), 'complete Upper Deck tables /',
          sum(r['rowCount'] for r in records), 'original card rows; release dates unverified.')


if __name__ == '__main__':
    main()
