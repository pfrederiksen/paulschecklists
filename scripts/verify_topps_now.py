"""Reconcile NOW shared tables against retained official observations."""
import json, hashlib, re, runpy
from urllib.parse import urlparse
from pathlib import Path
from topps_now_identity import observation_key, product_family, verified_single_card

root = Path(__file__).resolve().parents[1]
observations = json.loads((root / 'data/topps-now-observations.json').read_text())
inventory = json.loads((root / 'data/topps-now-official-catalog.json').read_text())
keys = [observation_key(p) for p in observations]
assert len(keys) == len(set(keys)), 'Duplicate series/card numbers'
assert all((p['number'] or p.get('identityKind') == 'official-single-card-product') and p['evidence']['title'] for p in observations)
listing_path=root/'data/topps-now-active-listings.json'
if listing_path.exists():
    listing=json.loads(listing_path.read_text())
    aggregate=json.loads((root/'data/imports/topps-now-2026.json').read_text())
    reconcile=runpy.run_path(str(root/'scripts/audit_topps_now_active.py'))['reconcile']
    active=reconcile(listing,observations,aggregate)
    audit=json.loads((root/'data/topps-now-active-audit.json').read_text())
    assert audit['listingSha256']==hashlib.sha256(listing_path.read_bytes()).hexdigest()
    assert audit['products']==active and not audit['historicalCoverageComplete']
    assert not any(p['status'].startswith('missing-') for p in active)
    # An unchanged listing must still reveal a missing public row.
    published_index=next((i for i,p in enumerate(active) if p['status']=='published'),None)
    if published_index is not None:
        sample=next(p for p in observations if p['source']==active[published_index]['url'])
        reduced={**aggregate,'rows':[r for r in aggregate['rows'] if (r[0],r[1])!=(sample['series'],sample['number'])]}
        assert reconcile(listing,observations,reduced)[published_index]['status']=='missing-published-row'
        assert reconcile(listing,[p for p in observations if p is not sample],aggregate)[published_index]['status']=='missing-observation'
regional_hashes=set()
browser_hashes=set()
for snapshot in (root/'data/catalog-sources').glob('topps-now-backfill-browser-*.json'):
    retained=json.loads(snapshot.read_text())
    assert retained['sourceKind']=='official-browser-product'
    for product in retained['products']:
        lines=[line.strip() for line in product['lines']]
        browser_hashes.add((product['url'],hashlib.sha256('\n'.join(lines).encode()).hexdigest()))
        fields=dict(line.split('  | ',1) for line in lines if '  | ' in line)
        assert re.search(r' (?:- )?Card ',lines[0]) or ' - Sticker # ' in lines[0] or verified_single_card(lines[0],fields,lines)
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
    expected = [[product_family(p), p['number'], p['name'], p['printRun'], p['saleFrom'], p['saleUntil'], '; '.join(p['parallels']), p['terms'], p['source']] for p in selected]
    assert data['rows'] == expected, entry['slug']
    assert entry['rowCount'] == len(expected)
    assert entry['backfillStart'] == '2026-01-01'
    assert entry['coverageComplete'] is False and data['coverageComplete'] is False
    assert entry['publishedOdds'] is False, 'Made-to-order runs are not pack odds'
    assert data['sourceProducts'] == [p['evidence'] for p in selected]
    expected_supplementary=[{'series':p['series'],**({'family':p['family']} if p.get('family') else {}),'number':p['number'],'field':field,'value':p[field],'evidence':proof} for p in selected for field,proof in sorted(p.get('fieldEvidence',{}).items())]
    assert data.get('supplementarySourceProducts',[])==expected_supplementary
    fingerprints=[(p['source'],p['evidence']['sha256'],*[(field,proof['url'],proof['sha256']) for field,proof in sorted(p.get('fieldEvidence',{}).items())]) for p in selected]
    assert data['sha256']==hashlib.sha256(json.dumps(fingerprints,ensure_ascii=False).encode()).hexdigest()
    for specification in data['publishedSpecifications']:
        for number, subject, parallel, source in specification['rows']:
            assert any(product_family(p) == specification['name'] and p['number'] == number and p['name'] == subject and parallel in p['parallels'] and p['source'] == source for p in selected)
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
    if not (root/'data/catalog-sources/topps-now-backfill-browser-20261017-2100-kyle-hamilton.json').exists():
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

