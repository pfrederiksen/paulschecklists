"""Reconcile original Toy Story text objects, artist rosters and ruled odds cells."""
import collections,hashlib,json,logging,re
from pathlib import Path
import pdfplumber
from pypdf import PdfReader
from import_topps_tribute_2026 import acquire,text
from official_odds_layout import cells_from_origins
logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-30-years-of-toy-story'
PARSER='scripts/import_topps_toy_story_2025.py';PROOF=ROOT/'data/parallel-audit-sources/toy-story-2025-20261015.json'
HEADERS=['Checklist section','Card number','Player / subjects','Source page','Character','Property','First Name','Last Name','Artist Name']
FAMILIES={'BASE','30 YEARS AND BEYOND','IMAGE VARIATIONS','PIZZA PLANET VARIATION','CONE VARIATION','PIXAR BALL VARIATION','SO PLAY NICE','FALLING WITH STYLE','TOPPS 1995',"AL'S TOY BARN","YOU'VE GOT A FRIEND IN ME",'TO INFINITY…','… AND BEYOND','TOY TAAFFEITE','ART OF TOY STORY','SID HAS YOUR CARDS',"ANDY'S CARDS SHADOWBOX",'THE CLAW SHADOWBOX','YOU. ARE. A. TOY... STORY AUTOGRAPH CARD',"YOU'VE GOT A FRIEND IN ME DUAL AUTOGRAPH",'GOLDEN TOYS SHADOWBOX AUTOGRAPH','EXECUTIVE STUDIO CREATIONS SKETCH CARD','STUDIO CREATIONS SKETCH CARD','TOY STORY SKETCH CARDS'}

def read_cards(path):
    rows=[];raw=[];notes=[];family=None;reader=PdfReader(path)
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==10
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text()));objects=[]
            def visit(value,cm,tm,font,size):
                if value.strip():objects.append((tm[4]*cm[0]+cm[4],tm[5]*cm[3]+cm[5],value))
            reader.pages[pn-1].extract_text(visitor_text=visit)
            groups=collections.defaultdict(list)
            for c in page.chars:
                y=c['matrix'][5]
                if pn==1 and y>680 and c['x0']>=398:continue
                groups[round(y,1)].append(c)
            if pn==1:notes.append([str(pn),text([c for c in page.chars if c['matrix'][5]>680 and c['x0']>=398])])
            origins=[54,108,274] if pn<=2 else [54,104,322] if pn<=4 else [54,98] if pn<=6 else [55,125,210,295] if pn<=8 else [55]
            for y,cs in sorted(groups.items(),reverse=True):
                line=text(cs)
                if not line:continue
                if line in FAMILIES:family=line;continue
                if line in {'Card NumberCharacterProperty','Card NumberFirst NameLast NameCharacter','Artist Name'}:continue
                row_objects=[o for o in objects if abs(o[1]-y)<.06 and not(pn==1 and y>680 and o[0]>=398)]
                cells,edges=cells_from_origins(cs,row_objects,origins)
                assert family,(pn,line)
                if pn>=9:
                    assert len(cells)==1 and cells[0],(pn,cells)
                    rows.append([family,'',cells[0],str(pn),'','','','',cells[0]]);continue
                number=cells[0];assert re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',number),(pn,cells)
                if pn<=4:
                    character,prop=cells[1:];first=last='';name=character
                elif pn<=6:
                    character=cells[1];prop=first=last='';name=character
                else:
                    first,last,character=cells[1:];prop='';name=' '.join([first,last]).strip()
                assert name and character,(pn,cells)
                rows.append([family,number,name,str(pn),character,prop,first,last,''])
    return rows,raw,notes

def read_odds(path):
    rows=[];raw=[]
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==6
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text()));tables=page.find_tables();assert len(tables)==1
            for i,row in enumerate(tables[0].rows):
                assert len(row.cells)==2 and all(row.cells)
                cells=[]
                for box in row.cells:
                    chars=[c for c in page.chars if box[0]<=(c['x0']+c['x1'])/2<box[2] and box[1]<=(c['top']+c['bottom'])/2<box[3]]
                    lines=collections.defaultdict(list)
                    for c in chars:lines[round(c['matrix'][5],1)].append(c)
                    cells.append(' '.join(text(cs) for y,cs in sorted(lines.items(),reverse=True)).strip())
                if i==0:assert cells==['','Hobby'];continue
                assert cells[0] and re.fullmatch(r'1:[\d,]+',cells[1]),(pn,cells)
                rows.append(dict(name=cells[0],values={'Hobby':cells[1]},page=pn))
    assert len(rows)==104
    return rows,raw


