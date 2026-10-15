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
browser_hashes=set()
for snapshot in (root/'data/catalog-sources').glob('topps-now-backfill-browser-*.json'):
    retained=json.loads(snapshot.read_text())
    assert retained['sourceKind']=='official-browser-product'
    for product in retained['products']:
        lines=[line.strip() for line in product['lines']]
        browser_hashes.add((product['url'],hashlib.sha256('\n'.join(lines).encode()).hexdigest()))
        assert ' - Card ' in lines[0] or ' - Sticker # ' in lines[0]
for snapshot in (root/'data/catalog-sources').glob('topps-now-backfill-regional*.txt'):
    raw=snapshot.read_text()
    starts=list(re.finditer(r'^[^\n]*\((https://(?:www|uk|uk-next|fr)\.topps\.com/products/[^)]+)\)\n',raw,re.M))
    for i,match in enumerate(starts):
        block=raw[match.start():starts[i+1].start() if i+1<len(starts) else len(raw)]
        lines=[re.sub(r'\ue200cite\ue202[^\ue201]*\ue201','',line.strip()).strip() for line in re.split(r'L\d+(?:@P\d+)?:\s*',block)[1:]]
        regional_hashes.add((match[1],hashlib.sha256('\n'.join(lines).encode()).hexdigest()))
for p in observations:
    parsed=urlparse(p['source'])
    assert parsed.scheme=='https' and parsed.hostname in {'www.topps.com','uk.topps.com','uk-next.topps.com','fr.topps.com'}
    assert not p['printRun'] or p['printRun'].replace(',', '').isdigit()
    assert len(p['evidence']['sha256']) == 64
    if p['evidence'].get('sourceKind')=='official-browser-product':
        assert (p['source'],p['evidence']['sha256']) in browser_hashes,'Browser facts must reconcile to retained official UI text'
        assert (root/p['evidence']['snapshotFile']).exists()
    for proof in [p['evidence'],*p.get('fieldEvidence',{}).values()]:
        if urlparse(proof['url']).hostname in {'uk.topps.com','uk-next.topps.com','fr.topps.com'}:
            assert (proof['url'],proof['sha256']) in regional_hashes,'Regional evidence must reconcile to a retained official web snapshot'
    if p['evidence'].get('sourceKind') == 'official-archive-title':
        assert p['evidence']['sha256'] == hashlib.sha256(p['evidence']['title'].encode()).hexdigest()
    for field,proof in p.get('fieldEvidence',{}).items():
        assert field in {'printRun','saleFrom','saleUntil','parallels','terms'}
        assert len(proof['sha256'])==64 and urlparse(proof['url']).hostname in {'www.topps.com','uk.topps.com','uk-next.topps.com','fr.topps.com'}
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
by_key={(p['series'],p['number']):p for p in observations}
mls_source=root/'data/catalog-sources/topps-now-backfill-browser-20261015-mls.json'
if mls_source.exists():
    snapshot=json.loads(mls_source.read_text());assert len(snapshot['products'])==3
    gaps=json.loads((root/'data/topps-now-import-gaps.json').read_text())
    aggregate=json.loads((root/'data/imports/topps-now-2026.json').read_text())
    for number,name in [('94','Cavan Sullivan, Robert Lewandowski'),('95','Inter Miami CF'),('96','St. Louis City SC')]:
        card=by_key[('2026 MLS Topps NOW®',number)]
        assert card['name']==name and card['saleUntil']=='Oct 18, 2026'
        assert card['parallels']==['/25 Orange','/10 Black','/5 Red','/1 FoilFractor'],'A spaced Parallels heading must retain every named color, not only FoilFractor'
        assert all(tier+'+ Print Run:' in card['terms'] for tier in ['50,000','100,000','250,000','500,000'])
        assert ('Relic Redemption Card' in card['terms'])==(number=='96'),'Relic redemption terms belong only to card 96'
        assert 'Numeric pack odds are not published.' in card['terms']
        if not card['saleFromISO']:
            assert any(p['series']==card['series'] and p['number']==number for p in gaps['pendingSaleDates'])
            assert not any(r[0]==card['series'] and r[1]==number for r in aggregate['rows']),'An expiry date must not establish calendar-year inclusion'