bowman_source=root/'data/catalog-sources/topps-now-backfill-20261017-bowman-football.txt'
if bowman_source.exists():
    raw=bowman_source.read_text();starts=list(re.finditer(r'^[^\n]*\((https://www\.topps\.com/products/[^)]+)\)\n',raw,re.M));assert len(starts)==18
    expected_runs={'2':'989','3':'1294','4':'790','6':'939','8':'895','9':'1409','10':'665','11':'754','12':'1243','13':'559','14':'576','15':'521','16':'2279','17':'4264','18':'695','19':'616','20':'549','21':'415'}
    for i,match in enumerate(starts):
        block=raw[match.start():starts[i+1].start() if i+1<len(starts) else len(raw)]
        lines=[line.strip() for line in re.split(r'L\d+:\s*',block)[1:]]
        title=next(line for line in lines if line.startswith('## '));number=re.search(r' - Card (\d+) - PR:',title)[1]
        card=by_key[('2026-27 Bowman U NOW® Football',number)]
        assert card['source']==match[1] and card['evidence']['sha256']==hashlib.sha256('\n'.join(lines).encode()).hexdigest()
        assert card['printRun']==expected_runs[number]
        date='2026-09-08' if int(number)<=4 else '2026-09-14' if int(number)<=8 else '2026-09-21' if int(number)<=12 else '2026-09-28' if int(number)<=16 else '2026-10-05'
        assert card['saleFromISO']==date and card['saleFrom']==card['evidence']['fields']['Available From'] and card['saleUntil']==card['evidence']['fields']['Available Until']
        assert card['parallels']==['/50 Gold Foil','/25 Orange\u00a0Foil','/10 Black\u00a0Foil','/5 Red\u00a0Foil','/1 FoilFractor']
        assert all(tier+'+ Print Run:' in card['terms'] for tier in ['50,000','100,000','250,000','500,000'])
        assert ('Relic Redemption Card' in card['terms'])==(number=='12')
        assert ('Autograph Card' in card['terms'])==(number=='17')
        assert ('Image Variation Short Prints' in card['terms'])==(number=='16')
        assert 'Numeric pack odds are not published.' in card['terms']
    bowman=next(s for s in inventory if s['title']=='2026-27 Bowman U NOW® Football')
    assert bowman['rowCount']>=23 and bowman['coverageComplete'] is False
    assert by_key[('2026-27 Bowman U NOW® Football','12')]['saleFrom']=='21 set 2026','Retain the literal localized official date'
    assert by_key[('2026-27 Bowman U NOW® Football','14')]['name']=='Mestemaker/Hawkins/Young','Do not infer expanded names'
    assert by_key[('2026-27 Bowman U NOW® Football','4')]['evidence']['fields']['Properties']=='Arizona State','Retain source assignments without inferred corrections'
    print('Verified 18 Bowman U NOW Football backfills: exact product-title runs, official sale dates, five foil parallels, four qualified print-run thresholds and isolated autograph/relic/image-variation terms; the 23-card series remains partial.')

