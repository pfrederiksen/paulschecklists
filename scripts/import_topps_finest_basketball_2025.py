"""Preserve Finest Basketball's original cells and borderless odds-column origins."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2025-26-topps-finest-basketball'
PARSER='scripts/import_topps_finest_basketball_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/finest-basketball-2025-26-20261016.json'
HEADERS=['Checklist section','Card number','Name','Source page','Team']
FAMILIES={'BASE COMMON':100,'BASE UNCOMMON':100,'BASE RARE':100,'ARRIVALS':30,'FIRST':30,'FINISHERS':10,'PULSE':20,'THE MAN':20,'HEADLINERS':15,'MUSE':30,'AURA':20,'AUTOGRAPH CARDS':54,'ROOKIE AUTOGRAPHS':40,'BASELINE AUTOGRAPHS':50,'MASTERS AUTOGRAPHS':47,'ELECTRIFYING SIGNATURES':49,'COLOSSAL SHOTS AUTOGRAPHS':49}
FORMATS=['Hobby','Breaker']

def read_cards(path):
    rows=[];raw=[];family=None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==16
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
            for c in page.chars:groups[round(c['top'],1)].append(c)
            for y,cs in sorted(groups.items()):
                line=text(cs)
                if all('Bold' in c['fontname'] for c in cs):
                    if line not in {'BASE','INSERT','AUTOGRAPH'}:
                        assert line in FAMILIES,(pn,line)
                        family=line
                    continue
                a=next(i for i,c in enumerate(cs) if abs(c['x0']-132.62)<.02)
                b=next(i for i,c in enumerate(cs) if abs(c['x0']-269.45)<.02)
                number,name,team=[text(part) for part in [cs[:a],cs[a:b],cs[b:]]]
                assert family and re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and name and team,(pn,line)
                rows.append([family,number,name,str(pn),team])
    assert len(rows)==764 and len({tuple(r[:2]) for r in rows})==764 and collections.Counter(r[0] for r in rows)==FAMILIES
    return rows,raw

def read_odds(path):
    odds=[];raw=[]
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==5
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
            for c in page.chars:groups[round(c['top'],2)].append(c)
            for y,cs in sorted(groups.items()):
                cells=[];a=0
                # Use original object starts, not merged words or a guessed border.
                starts=[(i,c['x0']) for i,c in enumerate(cs) if c['text'][0] in '0123456789' and any(abs(c['x0']-origin)<.02 for origin in [290.57,375.67])]
                if pn==1 and y==56.52:
                    assert text(cs)=='SubsetHobbyBreaker'
                    continue
                assert starts,(pn,y,text(cs))
                name=text(cs[:starts[0][0]]);values=dict.fromkeys(FORMATS)
                for j,(i,x) in enumerate(starts):
                    value=text(cs[i:starts[j+1][0] if j+1<len(starts) else len(cs)])
                    assert re.fullmatch(r'\d+:\d+',value),(pn,name,value)
                    fmt='Hobby' if abs(x-290.57)<.02 else 'Breaker'
                    assert values[fmt] is None
                    values[fmt]=value
                assert name
                odds.append(dict(name=name,values=values,page=pn))
    assert len(odds)==217
    assert odds[0]==dict(name='Base Common',values={'Hobby':'5:1','Breaker':None},page=1)
    assert next(o for o in odds if o['name']=='Base Common Geometric')['values']=={'Hobby':None,'Breaker':'2:1'}
    return odds,raw

def build():
    proof=json.loads(PROOF.read_text());sources=proof['sources'];evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');sha=acquire(proof['checklistUrl'],path);rows,raw=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);original,odds_raw=read_odds(op)
    assert (sha,oh)==(proof['checklistSha256'],proof['oddsSha256'])
    aliases={f.title():f for f in FAMILIES};aliases['Autographs']='AUTOGRAPH CARDS'
    odds=[]
    for item in original:
        prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None)
        assert prefix,item['name']
        odds.append(dict(item,family=aliases[prefix],familyBase=item['name'].casefold()==prefix.casefold()))
    assert {o['family'] for o in odds}==set(FAMILIES)
    table=lambda name,headers,values,source:dict(name=name,headers=headers,rows=values,source=source,worksheet='Official manufacturer evidence; retain source scope and original units',**evidence)
    published=[table('Official Hobby box contents',['Published item','Published quantity','Unit / qualification'],[['Packs','6','Per Hobby box'],['Cards','10','Per pack; box configuration, not a category ratio'],['Cards','60','Per Hobby box']],sources['spotlight']),
      table('Unjoined Cooper Flagg pull-report example',['Published subject','Parallel / variation','Published statement','Qualification'],[['Cooper Flagg','Black Geometric','1/1','Card-specific pull from Breaker’s Delight; no printed number or tier is identified. No limit is copied to Common, Uncommon, Rare or autographs.']],sources['pullReport']),
      table('BASE COMMON',['Card number','Name','Published statement','Qualification'],[['1','Cooper Flagg','Named as RC in the official historical-rookie article','Card-specific article annotation; the original PDF publishes no rookie field and no row flags are inferred.']],sources['rookieHistory']),
      table('Guide-described checklist sizes',['Checklist family','Published size'],[['BASE COMMON / BASE UNCOMMON / BASE RARE','300 cards'],['HEADLINERS','15 cards'],['AURA','20 cards'],['MASTERS AUTOGRAPHS','47 cards']],sources['spotlight'])]
    note=('All 764 original subject rows across 17 sections are reconciled to physical Name/Team cell origins. All 300 tiered base numbers remain intact. '
          'The PDF publishes no Rookie column: the shared rookie control stays disabled, while guide annotations remain separate. '
          'All 217 odds categories retain original Hobby/Breaker columns, blank cells, literal Base Common 5:1 and Geometric 2:1; the sheet names no ratio unit. '
          'Combining accents, printed Cade Cunnigham, Philadelpia 76ers, Seattle Supersonics and Portland Trailblazers spellings remain unchanged. '
          'The official Flagg Black Geometric 1/1 pull lacks an exact printed number/tier join and remains qualified. Historical rookie-card limits never number this release. '
          'February 26, 2026 release evidence is retained separately; exhaustive parallel numbering remains unverified.')
    data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=[],unclassifiedLines=[],source=proof['checklistUrl'],sha256=sha,dedicatedParser=PARSER,importKind='pdf',coverageComplete=True,sectionColumn=0,odds=odds,formats=FORMATS,officialOddsTable=original,officialOddsFormats=FORMATS,officialOddsHeader=['Subset',*FORMATS],oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser=PARSER,formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=published,sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(sourcePage=sources['landing'],rowCount=764,sections=17,sha256=sha,dedicatedParser=PARSER,coverageComplete=True,odds=217,formats=2,oddsParser=PARSER,oddsImportIssues=0,verified=proof['observed'],dataAudit=note,catalogEvidence=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=sources['spotlight']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=[]
    registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Unjoined card example and remaining numbering',gap=' '.join(proof['remainingGaps']),source=sources['pullReport'],**evidence)]
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Finest Basketball: 764 physical subjects / 17 sections, original Name/Team fields, 217 literal Hobby/Breaker odds; rookie flags unavailable and numbering examples remain strictly qualified.')
if __name__=='__main__':build()
