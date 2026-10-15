"""Import the official product-page-only Pristine checklist and pack odds."""
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from import_official_catalog import run
from import_topps_tribute_2026 import acquire, text
from official_odds_layout import physical_odds_pdf

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-pristine-baseball'
PARSER='scripts/import_topps_pristine_2026.py'
PROOF=ROOT/'data/parallel-audit-sources/pristine-baseball-2026-guide-20261015.json'
FAMILIES={'BASE CARDS I','PRISTINE WILDERNESS','PLATED AND POLISHED','SPOTLESS','PEARLESCENT','AMPED','RUSHMORE',
          'PRISTINE POPS','MONOGRAM','TIMELESS CONNECTIONS','PRISTINE AUTOGRAPHS','PRISTINE PAIR DUAL AUTOGRAPHS',
          'SPOTLESS SIGNATURES','PRISTINE PERSONAL ENDORSEMENTS AUTOGRAPHS','ITALICS','POPULAR DEMAND AUTOGRAPH RELIC',
          'PRISTINE PIECES AUTOGRAPH RELIC','ROOKIE JUMBO RELIC AUTOGRAPHS'}

def read_cards(path):
    rows,raw,notes=[],[],[];family=None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==15
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
                name=text([c for c in cs if 130<=c['x0']<265])
                team=text([c for c in cs if 265<=c['x0']<410])
                rookie=text([c for c in cs if c['x0']>=410])
                assert re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and name and team and rookie in {'','Rookie'},(pn,line)
                rows.append([family,number,name,team,rookie,str(pn)])
    assert len(rows)==729 and len({r[0] for r in rows})==18
    assert sum(r[4]=='Rookie' for r in rows)==224
    assert {int(r[1]) for r in rows if r[0]=='BASE CARDS I'}==set(range(1,201))
    return rows,raw,notes