active_source=root/'data/catalog-sources/topps-now-backfill-browser-20261017-active.json'
if active_source.exists():
    retained=json.loads(active_source.read_text());assert len(retained['products'])==29
    by_url={p['source']:p for p in observations}
    for product in retained['products']:
        lines=[line.strip() for line in product['lines']];card=by_url[product['url']]
        if card['evidence'].get('snapshotFile')!=str(active_source.relative_to(root)):continue
        fields=dict(line.split('  | ',1) for line in lines if '  | ' in line)
        assert card['evidence']['sha256']==hashlib.sha256('\n'.join(lines).encode()).hexdigest()
        assert card['name']==fields['Subjects']
        assert card['saleFrom']==fields['Available From'] and card['saleUntil']==fields['Available Until']
        start=lines.index('Parallels:')+1;expected=[]
        for line in lines[start:]:
            if not re.match(r'^/\d+\s+',line):break
            expected.append(line)
        assert card['parallels']==expected
        for line in lines:
            if line.startswith('* ') or re.match(r'^[\d,]+\+ Print Run:',line):
                assert line.removeprefix('* ') in card['terms']
        if card['printRun']:
            assert card.get('fieldEvidence',{}).get('printRun') or fields.get('Print Run'),'A later run needs its own official evidence; conditional thresholds are not a run'
    for number in ['794','795','796','797','798']:
        card=by_key[('2026 MLB Topps NOW®',number)]
        if card['evidence'].get('snapshotFile')!=str(active_source.relative_to(root)):continue
        assert card['saleFromISO']=='2026-10-16'
        assert ('Autograph Redemption Card' in card['terms'])==(number in {'794','797'})
        assert ('/44 Milwaukee Brewers Image Variation Short Prints' in card['terms'])==(number=='798')
    for number in ['94','95','96']:
        assert by_key[('2026 MLS Topps NOW®',number)]['saleFromISO']=='2026-10-15'
    assert next(s for s in inventory if s['title']=='2026-27 UEFA Nations League Topps NOW®')['sport']=='soccer'
    print('Verified all 29 products in the retained October 17 product snapshot, including exact per-card dates, subjects, foil ladders and conditional terms; current active coverage is checked separately.')

run_source=root/'data/catalog-sources/topps-now-backfill-browser-20261017-1700-print-runs.json'
if run_source.exists():
    retained=json.loads(run_source.read_text());assert len(retained['products'])==6
    expected={'782':'2169','783':'5691','784':'1858','785':'1770','786':'584','787':'573'}
    for product in retained['products']:
        lines=[s.strip() for s in product['lines']]
        number=re.search(r' - Card (\d+) - PR:',lines[0])[1]
        card=by_key[('2026 MLB Topps NOW®',number)]
        assert card['printRun']==expected[number]
        assert card['evidence']['sha256']==hashlib.sha256('\n'.join(lines).encode()).hexdigest()
        assert card['saleFromISO']=='2026-10-13' and card['saleUntil']=='Oct 14, 2026'
    print('Verified six freshly published MLB NOW print runs from exact official product titles; no pack odds inferred.')

basketball_source=root/'data/catalog-sources/topps-now-backfill-browser-20261017-1800-bowman-basketball.json'
if basketball_source.exists():
    retained=json.loads(basketball_source.read_text());assert len(retained['products'])==27
    expected_runs=['1196','2049','5885','495','641','708','715','833','1297','332','520','1118','1484','1705','693','1011','779','1278','573','633','264','297','287','1333','733','3995','1517']
    expected_starts=['2026-03-20']+['2026-03-21']*3+['2026-03-22']*4+['2026-03-23']*3+['2026-03-24']+['2026-03-27']*2+['2026-03-28']*2+['2026-03-29']*2+['2026-03-30']*2+['2026-03-31']*2+['2026-04-04']+['2026-04-06']*2+['2026-04-07']*2
    for product in retained['products']:
        lines=[line.strip() for line in product['lines']]
        number=re.search(r' - Card (\d+) - PR:',lines[0])[1]
        card=by_key[('2025-26 Bowman U NOW® Basketball',number)]
        fields=dict(line.split('  | ',1) for line in lines if '  | ' in line)
        assert card['source']==product['url'] and card['evidence']['sha256']==hashlib.sha256('\n'.join(lines).encode()).hexdigest()
        assert card['name']==fields['Subjects'] and card['printRun']==expected_runs[int(number)-100]
        assert card['saleFromISO']==expected_starts[int(number)-100]
        assert card['saleFrom']==fields['Available From'] and card['saleUntil']==fields['Available Until']
        assert card['parallels']==['/50 Gold Foil','/25 Orange Foil','/10 Black Foil','/5 Red Foil','/1 FoilFractor']
        for line in lines:
            if line.startswith('* ') or re.match(r'^[\d,]+\+ Print Run:',line):assert line.removeprefix('* ') in card['terms']
        assert bool(re.search(r'/\d+ Relic Redemption Card',card['terms']))==(number in {'123','125','126'})
        assert ('Auto-Relic Redemption Card' in card['terms'])==(number in {'102','124'})
        assert ('Autograph Card' in card['terms'])==(number in {'101','107','111','112','113','116'})
        assert ('Inscribed Autograph Redemption Card' in card['terms'])==(number=='108')
        assert all(tier+'+ Print Run:' in card['terms'] for tier in ['50,000','100,000','250,000','500,000'])
        assert 'Numeric pack odds are not published.' in card['terms']
    basketball=next(s for s in inventory if s['title']=='2025-26 Bowman U NOW® Basketball')
    assert basketball['rowCount']>=27 and basketball['coverageComplete'] is False and basketball['sport']=='basketball'
    assert by_key[('2025-26 Bowman U NOW® Basketball','118')]['name']=='Sarah Strong, Tarris Reed Jr.'
    assert by_key[('2025-26 Bowman U NOW® Basketball','122')]['name']=="Agot Makeer, Ta'Niya Latson"
    print('Verified 27 Bowman U NOW Basketball cards: official March/April sale windows, published print runs, five foil parallels, exact multi-subject cells and isolated autograph/relic terms; archive coverage remains partial.')

