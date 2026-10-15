"""Import Chrome Black Baseball physical subject cells, odds and exact guide limits."""
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from import_official_catalog import run
from import_topps_tribute_2026 import acquire, text
from official_odds_layout import physical_odds_pdf

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-chrome-black-baseball'
PARSER='scripts/import_topps_chrome_black_baseball_2026.py'
PROOF=ROOT/'data/parallel-audit-sources/chrome-black-baseball-2026-guide-20261015.json'
FAMILIES={'BASE CARDS','BASE ROOKIE DESIGN VARIATION','DAMASCUS','NOCTURNAL','DEPTH OF DARKNESS','HOME FIELD',
 'AUTOGRAPHS','IVORY AUTOGRAPHS','PITCH BLACK PAIRINGS DUAL AUTOGRAPHS','SUPER FUTURES AUTOGRAPHS','PAINT IT'}

def read_cards(path):
    rows,raw,notes=[],[],[];family=None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==11
        for pn,page in enumerate(pdf.pages,1):
            raw.append({'page':pn,'text':page.extract_text()})
            groups=[]
            for c in page.chars:
                y=c['matrix'][5];cs=next((cs for baseline,cs in groups if abs(y-baseline)<.6),None)
                if cs is None:cs=[];groups.append((y,cs))
                cs.append(c)
            for y,cs in sorted(groups,reverse=True):
                line=text(cs)
                if not line:continue
                if pn==1 and family is None and line not in FAMILIES:
                    notes.append([str(pn),line]);continue
                if line in FAMILIES:family=line;continue
                if line in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPH RELIC'}:continue
                number=text([c for c in cs if c['x0']<130])
                name=text([c for c in cs if 130<=c['x0']<269])
                team=text([c for c in cs if 269<=c['x0']<410])
                rookie=text([c for c in cs if c['x0']>=410])
                assert family and re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and name and team and rookie in {'','Rookie'},(pn,line,number,name,team,rookie)
                rows.append([family,number,name,team,rookie,str(pn)])
    assert len(rows)==556 and len({r[0] for r in rows})==11,(len(rows),len({r[0] for r in rows}))
    assert {int(r[1]) for r in rows if r[0]=='BASE CARDS'}==set(range(1,201))
    return rows,raw,notes