def build():
    proof=json.loads(PROOF.read_text());proof_hash=hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence=dict(source=proof['source'],evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=proof_hash)
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text())
    record=next((r for r in catalog['sets'] if r['slug']==SLUG),None)
    if record is None:
        record=dict(title='2026 Topps Pristine Baseball',manufacturer='Topps / Bowman',sport='baseball',year='2026',
                    slug=SLUG,page='sets/'+SLUG+'.html',sourcePage=proof['productSource'],checklistUrl=proof['checklistUrl'],
                    oddsUrl=proof['oddsUrl'],releaseStatus='Unverified',releaseDate=None,verified=proof['observed'],
                    catalogEvidence='The official 2026 product page links the checklist and odds; an exact calendar release date is not verified.')
        record=run(record)
        assert record.get('tableData')
        catalog['sets'].append(record)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
    digest=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');odds_hash=acquire(proof['oddsUrl'],op)
    odds,formats,odds_raw,issues=physical_odds_pdf(op)
    assert len(odds)==95 and formats==['Encased Pack','Non-Encased Pack'] and not issues
    aliases={f.title():f for f in FAMILIES}
    aliases.update({'Base Cards':'BASE CARDS I','Plated & Polished':'PLATED AND POLISHED',
                    'Pristine Pieces Autograph Relics':'PRISTINE PIECES AUTOGRAPH RELIC',
                    'Popular Demand Auto Relics':'POPULAR DEMAND AUTOGRAPH RELIC',
                    'Rookie Jumbo Relic Auto':'ROOKIE JUMBO RELIC AUTOGRAPHS'})
    for odd in odds:
        matches=[k for k in aliases if odd['name'].casefold()==k.casefold() or odd['name'].casefold().startswith(k.casefold()+' ')]
        assert matches,odd['name'];odd['family']=aliases[max(matches,key=len)]
    note=('Official product-page checklist: all 729 printed subject rows / 705 family-card identities across 18 sections, '
          'all 200 base numbers and 224 literal Rookie marks are retained. Rushmore prints four subjects per card and dual '
          'autographs retain both signer rows. Source team assignments and apparent rookie errors are not corrected or propagated. '
          'All 95 odds categories preserve both literal Encased Pack / Non-Encased Pack columns, blank cells and the spelling Refactor. '
          'Guide numbering uses exact source-family joins: ten base limits, six short-print Superfractors and Pristine Autographs '
          'Green/Black. Other color limits and the qualified autograph-relic Pristine /99 wording remain unjoined. '
          'This checklist was discovered on the product page, outside the global checklist directory. Guide publication is not a release date; '
          'exhaustive parallel numbering and an exact release date remain unverified.')
    data.update(headers=['Checklist section','Card number','Name','Team','Rookie','Source page'],rows=rows,
                originalSubjectHeaders=['Checklist section','Card number','Name','Team','Rookie','Source page'],
                originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,
                importKind='topps-grid-pdf',dedicatedParser=PARSER,sectionColumn=0,odds=odds,formats=formats,
                oddsSource=proof['oddsUrl'],oddsRawPages=odds_raw,oddsSha256=odds_hash,oddsIssues=[],oddsParser='scripts/official_odds_layout.py',
                formatNamesPublished=True,oddsUnitsPublished=True,
                publishedSpecifications=[dict(name='Manufacturer Hobby box contents',worksheet='Official guide; box contents are not odds',
                  headers=['Published field','Published value'],rows=proof['boxContents'],**evidence),
                  dict(name='Qualified autograph-relic numbering',worksheet='Official guide; exact family join not published',
                  headers=['Published scope','Qualified statement'],rows=[['Pristine Pieces / Popular Demand / Rookie Jumbo autograph relics',proof['qualifiedRelicNumbering']]],**evidence)],
                sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(rowCount=729,sections=18,importKind=data['importKind'],dedicatedParser=PARSER,sha256=digest,odds=95,formats=2,
                  oddsParser=data['oddsParser'],oddsImportIssues=0,verified=proof['observed'],catalogEvidence=note,dataAudit=note,
                  sourceObservation=dict(file=evidence['evidenceFile'],sha256=proof_hash,source=proof['productSource']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text())
    inventory=[record if r['slug']==SLUG else r for r in inventory]
    if not any(r['slug']==SLUG for r in inventory):inventory.append(record)
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    oddsp=ROOT/'data/topps-official-odds.json';odds_inventory=json.loads(oddsp.read_text())
    odds_record=dict(title=record['title'],url=proof['oddsUrl'],source='https://www.topps.com/pages/odds',
                     productSource=proof['productSource'],sha256=odds_hash)
    odds_inventory=[o for o in odds_inventory if o['title']!=record['title']]
    odds_inventory.append(odds_record)
    oddsp.write_text(json.dumps(odds_inventory,ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text())
    specs=[dict(family='BASE CARDS I',name=name,numbering=number,oddsName=odd,
                qualification='Base family only; no base color limits are applied to inserts, autographs or relics.',**evidence)
           for name,number,odd in proof['baseNumbering']]
    for family in proof['shortPrintSuperfractors']:
        odd=next(o for o in odds if o['family']==family and o['name'].endswith(' Superfractor'))
        specs.append(dict(family=family,name='SuperFractor',numbering='1/1',oddsName=odd['name'],
                          qualification='Guide explicitly names this short-print SuperFractor; no individual-subject eligibility is inferred.',**evidence))
    for color,number in [('Green','/150'),('Black','1/1')]:
        name='Pristine Autographs '+color+' Pristine Refractor'
        assert any(o['name']==name for o in odds)
        specs.append(dict(family='PRISTINE AUTOGRAPHS',name=color+' Pristine Refractor',numbering=number,oddsName=name,
                          qualification='Exact Pristine Autographs category within the guide-described autograph range; other programs do not inherit this color limit.',**evidence))
    registry['sets'][SLUG]=specs
    family='Autograph relic Pristine /99 scope'
    registry['conflicts']=[c for c in registry['conflicts'] if not(c['slug']==SLUG and c['family']==family)]
    registry['conflicts'].append(dict(slug=SLUG,family=family,gap=proof['qualifiedRelicNumbering'],source=proof['source'],
                                    evidenceFile=evidence['evidenceFile'],evidenceSha256=proof_hash))
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Pristine: 729 subject rows, 705 card identities, 224 Rookie flags, 95 two-format odds categories and 18 exact numbering joins.')

if __name__=='__main__':build()