basketball_backfill=root/'data/catalog-sources/topps-now-backfill-browser-20261017-1900-bowman-basketball.json'
if basketball_backfill.exists():
    retained=json.loads(basketball_backfill.read_text());assert len(retained['products'])==70
    data=json.loads((root/'data/imports/topps-now-2025-26-bowman-u-now-basketball.json').read_text())
    public_numbers={r[1] for r in data['rows']};eligible=0;excluded=0
    for product in retained['products']:
        lines=[line.strip() for line in product['lines']]
        number=re.search(r' - Card (\d+) - ',lines[0])[1]
        card=by_key[('2025-26 Bowman U NOW® Basketball',number)]
        fields=dict(line.split('  | ',1) for line in lines if '  | ' in line)
        assert card['evidence']['sha256']==hashlib.sha256('\n'.join(lines).encode()).hexdigest()
        assert card['name']==fields['Subjects'] and card['saleFrom']==fields['Available From'] and card['saleUntil']==fields['Available Until']
        run=re.search(r' - PR: (\d+)$',lines[0])
        assert card['printRun']==(run[1] if run else '')
        assert card['parallels']==['/50 Gold Foil','/25 Orange Foil','/10 Black Foil','/5 Red Foil','/1 FoilFractor']
        source_terms=[line.removeprefix('* ') for line in lines[lines.index('Overview')+1:lines.index('Parallels:')] if line.startswith('* ')]
        assert card['terms'].splitlines()[0]=='Published card types: '+'; '.join(source_terms),'Keep each redemption, autograph and variation term attached to its printed card'
        if card['saleFromISO']>='2026-01-01':
            assert number in public_numbers;eligible+=1
        else:
            assert number not in public_numbers;excluded+=1
    assert eligible==57 and excluded==13
    ambiguous=by_key[('2025-26 Bowman U NOW® Basketball','94')]
    assert ambiguous['name']=='AJ Dybantsa, Kevin Durant' and ambiguous['printRun']==''
    assert ambiguous['evidence']['unlabelledTitleSuffix']=='5738' and 'unlabelled value 5738' in ambiguous['terms']
    gaps=json.loads((root/'data/topps-now-import-gaps.json').read_text())
    assert any(g['number']=='94' and g['unlabelledValue']=='5738' for g in gaps['unverifiedPrintRuns'])
    assert by_key[('2025-26 Bowman U NOW® Basketball','99')]['saleFromISO']=='2026-03-16'
    assert by_key[('2025-26 Bowman U NOW® Basketball','42')]['saleFromISO']=='2026-01-02'
    assert by_key[('2025-26 Bowman U NOW® Basketball','41')]['saleFromISO']=='2025-12-30'
    assert len(data['rows'])>=84 and data['coverageComplete'] is False
    print('Verified 57 further calendar-year Bowman Basketball cards, 13 excluded December sale starts, exact card-specific terms and an explicitly unverified unlabelled title suffix on card 94.')

