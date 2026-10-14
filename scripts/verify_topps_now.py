"""Reconcile NOW shared tables against retained official observations."""
import json, hashlib, re
from urllib.parse import urlparse
from pathlib import Path

root = Path(__file__).resolve().parents[1]
observations = json.loads((root / 'data/topps-now-observations.json').read_text())
inventory = json.loads((root / 'data/topps-now-official-catalog.json').read_text())
keys = [(p['series'], p['number']) for p in observations]
assert len(keys) == len(set(keys)), 'Duplicate series/card numbers'
assert all(p['number'] and p['evidence']['title'] for p in observations)
regional_hashes=set()
for snapshot in (root/'data/catalog-sources').glob('topps-now-backfill-regional*.txt'):
    raw=snapshot.read_text()
    starts=list(re.finditer(r'^[^\n]*\((https://(?:www|uk|uk-next)\.topps\.com/products/[^)]+)\)\n',raw,re.M))
    for i,match in enumerate(starts):
        block=raw[match.start():starts[i+1].start() if i+1<len(starts) else len(raw)]
        lines=[re.sub(r'\ue200cite\ue202[^\ue201]*\ue201','',line.strip()).strip() for line in re.split(r'L\d+(?:@P\d+)?:\s*',block)[1:]]
        regional_hashes.add((match[1],hashlib.sha256('\n'.join(lines).encode()).hexdigest()))
for p in observations:
    parsed=urlparse(p['source'])
    assert parsed.scheme=='https' and parsed.hostname in {'www.topps.com','uk.topps.com','uk-next.topps.com'}
    assert not p['printRun'] or p['printRun'].replace(',', '').isdigit()
    assert len(p['evidence']['sha256']) == 64
    for proof in [p['evidence'],*p.get('fieldEvidence',{}).values()]:
        if urlparse(proof['url']).hostname in {'uk.topps.com','uk-next.topps.com'}:
            assert (proof['url'],proof['sha256']) in regional_hashes,'Regional evidence must reconcile to a retained official web snapshot'
    if p['evidence'].get('sourceKind') == 'official-archive-title':
        assert p['evidence']['sha256'] == hashlib.sha256(p['evidence']['title'].encode()).hexdigest()
    for field,proof in p.get('fieldEvidence',{}).items():
        assert field in {'printRun','saleFrom','saleUntil','parallels','terms'}
        assert len(proof['sha256'])==64 and urlparse(proof['url']).hostname in {'www.topps.com','uk.topps.com','uk-next.topps.com'}
        if proof.get('sourceKind')=='official-archive-title':
            assert field=='printRun'
            assert proof['sha256']==hashlib.sha256(proof['title'].encode()).hexdigest()
            assert re.search(r'PR:\s*([\d,]+)',proof['title'])[1]==p[field]
        elif field in {'saleFrom','saleUntil'}:
            assert proof['fields']['Available From' if field=='saleFrom' else 'Available Until']==p[field]
        elif field=='printRun':
            assert proof['fields'].get('Print Run')==p[field] or re.search(r'PR:\s*([\d,]+)',proof['title'])[1]==p[field]
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
    expected_supplementary=[{'series':p['series'],'number':p['number'],'field':field,'value':p[field],'evidence':proof} for p in selected for field,proof in sorted(p.get('fieldEvidence',{}).items())]
    assert data.get('supplementarySourceProducts',[])==expected_supplementary
    fingerprints=[(p['source'],p['evidence']['sha256'],*[(field,proof['url'],proof['sha256']) for field,proof in sorted(p.get('fieldEvidence',{}).items())]) for p in selected]
    assert data['sha256']==hashlib.sha256(json.dumps(fingerprints,ensure_ascii=False).encode()).hexdigest()
    for specification in data['publishedSpecifications']:
        for number, subject, parallel, source in specification['rows']:
            assert any(p['series'] == specification['name'] and p['number'] == number and p['name'] == subject and parallel in p['parallels'] and p['source'] == source for p in selected)
archive = json.loads((root / 'data/topps-now-archive-index.json').read_text())
assert archive['coverageComplete'] is False
assert [p['start'] for p in archive['pages']] == list(range(1, archive['pages'][-1]['start'] + 1, 24))
print(f"Verified {len(observations)} NOW observations, {len(inventory)} shared tables, source fingerprints, literal parallel terms and partial coverage labels.")
