"""Attach the product-linked F1 odds grid without flattening the ruled checklist."""
import hashlib,json,re
from pathlib import Path
from import_topps_tribute_2026 import acquire
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-chrome-formula-1'
PROOF=ROOT/'data/parallel-audit-sources/f1-2026-product-odds-20261016.json'

def enrich(data,record):
    proof=json.loads(PROOF.read_text());evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
    assert data['sha256']==proof['checklistSha256']
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],path)
    original,formats,raw,issues=physical_odds_pdf(path)
    assert oh==proof['oddsSha256'] and len(original)==174 and not issues
    assert formats==['HOBBY','FDI','SAPPHIRE','VALUE','MEGA','HONGBAO','LOGOFRACTOR']
    families=list(dict.fromkeys(r[0] for r in data['rows']));base=[f for f in families if f.startswith('BASE CARDS - ')]
    assert len(base)==12
    aliases={f:f for f in families if f not in base}
    aliases.update({'BASE':base[0],'VUELTA 1':'VUELTA 1 AUTOGRAPHS','PODIUM TRIPLES':'PODIUM TRIPLE AUTOGRAPHS','F1 DEBUT PATCH AUTOGRAPH REDEMPTIONS':'F1® DEBUT PATCH AUTOGRAPHS'})
    odds=[]
    for item in original:
        prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name']==a or item['name'].startswith(a+' ')),None)
        assert prefix,item['name']
        row=dict(item,family=aliases[prefix],familyBase=item['name']==prefix)
        if prefix=='BASE':row['familyAliases']=base[1:]
        if prefix=='BASE' and item['name']=='BASE FULL GRID REFRACTOR PARALLEL':row['qualification']='Official guide describes the current F1 driver lineup; individual-card parallel eligibility is not stated.'
        if prefix=='THE GRAIL':row['qualification']='Published odds for printed card '+item['name'].removeprefix('THE GRAIL ')+' only; not a common rate for every Grail card.'
        odds.append(row)
    specs=[dict(s,source=proof['sources'][s.pop('sourceKey')],**evidence) for s in [dict(s) for s in proof['guideSpecifications']]]
    for spec in specs:assert any(o['family']==spec['family'] and o['name']==spec['oddsName'] for o in odds)
    table=lambda name,headers,rows,source:dict(name=name,headers=headers,rows=rows,source=source,worksheet='Official format guide; retain source units and format scope',**evidence)
    # Preserve the previous product-page specifications, including original Value contents.
    # They remain set-wide context; exact numeric joins are separately hash-checked.
    data['publishedSpecifications'].extend([
        table('Official format configurations',['Format','Packs per box','Cards per pack','Boxes per case','Published box / case contents'],proof['configurations'],proof['sources']['boxGuide']),
        table('Format-scoped guide numbering without exact category joins',['Format','Published parallel / program','Published statement','Qualification'],proof['qualifiedGuideTerms'],proof['sources']['boxGuide']),
        table('Official format release dates',['Format scope','Published release date','Qualification'],proof['formatDates'],proof['sources']['boxGuide'])])
    note=('All 604 ruled checklist rows and six original source columns remain intact, including 12 blank Name cells. '
          'The product page links a four-page odds grid absent from the global catalog: all 174 categories and seven literal format columns are imported. '
          'SAPPHIRE, HONGBAO and LOGOFRACTOR have no listed ratios; retain their blank cells. The sheet does not state a ratio unit. '
          'Exact base odds aliases retain the 12 printed base subsets; Full Grid retains the guide’s current-driver-lineup qualifier without inferring individual-card eligibility. '
          'Five precise guide/product numbering joins are retained; format-specific statements without a safe category join remain qualified. '
          'The official SKU guide explicitly announces October 15, 2026 street date, with later Logofractor October 29 and Sapphire November 12 dates retained separately. Exhaustive parallel coverage remains unverified.')
    data.update(odds=odds,formats=formats,officialOddsTable=original,officialOddsFormats=formats,officialOddsHeader=['Card',*formats],oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=raw,oddsIssues=[],oddsParser='scripts/official_odds_layout.py',formatNamesPublished=True,oddsUnitsPublished=False,dedicatedParser='scripts/import_topps_f1_2026.py',coverageComplete=True,originalSubjectHeaders=data['headers'],originalSubjectRows=data['rows'],parallelSpecifications=[],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    record.update(odds=174,formats=7,oddsUrl=proof['oddsUrl'],oddsImportIssues=0,oddsParser='scripts/official_odds_layout.py',publishedOdds=True,dedicatedParser='scripts/import_topps_f1_2026.py',coverageComplete=True,verified=proof['observed'],releaseStatus='Released',catalogEvidence=note,dataAudit=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=proof['sources']['landing']))
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=specs
    registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Format scope and remaining numbering',gap=' '.join(proof['remainingGaps']),source=proof['sources']['boxGuide'],**evidence)]
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    p=ROOT/'data/topps-official-odds.json';sources=json.loads(p.read_text());item=dict(title=data['title'],url=proof['oddsUrl'],source=proof['sources']['landing'],sha256=oh)
    sources=[item if s['title']==data['title'] else s for s in sources] if any(s['title']==data['title'] for s in sources) else sources+[item]
    p.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
    return data,record
