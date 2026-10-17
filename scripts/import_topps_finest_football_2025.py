"""Reconcile Finest Football's original cells and strictly scoped guide evidence."""
import collections, hashlib, json, re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire, text
from official_odds_layout import physical_odds_pdf

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2025-topps-finest-football'
PARSER='scripts/import_topps_finest_football_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/finest-football-2025-20261016.json'
HEADERS=['Checklist section','Card number','Name','Source page','Team','Rookie']
FAMILIES={'BASE CARDS COMMON':100,'BASE CARDS UNCOMMON':100,'BASE CARDS RARE':100,'REFLASH':20,'TORCHERS':30,'POWER KINGS':10,'CENTURIONS':15,'THE MAN':20,'FOR THE RECORD':10,'FRAMED WHITE':25,'CREATORS':30,'NIGHTMARE FUEL':15,'SMASHING THROUGH':15,'LANDMARK METAL SERIES':20,'92 FINEST':44,'HEADLINERS':15,'TEAM FINEST':10,'FINEST AUTOGRAPHS':39,'ROOKIE FINEST AUTOGRAPHS':52,'FLASHBACK AUTOGRAPHS':38,'FINEST FRESHMAN AUTOGRAPHS':10,'FINEST GREATS AUTOGRAPHS':35,'FINEST MOMENTS AUTOGRAPHS':26,'FINEST FANS AUTOGRAPHS':9}

def read_cards(path):
    rows=[];raw=[];notes=[];family=None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==17
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
                assert family and re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',number) and name and team and rookie in {'','Rookie'},(pn,line)
                rows.append([family,number,name,str(pn),team,rookie])
    assert len(rows)==788 and collections.Counter(r[0] for r in rows)==FAMILIES
    assert len({tuple(r[:2]) for r in rows})==788 and sum(r[5]=='Rookie' for r in rows)==212
    return rows,raw,notes

def build():
    proof=json.loads(PROOF.read_text());sources=proof['sources']
    evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');sha=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);original,formats,odds_raw,issues=physical_odds_pdf(op)
    assert (sha,oh)==(proof['checklistSha256'],proof['oddsSha256']) and len(original)==228 and formats==['Hobby','Breaker Delight'] and not issues
    aliases={f.title():f for f in FAMILIES}
    aliases.update({'Base Common':'BASE CARDS COMMON','Base Uncommon':'BASE CARDS UNCOMMON','Base Rare':'BASE CARDS RARE','Finest Freshman Auto':'FINEST FRESHMAN AUTOGRAPHS'})
    odds=[]
    for item in original:
        prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None)
        assert prefix,item['name']
        odds.append(dict(item,family=aliases[prefix],familyBase=item['name'].casefold()==prefix.casefold() or item['name'].casefold()==(prefix+' Refractor').casefold()))
    assert {o['family'] for o in odds}==set(FAMILIES)
    def table(name,headers,values,source):
        return dict(name=name,worksheet='Official manufacturer guide; retain exact card scope',headers=headers,rows=values,source=source,**evidence)
    published=[]
    for family in dict.fromkeys(r[0] for r in proof['cardExamples']):
        values=[r[1:] for r in proof['cardExamples'] if r[0]==family]
        for r in values:assert any(row[0]==family and row[1]==r[0] and row[2]==r[1] for row in rows),r
        published.append(table(family,['Card number','Name','Parallel / variation','Published statement','Qualification'],values,sources['pulls'] if family!='FLASHBACK AUTOGRAPHS' else sources['chaseGuide']))
    published.append(table('Unjoined rookie-autograph guide examples',['Published subjects','Published parallel','Published statement','Qualification'],proof['unjoinedExamples'],sources['chaseGuide']))
    note=('All 788 physical subject rows across 24 sections are reconciled, with original Name/Team cells and 212 literal Rookie marks. '
          'The numeric-leading 92 FINEST caption is a section heading, not a card; its 44 numbered rows remain separate from Landmark Metal Series. '
          'All 228 Hobby/Breaker Delight odds categories retain literal values, including Base Common 6:1; the sheet states no ratio unit. '
          'Five exact card-specific guide/pull-report examples retain their published terms without numbering other subjects. Mixed Rookie Finest/Finest Freshman examples remain qualified without a family join. '
          'The May 22 official pull report explicitly states May 15 release, separate from product year 2025. Exhaustive parallel numbering remains unverified.')
    data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=sha,source=proof['checklistUrl'],dedicatedParser=PARSER,importKind='pdf',coverageComplete=True,sectionColumn=0,odds=odds,formats=formats,officialOddsTable=original,officialOddsFormats=formats,officialOddsHeader=['Card','Hobby','Breaker Delight'],oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser='scripts/official_odds_layout.py',formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=published,sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[gap] for gap in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(sourcePage=sources['landing'],rowCount=788,sections=24,sha256=sha,dedicatedParser=PARSER,coverageComplete=True,odds=228,formats=2,oddsParser='scripts/official_odds_layout.py',oddsImportIssues=0,verified=proof['observed'],dataAudit=note,catalogEvidence=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=sources['chaseGuide']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text())
    inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record]
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=[]
    registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Other numbering and card-specific guide scope',gap=' '.join(proof['remainingGaps']),source=sources['chaseGuide'],**evidence)]
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Finest Football: 788 physical subjects / 24 sections / 212 Rookie flags, 228 literal Hobby/Breaker Delight categories, five exact card examples and verified May 15 release evidence retained separately.')
if __name__=='__main__':build()
