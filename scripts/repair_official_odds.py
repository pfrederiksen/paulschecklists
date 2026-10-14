"""Repair malformed odds headings/categories without replacing checklist imports."""
import collections, concurrent.futures, hashlib, json, re, subprocess
from pathlib import Path
import pdfplumber
from official_odds_layout import physical_odds_pdf

ROOT = Path(__file__).resolve().parents[1]
PARSER = 'scripts/official_odds_layout.py'
LITERAL = r'[\d,.]+(?::[\d,.]+)+'

def prepare(record):
    path = ROOT / 'data/catalog-sources/downloads' / (record['slug'] + '-odds.pdf')
    temporary = path.with_suffix('.refresh.pdf')
    subprocess.run(['curl', '-sLf', '--retry', '2', '--max-time', '30', record['oddsUrl'], '-o', str(temporary)], check=True)
    assert temporary.read_bytes().startswith(b'%PDF')
    temporary.replace(path)
    entries, formats, raw, issues = physical_odds_pdf(path)
    assert not issues and entries and formats
    with pdfplumber.open(path) as pdf:
        original = collections.Counter(w['text'] for page in pdf.pages for w in page.extract_words() if re.fullmatch(LITERAL, w['text']))
    imported = collections.Counter(value for row in entries for value in row['values'].values() if value)
    assert original == imported, (record['slug'], original-imported, imported-original)
    return entries, formats, raw, hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    catalog_path = ROOT / 'data/set-catalog.json'
    catalog = json.loads(catalog_path.read_text())
    registry = json.loads((ROOT / 'data/parallel-specifications.json').read_text())
    targets = []
    for record in catalog['sets']:
        if not record.get('oddsUrl'):
            continue
        data = json.loads((ROOT / record['tableData']).read_text())
        names = [o['name'] for o in data['odds']]
        malformed = any(len(f) > 100 or f.startswith('Official column') for f in data['formats']) or len(names) > 1 and len(set(names)) < len(names)*.7
        if malformed and data.get('oddsParser') != PARSER:
            targets.append(record)
    # Downloads/parsing are independent. Apply validated changes serially.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        prepared = list(pool.map(prepare, targets))
    for record, (entries, formats, raw, fingerprint) in zip(targets, prepared):
        data_path = ROOT / record['tableData']
        data = json.loads(data_path.read_text())
        names = {entry['name'] for entry in entries}
        for specification in registry['sets'].get(record['slug'], []):
            assert not specification.get('oddsName') or specification['oddsName'] in names, ('Reconcile the approved exact guide join before importing', record['slug'], specification)
        old_by_name = {entry['name']: entry for entry in data['odds']}
        if fingerprint == data['oddsSha256']:
            for entry in entries:
                old = old_by_name.get(entry['name'], {})
                for field in ['family', 'familyAliases', 'numbering', 'numberingSource', 'qualification']:
                    if field in old:
                        entry[field] = old[field]
        data.update(odds=entries, formats=formats, oddsRawPages=raw, oddsSha256=fingerprint, oddsIssues=[], oddsParser=PARSER)
        if formats == ['Published odds (format not named)']:
            data.update(formatNamesPublished=False, oddsUnitsPublished=False)
            note = 'The official odds document does not print a format heading or define the ratio unit. Ratios are retained verbatim; no named pack configuration or hit-rate estimate is inferred.'
            if note not in record.get('catalogEvidence', ''):record['catalogEvidence'] = record.get('catalogEvidence', '') + ' ' + note
        unusual = sorted({v for entry in entries for v in entry['values'].values() if v and not re.fullmatch(r'[\d,]+:[\d,]+', v)})
        if unusual:
            data['oddsLiteralNotes'] = ['Some published odds use three-part or period-separated notation. These values are retained verbatim; no numeric hit-rate estimate is inferred.']
            note = data['oddsLiteralNotes'][0]
            if note not in record.get('catalogEvidence', ''):
                record['catalogEvidence'] = record.get('catalogEvidence', '') + ' ' + note
        data_path.write_text(json.dumps(data, ensure_ascii=False) + '\n')
        record.update(odds=len(entries), formats=len(formats), oddsImportIssues=0, oddsParser=PARSER)
        print(record['title'], len(entries), 'published categories;', len(formats), 'literal format headings;', len(unusual), 'unusual source values retained')
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    # Keep product-specific adapters and their checklist markers intact.
    inventory_path = ROOT / 'data/topps-product-official-catalog.json'
    inventory = json.loads(inventory_path.read_text())
    replacements = {record['slug']: record for record in targets}
    inventory = [replacements.get(record['slug'], record) for record in inventory]
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    print('Repaired', len(targets), 'sets without replacing their card rows or dedicated checklist parsers.')

if __name__ == '__main__':
    build()