kyle_source=root/'data/catalog-sources/topps-now-backfill-browser-20261017-2100-kyle-hamilton.json'
if kyle_source.exists():
    retained=json.loads(kyle_source.read_text());assert len(retained['products'])==1
    product=retained['products'][0];lines=[line.strip() for line in product['lines']]
    card=by_key[('2026-27 NFL Topps NOW®','57')]
    assert card['source']==product['url'] and card['name']=='Kyle Hamilton'
    assert card['evidence']['sha256']==hashlib.sha256('\n'.join(lines).encode()).hexdigest()
    assert 'Product is available from Oct 12, 2026' in lines and 'Available From  | Oct 12, 2026' in lines
    assert card['saleFromISO']=='2026-10-12' and card['saleUntil']=='Oct 15, 2026'
    assert card['printRun']=='','Conditional print-run thresholds do not establish an actual run'
    assert card['parallels']==['/50 Gold Foil','/25 Orange\u00a0Foil','/10 Black\u00a0Foil','/5 Red\u00a0Foil','/1 FoilFractor']
    assert all(tier+'+ Print Run:' in card['terms'] for tier in ['50,000','100,000','250,000','500,000'])
    assert 'Autograph' not in card['terms'] and 'Relic' not in card['terms']
    for slug in ['topps-now-2026','topps-now-2026-27-nfl-topps-now']:
        data=json.loads((root/'data/imports'/(slug+'.json')).read_text())
        rows=[r for r in data['rows'] if r[0]==card['series'] and r[1]=='57']
        assert len(rows)==1 and rows[0][2:6]==['Kyle Hamilton','','Oct 12, 2026','Oct 15, 2026']
        assert data['coverageComplete'] is False
    gaps=json.loads((root/'data/topps-now-import-gaps.json').read_text())
    assert not any(g['series']==card['series'] and g['number']=='57' for g in gaps['pendingSaleDates'])
    print('Verified NFL NOW 57 sale start from both the official sentence and Specs; published in both shared tables with no inferred print run or pack odds.')

punctuation_source=root/'data/catalog-sources/topps-now-backfill-browser-20261017-2300-title-punctuation.json'
if punctuation_source.exists():
    retained=json.loads(punctuation_source.read_text());assert len(retained['products'])==4
    expected={('2026-27 UCL Topps NOW®','1'):('Paris Saint-Germain','1326','2026-08-17','Aug 24, 2026'),('2026-27 UCL Topps NOW®','3'):('Khvicha Kvaratskhelia','2832','2026-08-17','Aug 24, 2026'),('2026-27 UCL Topps NOW®','4'):('Brian Madjo','8275','2026-08-17','Aug 24, 2026'),('2026 Topps NOW®','A201'):('Artemis II','24420','2026-04-02','Apr 5, 2026')}
    for product in retained['products']:
        lines=[line.strip() for line in product['lines']]
        assert 'NOW® Card ' in lines[0] and 'NOW® - Card ' not in lines[0]
        number=re.search(r' Card ([A-Za-z0-9]+) - PR:',lines[0])[1]
        key=next(key for key in expected if key[1]==number);card=by_key[key]
        assert (card['name'],card['printRun'],card['saleFromISO'],card['saleUntil'])==expected[key]
        assert card['evidence']['sha256']==hashlib.sha256('\n'.join(lines).encode()).hexdigest()
        assert card['evidence']['snapshotFile']==str(punctuation_source.relative_to(root))
        original_terms=[line.removeprefix('* ') for line in lines[lines.index('Overview')+1:lines.index('Parallels:')] if line.startswith('* ')]
        assert card['terms'].splitlines()[0]=='Published card types: '+'; '.join(original_terms)
        data=json.loads((root/'data/imports/topps-now-2026.json').read_text())
        assert sum(r[0]==key[0] and r[1]==number for r in data['rows'])==1
        if number!='A201':
            assert len(card['parallels'])==4 and not any('/50' in p for p in card['parallels'])
            assert ('/5 Relic Redemption Card' in card['terms'])==(number=='4')
            assert ('/5 Auto-Relic Redemption Card' in card['terms'])==(number=='3')
        else:
            assert len(card['parallels'])==5 and 'Artemis II Image Variation Super Short Prints' in card['terms']
    entertainment=next(s for s in inventory if s['title']=='2026 Topps NOW®')
    assert entertainment['sport']=='entertainment' and entertainment['coverageComplete'] is False
    print('Verified hyphenless official Card labels for UCL 1/3/4 and Artemis II A201, exact dates/runs, card-specific terms and published entertainment classification.')

