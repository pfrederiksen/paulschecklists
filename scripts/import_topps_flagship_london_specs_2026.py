"""Reconcile London-only paper base guide terms with exact original odds captions."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-flagship-football'
PROOF = ROOT / 'data/parallel-audit-sources/flagship-football-london-2026-20261020.json'


def apply_specs():
    proof = json.loads(PROOF.read_text())
    digest = hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence = dict(evidenceFile=str(PROOF.relative_to(ROOT)), evidenceSha256=digest)
    cp = ROOT / 'data/set-catalog.json'
    catalog = json.loads(cp.read_text())
    record = next(r for r in catalog['sets'] if r['slug'] == SLUG)
    dp = ROOT / record['tableData']
    data = json.loads(dp.read_text())
    assert data['sha256'] == proof['checklist']['sha256']
    assert data['oddsSha256'] == proof['odds']['sha256']
    assert len(data['rows']) == 4082 and len(data['odds']) == 1097 and len(data['formats']) == 20
    before = data['rows'], data['odds'], data['formats'], data['sha256'], data['oddsSha256']
    families = set(proof['checklist']['paperBaseFamilies'])
    paper = [r for r in data['rows'] if r[0] in families]
    assert len(paper) == 420 and {int(r[1]) for r in paper} == set(range(1, 401))
    specs = []
    for term in proof['approvedSpecifications']:
        assert term['family'] in families
        assert any(o['name'] == term['oddsName'] for o in data['odds'])
        specs.append(dict(term, source=proof['url'], sourceHeading='London Store Exclusive FAQs: exclusive base parallels and checklist equivalence',
                          qualification='London Store Exclusive Mega Box paper base program only; individual-card parallel eligibility is not guaranteed. No other regular, Chrome, insert, autograph or relic program inherits this limit.',
                          **evidence))
    assert len(specs) == 30
    name = 'Manufacturer London Store Exclusive scope'
    data['publishedSpecifications'] = [s for s in data.get('publishedSpecifications', []) if s['name'] != name] + [
        dict(name=name, worksheet='London store edition; preserve regional and program scope',
             headers=['Published field', 'Published value', 'Source qualification'], rows=proof['contextRows'],
             source=proof['url'], **evidence)]
    data['londonGuideEvidence'] = dict(file=evidence['evidenceFile'], sha256=digest, source=proof['url'])
    assert before == (data['rows'], data['odds'], data['formats'], data['sha256'], data['oddsSha256'])
    dp.write_text(json.dumps(data, ensure_ascii=False) + '\n')
    rp = ROOT / 'data/parallel-specifications.json'
    registry = json.loads(rp.read_text())
    registry['sets'][SLUG] = specs
    rp.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
    record['londonGuideEvidence'] = data['londonGuideEvidence']
    record['dataAudit'] = ('All 4,171 printed subject rows / 4,082 numbered rows, 87 sections and 1,097 original 20-column odds remain unchanged. '
                           'The London Store Exclusive guide reconciles five paper base parallel programs across the same 400 base numbers: Big Ben /59, Tudor Rose /5 and Crown Jewels 1/1; both Union Jack foils have numbering unstated. '
                           'The London store on-sale wording is separate from the regular August 21 release. Chrome, variations, inserts, autographs and relics inherit no London base limits; exhaustive numbering remains incomplete.')
    cp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    ip = ROOT / 'data/topps-product-official-catalog.json'
    inventory = json.loads(ip.read_text())
    inventory = [record if r['slug'] == SLUG else r for r in inventory]
    if not any(r['slug'] == SLUG for r in inventory):
        inventory.append(record)
    ip.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    print('London Flagship: 30 exact paper-base guide joins, 18 numbered scopes; all physical rows, odds and dates preserved.')


if __name__ == '__main__':
    apply_specs()