def build():
    proof=json.loads(PROOF.read_text());proof_hash=hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence=dict(source=proof['source'],evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=proof_hash)
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
    digest=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');odds_hash=acquire(proof['oddsUrl'],op)
    odds,formats,odds_raw,issues=physical_odds_pdf(op)
    assert len(odds)==68 and formats==['Hobby'] and not issues
    aliases={f.title():f for f in FAMILIES}
    aliases.update({'Base Card Rookie Design Variation':'BASE ROOKIE DESIGN VARIATION',
                    'Chrome Black Autograph Cards':'AUTOGRAPHS','Paint It!':'PAINT IT',
                    'Pitch Black Dual Pairing Autographs':'PITCH BLACK PAIRINGS DUAL AUTOGRAPHS',
                    'Super Future Autographs':'SUPER FUTURES AUTOGRAPHS'})
    for odd in odds:
        matches=[k for k in aliases if odd['name'].casefold()==k.casefold() or odd['name'].casefold().startswith(k.casefold()+' ')]
        assert matches,odd['name'];odd['family']=aliases[max(matches,key=len)]
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text())
    record=next((r for r in catalog['sets'] if r['slug']==SLUG),None)
    if record is None:
        record=dict(title='2026 Topps Chrome Black Baseball',manufacturer='Topps / Bowman',sport='baseball',year='2026',
                    slug=SLUG,page='sets/'+SLUG+'.html',sourcePage=proof['productSource'],checklistUrl=proof['checklistUrl'],
                    oddsUrl=proof['oddsUrl'],releaseStatus='Released',releaseDate=proof['releaseDate'],verified=proof['observed'],
                    catalogEvidence=proof['releaseEvidence'])
        record=run(record)
        assert record.get('tableData');catalog['sets'].append(record)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    note=('All 556 printed subject rows / 542 family-card identities across 11 sections retain physical Name, Team and Rookie cells, '
          'including 200 base numbers, 30 selected rookie-design variation numbers and 203 literal Rookie marks. Dual autographs '
          'retain both signer rows and original team values, including different clubs on PDPA-WW. No missing flags or team updates '
          'are inferred. All 68 categories retain literal Hobby ratios with unpublished units. Thirty exact guide specifications '
          'include 21 base limits and nine named insert/autograph limits; Blue and Green Mini Diamond base entries have no published '
          'odds and remain specification-only. Base limits never number rookie design variations or ordinary autographs. '
          'The guide announces April 29, 2026 arrival. Damascus has 30 checklist rows versus 31 in the guide, and Paint It has 19 '
          'versus 20; no subjects are added. Other numbering ladders remain unverified.')
    data.update(headers=['Checklist section','Card number','Name','Team','Rookie','Source page'],rows=rows,
                originalSubjectHeaders=['Checklist section','Card number','Name','Team','Rookie','Source page'],
                originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,
                importKind='topps-grid-pdf',dedicatedParser=PARSER,sectionColumn=0,odds=odds,formats=formats,
                oddsSource=proof['oddsUrl'],oddsRawPages=odds_raw,oddsSha256=odds_hash,oddsIssues=[],oddsParser='scripts/official_odds_layout.py',
                formatNamesPublished=True,oddsUnitsPublished=False,
                publishedSpecifications=[dict(name='Manufacturer Hobby box contents',worksheet='Official guide; box contents are not odds',
                  headers=['Published field','Published value'],rows=proof['boxContents'],**dict(evidence,source=proof['productSource'])),
                  dict(name='Official guide checklist-count reconciliation',worksheet='Guide counts; discrepancies retained',
                  headers=['Published scope','Guide count'],rows=proof['guideCounts'],**evidence)],
                sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(rowCount=len(rows),sections=11,importKind=data['importKind'],dedicatedParser=PARSER,sha256=digest,odds=68,formats=1,
                  oddsParser=data['oddsParser'],oddsImportIssues=0,verified=proof['observed'],catalogEvidence=note,dataAudit=note,
                  releaseSource=proof['source'],releaseEvidence=proof['releaseEvidence'],
                  sourceObservation=dict(file=evidence['evidenceFile'],sha256=proof_hash,source=proof['productSource']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text())
    inventory=[record if r['slug']==SLUG else r for r in inventory]
    if not any(r['slug']==SLUG for r in inventory):inventory.append(record)
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    oddsp=ROOT/'data/topps-official-odds.json';odds_inventory=json.loads(oddsp.read_text())
    # Preserve previously observed global catalog records verbatim.
    if not any(o['url']==proof['oddsUrl'] and o.get('sha256')==odds_hash for o in odds_inventory):
        odds_inventory.append(dict(title=record['title'],url=proof['oddsUrl'],source=proof['productSource'],sha256=odds_hash))
    oddsp.write_text(json.dumps(odds_inventory,ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text())
    specs=[]
    for name,number,odd in proof['baseNumbering']:
        spec=dict(family='BASE CARDS',name=name,numbering=number,
                  qualification='Sequential numbering published for the base family only; not applied to rookie design variations, inserts or autographs.',**evidence)
        if odd:
            assert any(o['name']==odd and o['family']=='BASE CARDS' for o in odds);spec['oddsName']=odd
        else:spec['qualification']+=' Named in the guide but absent from the odds sheet; no odds are inferred.'
        specs.append(spec)
    for family,name,number,odd in proof['otherNumbering']:
        assert any(o['name']==odd and o['family']==family for o in odds)
        specs.append(dict(family=family,name=name,numbering=number,oddsName=odd,
                          qualification='Published for this exact named family and parallel; individual-subject eligibility is not inferred.',**evidence))
    assert len(specs)==30
    registry['sets'][SLUG]=specs
    family='Guide counts and incomplete numbering coverage'
    registry['conflicts']=[c for c in registry['conflicts'] if not(c['slug']==SLUG and c['family']==family)]
    registry['conflicts'].append(dict(slug=SLUG,family=family,gap=' '.join(proof['remainingGaps'][:4]),**evidence))
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Chrome Black Baseball: 556 subject rows, 542 identities, 203 Rookie flags, 68 literal Hobby ratios, 30 source-scoped numbering specifications.')

if __name__=='__main__':build()