marvel_source=root/'data/catalog-sources/topps-now-backfill-browser-20261018-0000-marvel.json'
if marvel_source.exists():
    retained=json.loads(marvel_source.read_text());assert len(retained['products'])==6
    by_url={p['source']:p for p in observations}
    marvel=[p for p in observations if p['series']=='2026 Marvel Topps NOW®']
    assert len(marvel)>=6 and len({observation_key(p) for p in marvel})==len(marvel)
    assert len({product_family(p) for p in marvel})==len(marvel),'Unnumbered products need separate exact families'
    marvel_entry=next(s for s in inventory if s['title']=='2026 Marvel Topps NOW®')
    assert marvel_entry['sport']=='entertainment' and marvel_entry['releaseDate'] is None
    data=json.loads((root/marvel_entry['tableData']).read_text())
    expected_runs=['35984','15885','33838','5770','5073','8482']
    expected_dates=['2026-09-23','2026-09-15','2026-07-29','2026-07-01','2026-05-12','2026-03-24']
    for i,product in enumerate(retained['products']):
        lines=[line.strip() for line in product['lines']]
        fields=dict(line.split('  | ',1) for line in lines if '  | ' in line)
        card=by_url[product['url']]
        assert card['number']=='' and card['identityKind']=='official-single-card-product'
        identity=verified_single_card(lines[0],fields,lines)
        assert identity and identity['family']==card['family']
        assert card['name']==fields['Subjects'] and card['printRun']==expected_runs[i]
        assert card['saleFromISO']==expected_dates[i]
        assert card['saleFrom']==fields['Available From'] and card['saleUntil']==fields['Available Until']
        assert card['evidence']['sha256']==hashlib.sha256('\n'.join(lines).encode()).hexdigest()
        assert card['parallels']==['/99 Green Foil','/75 Blue Foil','/50 Gold Foil','/25 Orange Foil','/10 Black Foil','/5 Red Foil','1/1 FoilFractor']
        for line in lines:
            if line.startswith('* ') or line.startswith('*Parallels') or re.match(r'^[\d,]+\+ Print Run:',line):assert line.removeprefix('* ') in card['terms']
        assert ('Jon Bernthal' in card['terms'])==(i==4)
        assert ('Vincent D\'Onofrio' in card['terms'])==(i==5)
        specs=[s for s in data['publishedSpecifications'] if s['name']==card['family']]
        assert len(specs)==1 and len(specs[0]['rows'])==7
        assert all(r[0]=='' and r[1]==card['name'] and r[3]==card['source'] for r in specs[0]['rows'])
        assert not verified_single_card(lines[0],{**fields,'Product Type':'Multi-card Set'},lines)
        assert not verified_single_card(lines[0],{**fields,'Card number':'123'},lines)
        assert not verified_single_card(lines[0],fields,[line for line in lines if 'Open-Edition Base Card' not in line])
    # These products must also reconcile if they appear in a future active listing.
    listing={'listings':[{'reportedProductCount':len(marvel),'products':[{'url':p['source'],'title':p['evidence']['title']} for p in marvel]}]}
    statuses=reconcile(listing,observations,data)
    assert all(p['status']=='published' for p in statuses)
    reduced={**data,'rows':data['rows'][1:]}
    assert sum(p['status']=='missing-published-row' for p in reconcile(listing,observations,reduced))==1
    assert sum(p['status']=='missing-observation' for p in reconcile(listing,[p for p in observations if p is not marvel[0]],data))==1
    assert not verified_single_card('Anthony Edwards - 2025-26 NBA Topps NOW® - Card - PR: 1057',fields,lines)
    review=json.loads((root/'data/official-source-reviews/now-archive-title-review-20261017.json').read_text())
    assert not {p['url'] for p in retained['products']} & {p['url'] for p in review['pendingProductReviews']}
    gaps=json.loads((root/'data/topps-now-import-gaps.json').read_text())
    assert not {p['url'] for p in retained['products']} & {p['url'] for p in gaps['unparsedNumberedTitles']}
    print('Verified six unnumbered Marvel NOW single-card products: URL identities, blank published numbers, exact product families, official sale windows/runs, seven foil parallels and isolated autograph/SP terms; active reconciliation detects missing rows without number guesses.')

