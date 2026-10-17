"""Reconcile Cosmic Football's original cells and strictly scoped guide evidence."""
import collections, hashlib, json, re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire, text
from official_odds_layout import physical_odds_pdf

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2025-topps-cosmic-chrome-football'
PARSER='scripts/import_topps_cosmic_football_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/cosmic-football-2025-20261016.json'
HEADERS=['Checklist section','Card number','Name','Source page','Team','Rookie']
FAMILIES={'BASE CARDS':100,'ROOKIES':100,'LIGHT SPEED':35,'EXTRATERRESTRIAL TALENT':25,'STARS IN THE NIGHT':25,'STAR CLUSTERS':30,'LIGHT YEARS':20,'COSMIC DUST':20,'COS PLAY':25,'SUPERNOVA':25,'PLANETARY PURSUIT':100,'BASE CARDS CONSTELLATION VARIATION':100,'STARFRACTOR':100,'PLANETARIUM':25,'COSMIC CHROME AUTOGRAPH VARIATION':68,'SOLAR FLARES SIGNATURES':26,'EQUINOX AUTOGRAPHS':29,'FIRST FLIGHT SIGNATURES':25}

def read_cards(path):
    rows=[];raw=[];notes=[];family=None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==18
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
            for c in page.chars:groups[round(c['top'],1)].append(c)
            for y,cs in sorted(groups.items()):
                line=text(cs)
                if pn==1 and y<100:notes.append([str(pn),line]);continue
                if all('Bold' in c['fontname'] for c in cs):
                    if line not in {'BASE','INSERT','AUTOGRAPH'}:
                        assert line in FAMILIES,(pn,line)
                        family=line
                    continue
                # Cell-start glyphs delimit the original drawing sequence, including overlaps.
                a=next(i for i,c in enumerate(cs) if abs(c['x0']-132.62)<.02)
                b=next(i for i,c in enumerate(cs) if abs(c['x0']-269.45)<.02)
                k=next((i for i,c in enumerate(cs) if abs(c['x0']-421.27)<.02),len(cs))
                number,name,team,rookie=[text(v) for v in [cs[:a],cs[a:b],cs[b:k],cs[k:]]]
                assert family and re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and name and team and rookie in {'','Rookie'},(pn,line)
                rows.append([family,number,name,str(pn),team,rookie])
    assert len(rows)==878 and collections.Counter(r[0] for r in rows)==FAMILIES
    assert len({tuple(r[:2]) for r in rows})==863 and sum(r[5]=='Rookie' for r in rows)==373
    return rows,raw,notes

def build():
    proof=json.loads(PROOF.read_text());sources=proof['sources']
    evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');sha=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);original,formats,odds_raw,issues=physical_odds_pdf(op)
    assert (sha,oh)==(proof['checklistSha256'],proof['oddsSha256']) and len(original)==113 and formats==['Hobby','Lunar'] and not issues
    aliases={f.title():f for f in FAMILIES}
    aliases.update({'Base':'BASE CARDS','Base Constellation Variation':'BASE CARDS CONSTELLATION VARIATION','Cos-Play':'COS PLAY'})
    odds=[]
    for item in original:
        prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None)
        assert prefix,item['name']
        odds.append(dict(item,family=aliases[prefix],familyBase=item['name'].casefold()==prefix.casefold()))
    assert {o['family'] for o in odds}==set(FAMILIES)
    specs=[dict(s,source=sources['hobbyGuide'],**evidence) for s in proof['guideSpecifications']]
    for spec in specs:assert any(o['name']==spec['oddsName'] and o['family']==spec['family'] for o in odds),spec
    def table(name,headers,values,source):
        return dict(name=name,worksheet='Official manufacturer guide; preserve card scope and source units',headers=headers,rows=values,source=source,**evidence)
    published=[table('EQUINOX AUTOGRAPHS',['Card number','Name','Parallel / variation','Published statement','Qualification'],proof['cardExamples'],sources['chaseGuide']),
        table('Official Hobby box configuration',['Published item','Published value','Unit / qualification'],proof['boxContents'],sources['hobbyGuide']),
        table('Official guide program sizes',['Checklist family','Published size','Qualification'],[['BASE CARDS / ROOKIES','200 cards','100 veterans / legends plus 100 rookies; both physical sections retain separate odds.']],sources['chaseGuide']),
        table('PLANETARY PURSUIT',['Published parallel name','Guide numbering statement'],[[n,'No numbering stated in the guide'] for n in proof['planetaryNames']],sources['hobbyGuide'])]
    for family in ['BASE CARDS','ROOKIES']:
        published.append(table(family,['Parallel / variation','Guide numbering statement'],[[n,'No numbering stated in the guide'] for n in proof['unnumberedBaseNames']],sources['hobbyGuide']))
    note=('All 878 physical subject rows / 863 family-card identities across 18 sections are reconciled, with original Name/Team cells and 373 literal Rookie marks. '
          'The 15 Star Clusters numbers each retain both subjects and their individual teams/flags. All 113 Hobby/Lunar odds categories retain literal values, including Base 3:1; the sheet states no ratio unit. '
          'Four exact guide joins retain Aqua Equinox /199 and Superfractor 1/1 only for the 200-card base program, split across Base and Rookies. '
          'Equinox Tom Brady five-copy Red Flare and Caleb Williams Orange Galactic numbered to 25 remain card-specific; the Brady statement does not establish serial marking. '
          'Other colors, autograph families and the calendar release date remain unverified; guide publication dates and box contents do not establish release or pack odds.')
    data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=sha,source=proof['checklistUrl'],dedicatedParser=PARSER,importKind='pdf',coverageComplete=True,sectionColumn=0,odds=odds,formats=formats,officialOddsTable=original,officialOddsFormats=formats,officialOddsHeader=['Card','Hobby','Lunar'],oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser='scripts/official_odds_layout.py',formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=published,sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[gap] for gap in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(sourcePage=sources['landing'],rowCount=878,sections=18,sha256=sha,dedicatedParser=PARSER,coverageComplete=True,odds=113,formats=2,oddsParser='scripts/official_odds_layout.py',oddsImportIssues=0,verified=proof['observed'],dataAudit=note,catalogEvidence=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=sources['hobbyGuide']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text())
    inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record]
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=specs
    registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Other numbering and card-specific guide scope',gap=' '.join(proof['remainingGaps']),source=sources['hobbyGuide'],**evidence)]
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Cosmic Football: 878 subjects / 863 identities / 18 sections / 373 Rookie flags, 113 literal Hobby/Lunar odds, four scoped base guide limits and two card-specific autograph statements.')
if __name__=='__main__':build()