browser_source=root/'data/catalog-sources/topps-now-backfill-browser-20261014.json'
if browser_source.exists():
    assert len(json.loads(browser_source.read_text())['products'])==38
    assert by_key[('2026 AUSL Topps NOW®','11')]['saleFromISO']=='2026-06-18'
    assert by_key[('2026 AUSL Topps NOW®','14')]['parallels']==['/10 Black\u00a0Foil','/5 Red\u00a0Foil','/1 FoilFractor']
    assert '/1 Autograph Redemption Card' in by_key[('2026 AUSL Topps NOW®','14')]['terms']
    nhl=by_key[('2025-26 NHL Topps NOW®','188')]
    assert nhl['parallels']==['/10 Black Ice Parallels','/5 Red Ice Parallels','/1 Gold Ice Parallel']
    assert 'Published sticker types' in nhl['terms'] and 'non-base sticker' in nhl['terms']
    assert by_key[('2026 UFC Topps NOW®','35')]['parallels']==['/50 Gold Foil','/25 Orange\u00a0Foil','/10 Black\u00a0Foil','/5 Red\u00a0Foil','/1 FoilFractor']
    assert by_key[('2026-27 NFL Topps NOW®','5')]['saleFromISO']=='2026-09-11'
    assert ('2026 NFL Topps NOW®','5') not in by_key,'Conflicting regional series identity must not merge'
    bailey=by_key[('2026-27 NFL Topps NOW®','53')]
    assert bailey['source'].startswith('https://fr.topps.com/') and bailey['saleFromISO']=='2026-10-12'
    assert bailey['evidence']['fields']['Disponible À Partir De']==bailey['saleFrom']
    assert not by_key[('2026-27 NFL Topps NOW®','57')]['saleFromISO'],'An end date must not imply a sale start'
new_mlb_source=root/'data/catalog-sources/topps-now-backfill-20261014-new-mlb.txt'
if new_mlb_source.exists():
    raw=new_mlb_source.read_text()
    starts=list(re.finditer(r'^[^\n]*\((https://www\.topps\.com/products/[^)]+)\)\n',raw,re.M))
    assert len(starts)==3
    proofs={}
    for i,match in enumerate(starts):
        block=raw[match.start():starts[i+1].start() if i+1<len(starts) else len(raw)]
        lines=[line.strip() for line in re.split(r'L\d+:\s*',block)[1:]]
        proofs[match[1]]=hashlib.sha256('\n'.join(lines).encode()).hexdigest()
    for number,name in [('788','Freddy Peralta'),('789','Liam Hicks'),('790','Bryan Baker')]:
        card=by_key[('2026 MLB Topps NOW®',number)]
        assert card['name']==name and card['saleFromISO']=='2026-10-14'
        assert card['saleUntil']=='Oct 15, 2026'
        assert card['evidence']['sha256']==proofs[card['source']]
        assert card['parallels']==['/50 Gold Foil','/25 Orange\u00a0Foil','/10 Black\u00a0Foil','/5 Red\u00a0Foil','/1 FoilFractor']
        assert all(tier+'+ Print Run:' in card['terms'] for tier in ['50,000','100,000','250,000','500,000'])
        assert 'Numeric pack odds are not published.' in card['terms']
        # Thresholds are conditional distribution terms, never actual print runs.
        if not card['printRun']:
            assert 'Print Run' not in card['evidence']['fields']
print(f"Verified {len(observations)} NOW observations, {len(inventory)} shared tables, source fingerprints, literal parallel terms and partial coverage labels.")

new_mlb_source=root/'data/catalog-sources/topps-now-backfill-20261015-new-mlb.txt'
if new_mlb_source.exists():
    raw=new_mlb_source.read_text();starts=list(re.finditer(r'^[^\n]*\((https://www\.topps\.com/products/[^)]+)\)\n',raw,re.M));assert len(starts)==3
    proofs={}
    for i,match in enumerate(starts):
        block=raw[match.start():starts[i+1].start() if i+1<len(starts) else len(raw)]
        lines=[line.strip() for line in re.split(r'L\d+:\s*',block)[1:]]
        proofs[match[1]]=hashlib.sha256('\n'.join(lines).encode()).hexdigest()
    for number,name in [('791','Jackson Chourio'),('792','Jake Bauers'),('793','Jake Bauers, Garrett Mitchell')]:
        card=by_key[('2026 MLB Topps NOW®',number)]
        assert card['evidence']['sha256']==proofs[card['source']]
        assert card['name']==name and card['saleFromISO']=='2026-10-15'
        assert card['saleUntil']=='Oct 16, 2026'
        assert card['parallels']==['/50 Gold Foil','/25 Orange\u00a0Foil','/10 Black\u00a0Foil','/5 Red\u00a0Foil','/1 FoilFractor']
        assert card['evidence']['fields']['SKU']=='ARTBB-16C2S-26TN-0'+number
        assert card['evidence']['fields']['Properties']=='Milwaukee Brewers'
        assert all(tier+'+ Print Run:' in card['terms'] for tier in ['50,000','100,000','250,000','500,000'])
        if number=='791':
            for limit in ['10','5','1']:assert '/'+limit+' Autograph Redemption Card' in card['terms']
        else:assert 'Autograph Redemption' not in card['terms']
    print('Verified MLB NOW 791–793: exact official subjects, October 15–16 sale dates, five foil parallels and card-specific Chourio autograph redemption terms.')
