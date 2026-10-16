"""Import Mars Christmas physical rows, wrapped artist and product-linked odds."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-mars-attacks-christmas'
PARSER='scripts/import_topps_mars_christmas_2026.py';PROOF=ROOT/'data/parallel-audit-sources/mars-christmas-2026-20261015.json'
HEADERS=['Checklist section','Card number','Player / subjects','Source page','Artist Name']
FAMILIES={'BASE CARDS','BASE CARDS CHARACTERS A','BASE CARDS CHARACTERS B','HEADLINES','BATTLE READY','CAUGHT IN THE CROSSFIRE','MARS INVASION CHROME CARDS','LUMP OF COAL DIE CUT','GREETING CARD BOXTOPPER','PRESENT RIP CARD BOXTOPPER','PRESENT MINI CARDS','CRYPTIDS ALLIANCE','CRYPTIDS ALLIANCE FACSIMILE AUTOGRAPHS','CAUGHT IN THE CROSSFIRE AUTOGRAPH VARIATION','INVASION WORN RELIC CARDS','SKETCH CARD ARTISTS'}

def read_cards(path):
    rows=[];raw=[];notes=[];family=None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==7
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
            for c in page.chars:groups[round(c['matrix'][5],1)].append(c)
            for y,cs in sorted(groups.items(),reverse=True):
                line=text(cs)
                if not line:continue
                if pn==1 and line.startswith(('Checklists provided by Topps','at the time of production')):notes.append([str(pn),line]);continue
                if line in FAMILIES:family=line;continue
                if line in {'BASE','INSERT','AUTOGRAPH','RELIC','SKETCH'}:continue
                assert family,(pn,line)
                if family=='SKETCH CARD ARTISTS':
                    if pn==7 and line=='Gumbrell':
                        assert rows[-1][4]=='Jordan "Slippa Chervascus"'
                        rows[-1][2]+=' '+line;rows[-1][4]+=' '+line;continue
                    rows.append([family,'',line,str(pn),line]);continue
                number=text([c for c in cs if c['x0']<130]);name=text([c for c in cs if c['x0']>=130])
                assert re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+|LC',number) and name,(pn,number,name,line)
                rows.append([family,number,name,str(pn),''])
    assert len(rows)==316 and sum(bool(r[1]) for r in rows)==239
    return rows,raw,notes

def read_odds(path):
    odds=[];raw=[]
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==4
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text()));tables=page.find_tables();assert len(tables)==1
            # Alternating rows omit the central border. Its printed segments
            # at x=440.5 anchor the same two physical columns on all pages.
            assert any(row.cells[0] and abs(row.cells[0][2]-440.5)<.01 for row in tables[0].rows)
            for i,row in enumerate(tables[0].rows):
                box=row.bbox;chars=[c for c in page.chars if box[0]<=(c['x0']+c['x1'])/2<box[2] and box[1]<=(c['top']+c['bottom'])/2<box[3]]
                cells=[]
                for left,right in [(box[0],440.5),(440.5,box[2])]:
                    lines=collections.defaultdict(list)
                    for c in chars:
                        if left<=(c['x0']+c['x1'])/2<right:lines[round(c['matrix'][5],1)].append(c)
                    cells.append(' '.join(text(cs) for y,cs in sorted(lines.items(),reverse=True)).strip())
                if i==0:assert cells==['Cards','Hobby'];continue
                assert cells[0] and (cells[1]=='-' or re.fullmatch(r'1:[\d,]+',cells[1])),(pn,cells)
                odds.append(dict(name=cells[0],values={'Hobby':None if cells[1]=='-' else cells[1]},page=pn))
    assert len(odds)==70 and sum(o['values']['Hobby'] is None for o in odds)==5
    return odds,raw


def build():
    proof=json.loads(PROOF.read_text());ph=hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);odds,odds_raw=read_odds(op)
    assert digest==proof['checklistSha256'] and oh==proof['oddsSha256']
    aliases={'Base Cards':'BASE CARDS','Battle Ready':'BATTLE READY','Caught In The Crossfire':'CAUGHT IN THE CROSSFIRE','Cryptids Alliance':'CRYPTIDS ALLIANCE','Cryptids Alliance Facsimile Autographs Chrome':'CRYPTIDS ALLIANCE FACSIMILE AUTOGRAPHS','Headlines':'HEADLINES','Lump Of Coal':'LUMP OF COAL DIE CUT','Mars Invasion Chrome':'MARS INVASION CHROME CARDS','Caught In The Crossfire Autographs Chrome':'CAUGHT IN THE CROSSFIRE AUTOGRAPH VARIATION','Invasion Worn Relics':'INVASION WORN RELIC CARDS','Greeting Card Box Topper':'GREETING CARD BOXTOPPER','Present Rip Card Box Topper':'PRESENT RIP CARD BOXTOPPER','Present Mini Cards':'PRESENT MINI CARDS','Sketch Card':'SKETCH CARD ARTISTS'}
    for odd in odds:
        prefix=next((a for a in sorted(aliases,key=len,reverse=True) if odd['name']==a or odd['name'].startswith(a+' ')),None)
        assert prefix,odd['name'];odd.update(family=aliases[prefix],familyBase=odd['name']==prefix)
    additions=[dict(**s,**evidence,qualification='Published for this family; individual-card eligibility is not inferred.') for s in proof['guideNumbering']]
    assert len(additions)==2 and all(any(o['name']==s['oddsName'] and o['family']==s['family'] for o in odds) for s in additions)
    note=('All 239 coded subject rows and 77 unnumbered sketch artists across 16 sections are reconciled against original physical PDF rows. '
          'LC Lump of Coal is retained; the 50-card base and both 25-row Characters A/B lists remain separate. '
          'The wrapped Jordan "Slippa Chervascus" Gumbrell artist is a single entry. Printed CCA-GTA and CCA-MRO differ from their non-autograph codes; all original titles and spellings are retained. '
          'The official product landing page supplies odds absent from the global catalog: all 70 Hobby categories retain 65 literal ratios and five unlisted Present Mini values. '
          'No ratio unit is named. Exact guide joins number only Base Cards Candy Cane /299 and Snowcaps /5; extended character allocation, illustrated insert examples and other numbering remain qualified. '
          'Box contents and store availability are not pack odds or a verified general release date. Exhaustive parallel reconciliation remains incomplete.')
    data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,dedicatedParser=PARSER,coverageComplete=True,importKind='pdf',sectionColumn=0,odds=odds,formats=['Hobby'],oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser=PARSER,formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=additions,
      publishedSpecifications=[dict(name='Manufacturer product fields',worksheet='Store availability and box contents are not category odds or a general release date',headers=['Published field','Published value','Scope'],rows=proof['productFields'],source=proof['productSource'],**evidence),dict(name='Manufacturer guide qualifications',worksheet='Exact numbering joins appear with their family odds; other claims retain their published scope',headers=['Published field','Published value','Scope'],rows=proof['guideFields'],source=proof['guideSource'],**evidence),dict(name='Manufacturer illustrated examples',worksheet='Only the named guide examples; limits are not assigned to entire checklist families',headers=['Published example','Parallel / variation','Published numbering','Scope'],rows=proof['illustratedExamples'],source=proof['guideSource'],**evidence)],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(sourcePage=proof['landingSource'],rowCount=len(rows),sections=16,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=70,formats=1,oddsUrl=proof['oddsUrl'],verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser=PARSER,oddsImportIssues=0,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=proof['landingSource']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());ip.write_text(json.dumps([r for r in inventory if r['slug']!=SLUG]+[record],ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=additions;registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]
    registry['conflicts'].append(dict(slug=SLUG,family='Extended character scope, illustrated insert numbering and ratio units',gap=' '.join(proof['remainingGaps']),source=proof['guideSource'],**evidence));rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    op=ROOT/'data/entertainment-topps-odds.json';sources=json.loads(op.read_text());sources=[r for r in sources if r['title']!=record['title']]+[dict(title=record['title'],url=proof['oddsUrl'],discoverySource=proof['landingSource'],sha256=oh)];op.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
    print('Mars Christmas: 239 coded subjects, 77 artists, 16 families, 70 Hobby odds categories / 65 ratios / five nulls; two exact base numbering joins.')

if __name__=='__main__':build()
