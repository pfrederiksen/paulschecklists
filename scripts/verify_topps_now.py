"""Reconcile NOW shared tables against retained official observations."""
import json, hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
observations = json.loads((root / 'data/topps-now-observations.json').read_text())
inventory = json.loads((root / 'data/topps-now-official-catalog.json').read_text())
keys = [(p['series'], p['number']) for p in observations]
assert len(keys) == len(set(keys)), 'Duplicate series/card numbers'
assert all(p['number'] and p['evidence']['title'] for p in observations)
for p in observations:
    assert p['source'].startswith('https://www.topps.com/')
    assert not p['printRun'] or p['printRun'].replace(',', '').isdigit()
    assert len(p['evidence']['sha256']) == 64
    if p['evidence'].get('sourceKind') == 'official-archive-title':
        assert p['evidence']['sha256'] == hashlib.sha256(p['evidence']['title'].encode()).hexdigest()
for entry in inventory:
    data = json.loads((root / entry['tableData']).read_text())
    eligible = [p for p in observations if p.get('saleFromISO') and p['saleFromISO'] >= '2026-01-01']
    selected = eligible if entry['slug'] == 'topps-now-2026' else [p for p in eligible if p['series'] == entry['title']]
    expected = [[p['series'], p['number'], p['name'], p['printRun'], p['saleFrom'], p['saleUntil'], '; '.join(p['parallels']), p['terms'], p['source']] for p in selected]
    assert data['rows'] == expected, entry['slug']
    assert entry['rowCount'] == len(expected)
    assert entry['backfillStart'] == '2026-01-01'
    assert entry['coverageComplete'] is False and data['coverageComplete'] is False
    assert entry['publishedOdds'] is False, 'Made-to-order runs are not pack odds'
    assert data['sourceProducts'] == [p['evidence'] for p in selected]
    for specification in data['publishedSpecifications']:
        for number, subject, parallel, source in specification['rows']:
            assert any(p['series'] == specification['name'] and p['number'] == number and p['name'] == subject and parallel in p['parallels'] and p['source'] == source for p in selected)
archive = json.loads((root / 'data/topps-now-archive-index.json').read_text())
assert archive['coverageComplete'] is False
assert [p['start'] for p in archive['pages']] == list(range(1, archive['pages'][-1]['start'] + 1, 24))
print(f"Verified {len(observations)} NOW observations, {len(inventory)} shared tables, source fingerprints, literal parallel terms and partial coverage labels.")
