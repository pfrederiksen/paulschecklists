"""Import Midnight Basketball's physical cells and unlabelled literal odds."""
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from import_official_catalog import run
from import_topps_tribute_2026 import acquire, text
from official_odds_layout import physical_odds_pdf

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2025-26-topps-midnight-basketball'
PARSER='scripts/import_topps_midnight_basketball.py'
PROOF=ROOT/'data/parallel-audit-sources/midnight-basketball-2025-26-guide-20261015.json'
FAMILIES={'BASE CARDS','ROOKIE JERSEY AUTOGRAPHS','STROKE OF MIDNIGHT AUTOGRAPHS',
 'STROKE OF MIDNIGHT AUTOGRAPHS ROOKIES','ROOKIE HORIZON SIGNATURES','MIDNIGHT SUN SIGNATURES',
 'MIDNIGHT SUN SIGNATURES ROOKIES','DARK MARKS','DARK MARKS ROOKIES','DARK MATTER AUTOGRAPHS',
 'DARK MATTER AUTOGRAPHS ROOKIES','MIDNIGHT OIL MARKS','MIDNIGHT OIL MARKS ROOKIES',
 'STROKE OF MIDNIGHT AUTOGRAPHS II','NIGHT OWLS','DAYDREAMERS','INSOMNIA','MOONFALL','NIGHT SHADE',
 'DREAMLAND','NIGHT VISION','TWILIGHT'}

def read_cards(path):
    rows,raw=[],[];family=None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==13
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
                if line in FAMILIES:family=line;continue
                if line in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPH RELIC'}:continue
                number=text([c for c in cs if c['x0']<130])
                name=text([c for c in cs if 130<=c['x0']<270])
                team=text([c for c in cs if 270<=c['x0']<410])
                rookie=text([c for c in cs if c['x0']>=410])
                assert family and re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and name and team and rookie in {'','Rookie'},(pn,line,number,name,team,rookie)
                rows.append([family,number,name,team,rookie,str(pn)])
    assert len(rows)==593 and len({r[0] for r in rows})==22,(len(rows),len({r[0] for r in rows}))
    assert {int(r[1]) for r in rows if r[0]=='BASE CARDS'}==set(range(1,101))
    return rows,raw

def build():
    proof=json.loads(PROOF.read_text());proof_hash=hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence=dict(source=proof['source'],evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=proof_hash)
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
    digest=acquire(proof['checklistUrl'],path);rows,raw=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');odds_hash=acquire(proof['oddsUrl'],op)
    odds,formats,odds_raw,issues=physical_odds_pdf(op)
    assert len(odds)==219 and formats==['Published odds (format not named)'] and not issues
    aliases={f.title():f for f in FAMILIES}
    aliases.update({'Base':'BASE CARDS','Nightshade':'NIGHT SHADE'})
    for odd in odds:
        matches=[k for k in aliases if odd['name'].casefold()==k.casefold() or odd['name'].casefold().startswith(k.casefold()+' ')]
        assert matches,odd['name'];odd['family']=aliases[max(matches,key=len)]
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text())
    record=next((r for r in catalog['sets'] if r['slug']==SLUG),None)
    if record is None:
        record=dict(title='2025-26 Topps Midnight Basketball',manufacturer='Topps / Bowman',sport='basketball',year='2025-26',
                    slug=SLUG,page='sets/'+SLUG+'.html',sourcePage=proof['productSource'],checklistUrl=proof['checklistUrl'],
                    oddsUrl=proof['oddsUrl'],releaseStatus='Released',releaseDate=proof['releaseDate'],verified=proof['observed'],
                    catalogEvidence=proof['releaseEvidence'])
        record=run(record)
        assert record.get('tableData');catalog['sets'].append(record)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    note=('All 593 printed subject rows across 22 sections retain their physical Name, Team and Rookie cells, including '
          'all 100 base numbers. Historical team assignments, accents, literal Minnesota Tmberwolves and Karl Anthony-Towns '
          'spellings are retained without correction. All 219 odds categories retain their literal unlabelled ratios; '
          'the PDF names neither format nor unit, so separate box configuration does not turn them into per-pack odds. '
          'The NIGHT SHADE / Nightshade spelling alias is exact and family-specific. The official January 12 guide '
          'confirms January 29, 2026 release despite the 2025-26 product label. Neither checked official page publishes '
          'a named numbering ladder; serial limits and exhaustive parallel numbering remain unverified.')
    data.update(headers=['Checklist section','Card number','Name','Team','Rookie','Source page'],rows=rows,
                originalSubjectHeaders=['Checklist section','Card number','Name','Team','Rookie','Source page'],
                originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=[],unclassifiedLines=[],sha256=digest,
                importKind='topps-grid-pdf',dedicatedParser=PARSER,sectionColumn=0,odds=odds,formats=formats,
                oddsSource=proof['oddsUrl'],oddsRawPages=odds_raw,oddsSha256=odds_hash,oddsIssues=[],oddsParser='scripts/official_odds_layout.py',
                formatNamesPublished=False,oddsUnitsPublished=False,
                publishedSpecifications=[dict(name='Manufacturer Hobby box contents',worksheet='Official guide; box contents are not odds',
                  headers=['Published field','Published value'],rows=proof['boxContents'],**evidence)],
                sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(rowCount=len(rows),sections=22,importKind=data['importKind'],dedicatedParser=PARSER,sha256=digest,odds=219,formats=1,
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
    family='Unverified numbering ladder and unlabelled odds units'
    registry['conflicts']=[c for c in registry['conflicts'] if not(c['slug']==SLUG and c['family']==family)]
    registry['conflicts'].append(dict(slug=SLUG,family=family,gap=' '.join(proof['remainingGaps'][:2]),**evidence))
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print(f'Midnight Basketball: {len(rows)} rows, 22 sections, {sum(r[4]=="Rookie" for r in rows)} Rookie flags, 219 unlabelled odds categories. Numbering audit remains incomplete.')

if __name__=='__main__':build()