entertainment_source=root/'data/catalog-sources/topps-now-backfill-browser-20261018-0100-disney-star-wars.json'
if entertainment_source.exists():
    retained=json.loads(entertainment_source.read_text());assert len(retained['products'])==5
    by_url={p['source']:p for p in observations}
    expected_runs=['2665','18319','3592','28832','11984']
    expected_starts=['2026-07-08','2026-06-17','2026-03-04','2026-05-20','2026-04-06']
    aggregate=json.loads((root/'data/imports/topps-now-2026.json').read_text())
    reviewed=[]
    for i,product in enumerate(retained['products']):
        lines=[line.strip() for line in product['lines']]
        fields=dict(line.split('  | ',1) for line in lines if '  | ' in line)
        card=by_url[product['url']];reviewed.append(card)
        identity=verified_single_card(lines[0],fields,lines)
        assert identity and card['identityKind']=='official-single-card-product' and card['number']==''
        assert card['family']==identity['family'] and card['family']==re.sub(r' - PR: [\d,]+$','',lines[0])
        assert card['series']==('2026 Disney Topps NOW®' if i<3 else '2026 Star Wars Topps NOW®')
        assert card['printRun']==expected_runs[i] and card['saleFromISO']==expected_starts[i]
        assert card['name']==fields['Subjects'] and card['saleFrom']==fields['Available From'] and card['saleUntil']==fields['Available Until']
        assert card['evidence']['fields']==fields and card['evidence']['sha256']==hashlib.sha256('\n'.join(lines).encode()).hexdigest()
        assert card['parallels']==['/99 Green Foil','/75 Blue Foil','/50 Gold Foil','/25 Orange Foil','/10 Black Foil','/5 Red Foil','1/1 FoilFractor']
        for line in lines:
            if line.startswith('* ') or line.startswith('*Parallels') or re.match(r'^[\d,]+\+ Print Run:',line):assert line.removeprefix('* ') in card['terms']
        assert ('Tim Allen' in card['terms'])==(i==1) and ('Tom Hanks' in card['terms'])==(i==1)
        assert ('Pedro Pascal' in card['terms'])==(i==3) and ('Sam Witwer' in card['terms'])==(i==4)
        assert all(tier+'+ Print Run:' in card['terms'] for tier in ['50,000','100,000','250,000','500,000'])
        assert 'Numeric pack odds are not published.' in card['terms']
        if i<3:assert 'Properties' not in fields,'Do not invent a Disney Properties cell'
        entry=next(s for s in inventory if s['title']==card['series'])
        assert entry['sport']=='entertainment' and entry['releaseStatus']=='Ongoing' and entry['releaseDate'] is None
        table=json.loads((root/entry['tableData']).read_text())
        for data in [aggregate,table]:
            specs=[s for s in data['publishedSpecifications'] if s['name']==card['family']]
            assert len(specs)==1 and len(specs[0]['rows'])==7
            assert all(r[0]=='' and r[1]==card['name'] and r[3]==card['source'] for r in specs[0]['rows'])
        assert not verified_single_card(lines[0],{**fields,'Category':'Sports'},lines)
        assert not verified_single_card(lines[0],{**fields,'Subjects':''},lines)
        assert not verified_single_card('2026 Disney Topps NOW® 11-Card Team Set - PR: 1',fields,lines)
    assert len({observation_key(p) for p in reviewed})==5
    listing={'listings':[{'reportedProductCount':5,'products':[{'url':p['source'],'title':p['evidence']['title']} for p in reviewed]}]}
    assert all(p['status']=='published' for p in reconcile(listing,observations,aggregate))
    first=reviewed[0]
    reduced={**aggregate,'rows':[r for r in aggregate['rows'] if r[8]!=first['source']]}
    assert reconcile(listing,observations,reduced)[0]['status']=='missing-published-row'
    review=json.loads((root/'data/official-source-reviews/now-archive-title-review-20261017.json').read_text())
    gaps=json.loads((root/'data/topps-now-import-gaps.json').read_text())
    urls={p['source'] for p in reviewed}
    assert not urls & {p['url'] for p in review['pendingProductReviews']}
    assert not urls & {p['url'] for p in gaps['unparsedNumberedTitles']}
    assert any('Anthony Edwards' in p['title'] for p in review['pendingProductReviews'])
    print('Verified five Disney/Star Wars NOW single-card backfills: exact subjects, sale dates, labelled runs, seven foil parallels, literal conditional thresholds, separate product families, isolated Tim Allen/Tom Hanks/Pedro Pascal/Sam Witwer terms and blank card numbers; no complete-history or pack-odds claim.')

