"""Apply only exact guide scopes; quantities never become serial-number claims."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-star-wars-chrome-galaxy'
PROOF=ROOT/'data/parallel-audit-sources/star-wars-galaxy-guides-20261020-1700.json'

def apply_specs():
    proof=json.loads(PROOF.read_text());digest=hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=digest)
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text())
    record=next(r for r in catalog['sets'] if r['slug']==SLUG)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    before=data['sha256'],data['oddsSha256'],data['rows'],data['odds']
    assert len(data['rows'])==584 and len(data['odds'])==110
    for spec in proof['approvedNumbering']:
        assert any(o['name']==spec['oddsName'] for o in data['odds'])
    collector=proof['guides'][1]['url'];hobby=proof['guides'][0]['url']
    additions=[
      dict(name='BASE CARDS',worksheet='Base-only guide quantity; serial marking not stated',headers=['Published parallel','Published quantity','Qualification'],rows=proof['baseQuantityRows'],source=collector,**evidence),
      dict(name='GALAXY AUTOGRAPHS',worksheet='Named Pedro Pascal card only; no color or serial marking stated',headers=['Card number','Actor','Character','Published parallel example','Published quantity','Qualification'],rows=proof['cardQuantityRows'],source=collector,**evidence),
      dict(name='TRIPLE AUTOGRAPHS',worksheet='Named triple-card example only; not a family-wide serial limit',headers=['Card number','Signers','Characters','Published statement','Qualification'],rows=proof['tripleExampleRows'],source=hobby,**evidence),
      dict(name='Manufacturer Hobby configuration',worksheet='Original pack, box and case units; not calculated pack odds',headers=['Published field','Published value','Unit'],rows=proof['boxConfigurationRows'],source=hobby,**evidence)]
    names={r['name'] for r in additions};data['publishedSpecifications']=[r for r in data.get('publishedSpecifications',[]) if r['name'] not in names]+additions
    data.pop('includePublishedSpecifications',None)
    data['parallelGuideEvidence']=dict(file=evidence['evidenceFile'],sha256=digest,sources=[hobby,collector])
    for sheet in data.get('sourceSheets',[]):
        for row in sheet.get('notes',[]):
            if row and row[0]=='Parallel audit':row[1]='Fresh official Hobby and Collector guides confirm only the base SuperFractor 1/1. Base Red LogoFractor and named Pedro Pascal five-copy claims retain unstated serial marking. The triple-card example and case distributions remain qualified. Exhaustive parallel eligibility and numbering remain incomplete.'
    assert before==(data['sha256'],data['oddsSha256'],data['rows'],data['odds'])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    note=('All 366 numbered subject rows and 218 unnumbered sketch-artist entries retain original physical cells and all 110 literal Hobby odds. '
      'Fresh official guides map base SuperFractor 1/1 only. Base Red LogoFractor and GA-PP Pedro Pascal five-copy quantities have unstated serial marking; '
      'the named T-EP6 triple example is not a family-wide serial limit. Pack/box/case distributions retain their original units. '
      'August 12 store availability and guide publication dates do not establish a general release date. Exhaustive parallel numbering remains incomplete.')
    record.update(dataAudit=note,catalogEvidence=note,parallelGuideEvidence=data['parallelGuideEvidence'])
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory]
    if not any(r['slug']==SLUG for r in inventory):inventory.append(record)
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=[dict(spec,**evidence) for spec in proof['approvedNumbering']]
    registry['conflicts']=[r for r in registry['conflicts'] if not (r['slug']==SLUG and r.get('family')=='Incomplete guide numbering inventory')]
    registry['conflicts'].append(dict(slug=SLUG,family='Incomplete guide numbering inventory',gap=' '.join(proof['remainingGaps']),source=hobby,**evidence))
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Galaxy: one base-only 1/1 mapping, two five-copy quantity scopes, one named triple example and original case/box units; source rows and odds unchanged.')

if __name__=='__main__':apply_specs()