def build():
    proof=json.loads(PROOF.read_text());ph=hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence=dict(source=proof['guideSource'],evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);odds,odds_raw=read_odds(op)
    assert digest==proof['checklistSha256'] and oh==proof['oddsSha256']
    aliases={'Base Cards':'BASE','Image Variations':'IMAGE VARIATIONS','Pizza Planet Variation':'PIZZA PLANET VARIATION','Cone Variation':'CONE VARIATION','Pixar Ball Variation':'PIXAR BALL VARIATION','30 Years And Beyond':'30 YEARS AND BEYOND',"You've Got A Friend In Me":"YOU'VE GOT A FRIEND IN ME",'Falling with Style':'FALLING WITH STYLE','So Play Nice':'SO PLAY NICE','Topps 1995':'TOPPS 1995',"Al's Toy Barn":"AL'S TOY BARN",'To Infinity…':'TO INFINITY…','…and Beyond':'… AND BEYOND','Toy Taaffeite':'TOY TAAFFEITE','Art of Toy Story':'ART OF TOY STORY','Sid Has Your Cards':'SID HAS YOUR CARDS',"Andy's Cards Shadowbox":"ANDY'S CARDS SHADOWBOX",'The Claw Shadowbox':'THE CLAW SHADOWBOX','You. Are. A. Toy… Story Autograph Card':'YOU. ARE. A. TOY... STORY AUTOGRAPH CARD',"You've Got A Friend In Me Dual Autograph":"YOU'VE GOT A FRIEND IN ME DUAL AUTOGRAPH",'Golden Toys Shadowbox Autograph':'GOLDEN TOYS SHADOWBOX AUTOGRAPH','Toy Story Sketch Card':'TOY STORY SKETCH CARDS','Studio Creations Sketch Card':'STUDIO CREATIONS SKETCH CARD'}
    for odd in odds:
        prefix=next((a for a in sorted(aliases,key=len,reverse=True) if odd['name']==a or odd['name'].startswith(a+' ')),None)
        assert prefix,odd['name'];odd.update(family=aliases[prefix],familyBase=odd['name']==prefix)
    additions=[]
    for published in proof['guideNumbering']:
        spec={**published,**evidence,'qualification':'Published for this family; individual-card eligibility is not inferred.'}
        prefix=next(a for a,f in aliases.items() if f==spec['family'])
        label=spec['name'].replace('’',"'")
        if spec['family']!='BASE':label=label.removesuffix(' Parallel')
        if label in {"Woody's Cowboy Hat Shimmer Refractor",'Buzz Lightyear Shimmer Refractor'}:
            label=label.removesuffix(' Refractor')
        target=prefix+' '+label;match=[o for o in odds if o['name']==target]
        if match:assert len(match)==1;spec['oddsName']=match[0]['name']
        else:
            assert spec['family']=='SID HAS YOUR CARDS' or (spec['family']=="YOU'VE GOT A FRIEND IN ME DUAL AUTOGRAPH" and label in {"Woody's Cowboy Hat Shimmer",'Gold Refractor'}),target
            spec['qualification']+=' Guide-only parallel; no matching odds row is published in the checked PDF.'
        additions.append(spec)
    assert len(additions)==47 and sum('oddsName' in s for s in additions)==42
    assert len(rows)==511 and sum(bool(r[1]) for r in rows)==425
    note=('All 425 numbered subject rows / 395 family-card identities and 86 unnumbered artists across 24 sections are reconciled against original PDF text-object columns. '
          'The 100 BASE entries and 35 30 YEARS AND BEYOND entries are separate programs; the numeric-leading heading is a caption. '
          'Character/Property and First Name/Last Name/Character cells remain separate, including repeated dual signers, three image-variation 25 entries and Tinny’s printed Toy Story 2 variation property. '
          'All 104 Hobby odds and literal values are preserved; no ratio unit is named. The guide supplies 47 exact family limits: 42 join existing odds and five remain specification-only, without invented ratios. '
          'Guide-only autograph example spellings, store availability and box contents remain qualified. A general release date and exhaustive parallel coverage remain unverified.')
    data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,dedicatedParser=PARSER,coverageComplete=True,importKind='pdf',sectionColumn=0,odds=odds,formats=['Hobby'],oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser=PARSER,formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=additions,
      publishedSpecifications=[dict(name='Manufacturer product fields',worksheet='Store availability and box contents are not pack odds or a general release date',headers=['Published field','Published value','Scope'],rows=proof['productFields'],**{**evidence,'source':proof['productSource']}),dict(name='Manufacturer guide qualifications',worksheet='Read directly from the official guide; family-scoped limits appear with the published odds',headers=['Published field','Published value','Scope'],rows=proof['guideFields'],**evidence)],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(sourcePage=proof['productSource'],rowCount=len(rows),sections=24,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=104,formats=1,verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser=PARSER,oddsImportIssues=0,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=proof['productSource']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());ip.write_text(json.dumps([r for r in inventory if r['slug']!=SLUG]+[record],ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=additions;registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]
    registry['conflicts'].append(dict(slug=SLUG,family='Unjoined guide parallels, sketch odds and release-date audit',gap=' '.join(proof['remainingGaps']),**evidence));rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Toy Story: 425 numbered subjects, 86 artists, 24 families, all 104 Hobby odds, 42 numbered odds joins and five specification-only guide parallels.')

if __name__=='__main__':build()
