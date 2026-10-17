"""Retain physical McDonald's player/designation cells and literal Hobby odds."""
import collections, hashlib, json, re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire, text
from official_odds_layout import physical_odds_pdf

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2025-topps-chrome-mcdonald-s-all-american-basketball'
PARSER = 'scripts/import_topps_mcdonalds_2025.py'
PROOF = ROOT/'data/parallel-audit-sources/mcdonalds-basketball-2025-20261016.json'
HEADERS = ['Checklist section', 'Card number', 'Name', 'Source page', 'Published East/West designation']
FAMILIES = {'BASE CARDS':100, 'HIGH RISES':38, 'TOP RECRUITS':32, 'PROSPECT PATHS':20,
    'HYPE TO LEGACY':10, 'ALL AMERICAN DRIP':10, 'CONCRETE CANVAS':20, 'BILLBOARD INK':38,
    'LEGENDS AUTOGRAPHS':18, 'WINNING TAGS':38, 'EVENT AUTOGRAPHS':38, 'GOLDEN PATCH AUTOGRAPHS':38}

def read_cards(path):
    rows=[]; raw=[]; notes=[]; family=None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==9
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text())); groups=collections.defaultdict(list)
            for c in page.chars: groups[round(c['top'],2)].append(c)
            for y,cs in sorted(groups.items()):
                line=text(cs)
                if line=='Checklist is Subject to change':
                    notes.append([str(pn),line]); continue
                if all('Bold' in c['fontname'] for c in cs):
                    if line in {'INSERT','AUTOGRAPH','AUTOGRAPH RELIC'}: notes.append([str(pn),line])
                    else:
                        assert line in FAMILIES,(pn,line)
                        family=line
                    continue
                # Original text-object starts separate adjacent cells without
                # guessing where the subject's name ends or assigning NBA teams.
                a=next(i for i,c in enumerate(cs) if abs(c['x0']-233.09)<.02)
                b=next(i for i,c in enumerate(cs) if abs(c['x0']-370.63)<.02)
                number,name,designation=[text(part) for part in [cs[:a],cs[a:b],cs[b:]]]
                assert family and re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and name and designation in {'East','West'},(pn,line)
                rows.append([family,number,name,str(pn),designation])
    assert len(rows)==len({tuple(r[:2]) for r in rows})==400
    assert collections.Counter(r[0] for r in rows)==FAMILIES
    assert collections.Counter(r[4] for r in rows)=={'East':183,'West':217}
    return rows,raw,notes

def build():
    proof=json.loads(PROOF.read_text()); sources=proof['sources']
    evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
    cp=ROOT/'data/set-catalog.json'; catalog=json.loads(cp.read_text())
    record=next(s for s in catalog['sets'] if s['slug']==SLUG); dp=ROOT/record['tableData']; data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
    sha=acquire(proof['checklistUrl'],path); rows,raw,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf'); oh=acquire(proof['oddsUrl'],op)
    original,formats,odds_raw,issues=physical_odds_pdf(op)
    assert (sha,oh)==(proof['checklistSha256'],proof['oddsSha256'])
    assert len(original)==73 and formats==['Hobby'] and not issues
    # The product and landing links have different cache parameters, but the
    # actual refreshed bytes must agree before their evidence is combined.
    product_path=path.with_name(SLUG+'-product-odds.pdf')
    assert acquire(proof['productOddsUrl'],product_path)==oh==proof['productOddsSha256']
    aliases={f.title():f for f in FAMILIES}
    aliases.update({'Base':'BASE CARDS','All-American Drip':'ALL AMERICAN DRIP','Event Autogrpahs':'EVENT AUTOGRAPHS'})
    refractor_base={'BILLBOARD INK','LEGENDS AUTOGRAPHS','WINNING TAGS'}; odds=[]
    for item in original:
        prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None)
        assert prefix,item['name']; family=aliases[prefix]
        odds.append(dict(item,family=family,familyBase=item['name'].casefold()==(prefix+(' Refractor' if family in refractor_base else '')).casefold()))
    assert {o['family'] for o in odds}==set(FAMILIES)-{'CONCRETE CANVAS'}
    table=lambda name,headers,values,source:dict(name=name,headers=headers,rows=values,source=source,
        worksheet='Official manufacturer evidence; retain source scope and original units',**evidence)
    published=[table('Manufacturer product fields',['Published field','Published value','Scope'],proof['productFields'],sources['product']),
        table('Guide-described checklist sizes',['Checklist family','Published size'],proof['guideCounts'],sources['guide']),
        table('Unscoped product parallel descriptions',['Parallel / variation','Qualification'],proof['parallelDescriptions'],sources['product'])]
    note=('All 400 original rows / 12 sections are reconciled to physical Name and East/West cell origins, with all 100 base numbers. '
        'East/West designations remain separate from NBA teams; no rookie field is published. Original ZAKiyah / ZaKiyah / Zakiyah and Lebron / LeBron spellings remain unchanged. '
        'All 73 Hobby categories retain literal values, including Base 9:1 and Event Autogrpahs. The header does not state a ratio unit. '
        'Concrete Canvas has no published odds join. The official guide explicitly confirms March 12, 2026 release, separately from the 2025 title and store Product Year 2026. '
        'Product parallel names have no numeric ladder; exhaustive numbering remains unverified.')
    data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,
        unclassifiedLines=[],source=proof['checklistUrl'],sha256=sha,dedicatedParser=PARSER,importKind='pdf',coverageComplete=True,sectionColumn=0,
        odds=odds,formats=formats,officialOddsTable=original,officialOddsFormats=formats,officialOddsHeader=['Card','Hobby'],
        oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=issues,oddsParser='scripts/official_odds_layout.py',
        formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=published,
        supplementaryOddsSources=[dict(url=proof['productOddsUrl'],sha256=oh,qualification='Fresh product-linked odds bytes match the landing/global PDF.')],
        sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(sourcePage=sources['landing'],rowCount=400,sections=12,sha256=sha,dedicatedParser=PARSER,coverageComplete=True,odds=73,formats=1,
        oddsParser='scripts/official_odds_layout.py',oddsImportIssues=0,verified=proof['observed'],dataAudit=note,catalogEvidence=note,
        sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=sources['guide']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json'; inventory=json.loads(ip.read_text())
    inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record]
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json'; registry=json.loads(rp.read_text()); registry['sets'][SLUG]=[]
    registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Unscoped parallel descriptions and unjoined odds',
        gap=' '.join(proof['remainingGaps']),source=sources['history'],**evidence)]
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('McDonald’s Basketball: 400 original subjects / 12 sections, separate East/West designations and 73 literal Hobby odds; no inferred teams, rookie flags or serial ladder.')

if __name__=='__main__': build()