bundesliga_source=root/'data/catalog-sources/topps-now-backfill-browser-20261018-0200-bundesliga.json'
if bundesliga_source.exists():
    retained=json.loads(bundesliga_source.read_text());assert len(retained['products'])==3
    by_url={p['source']:p for p in observations}
    expected=[('145','Patrice Čović','742','2026-03-10','Mar 17, 2026','SV Werder Bremen'),('132','Arijon Ibrahimović','115','2026-02-23','Mar 2, 2026','1. FC Heidenheim 1846'),('131','Fábio Silva','295','2026-02-23','Mar 2, 2026','Borussia Dortmund')]
    cards=[]
    for product,(number,subject,print_run,start,end,properties) in zip(retained['products'],expected):
        lines=[line.strip() for line in product['lines']]
        fields=dict(line.split('  | ',1) for line in lines if '  | ' in line)
        card=by_url[product['url']];cards.append(card)
        assert card['series']=='2025-26 Bundesliga Topps NOW®' and card['number']==number
        assert card['name']==subject==fields['Subjects'] and card['printRun']==print_run
        assert card['saleFromISO']==start and card['saleUntil']==end
        assert card['saleFrom']==fields['Available From'] and card['saleUntil']==fields['Available Until']
        assert card['evidence']['fields']==fields and fields['Properties']==properties
        assert card['evidence']['title']==lines[0] and subject+'- 2025-26' in lines[0]
        assert card['evidence']['sha256']==hashlib.sha256('\n'.join(lines).encode()).hexdigest()
        assert card['parallels']==['/50 Gold Foil','/25 Orange Foil','/10 Black Foil','/5 Red Foil','/1 FoilFractor']
        for line in lines:
            if line.startswith('* ') or re.match(r'^[\d,]+\+ Print Run:',line):assert line.removeprefix('* ') in card['terms']
        assert 'Numeric pack odds are not published.' in card['terms']
        assert 'Autograph' not in card['terms']
    listing={'listings':[{'reportedProductCount':3,'products':[{'url':p['source'],'title':p['evidence']['title']} for p in cards]}]}
    aggregate=json.loads((root/'data/imports/topps-now-2026.json').read_text())
    assert all(p['status']=='published' for p in reconcile(listing,observations,aggregate))
    gaps=json.loads((root/'data/topps-now-import-gaps.json').read_text())
    assert not {p['source'] for p in cards} & {p['url'] for p in gaps['unparsedNumberedTitles']}
    assert any('Chase Burns' in p['title'] for p in gaps['unparsedNumberedTitles']),'Conflicting double-PR text must remain unresolved'
    entry=next(s for s in inventory if s['title']=='2025-26 Bundesliga Topps NOW®')
    assert entry['sport']=='soccer' and entry['rowCount']>=102 and not entry['coverageComplete']
    print('Verified Bundesliga NOW 131/132/145: literal missing-space titles, printed numbers, accented Subjects, February/March sale dates, runs295/115/742, five foil terms and conditional thresholds; no URL-derived facts or pack odds.')
