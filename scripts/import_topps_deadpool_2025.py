"""Reconcile Deadpool's original checklist cells, repeated odds grids and guide scopes."""
import collections,hashlib,json,logging,re
from pathlib import Path
import pdfplumber
from pypdf import PdfReader
from import_topps_tribute_2026 import acquire,text
logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-chrome-deadpool'
PARSER='scripts/import_topps_deadpool_2025.py';PROOF=ROOT/'data/parallel-audit-sources/deadpool-2025-20261015.json'
HEADERS=['Checklist section','Card number','Player / subjects','Source page','Official text column 1','Official text column 2','Artist Name']
FAMILIES={'COMIC ACCURATE','CHARACTERS','MULTIVERSE AND MORE','COMIC BOOK GOLD','COVER STARS','WELL YOU GOT NOTHING TO SAY MOUTH','FUTURE STARS','TOPPS ORIGINALS','10005 FIRE','BEST BUBS','LOOKING FOR LOGAN','INDESTRUCTIBLE','DEADPOOL REFLECTIONS','HIDDEN GEMS','THE VOID','DEADPOOL ICONS','TOPPS CHROME AUTOGRAPH CARDS','BEST BUBS AUTOGRAPH CARDS','ON CARD DUAL INSCRIPTIONS BOOK CARD','TOPPS CHROME DUAL AUTOGRAPHS','MARVEL COMIC BOOK ARTIST AUTOGRAPHS','DEADPOOL AUTOGRAPHS','MARVEL COMIC BOOK ARTIST SKETCH CARDS','DEADPOOL SKETCH CARDS'}
FORMATS=['HOBBY','VALUE SE','VALUE BOX EA','VALUE BOX CEE']

def cell_boxes(page):
    state={'clip':None,'pending':None};stack=[];boxes=set()
    def before(op,args,cm,tm):
        if op==b'q':stack.append(state.copy())
        elif op==b'Q':state.clear();state.update(stack.pop())
        elif op==b're':
            x,y,w,h=map(float,args);assert abs(cm[1])+abs(cm[2])<.001
            state['pending']=(x*cm[0]+cm[4],y*cm[3]+cm[5],(x+w)*cm[0]+cm[4],(y+h)*cm[3]+cm[5])
        elif op in {b'W',b'W*'}:state['clip']=state['pending']
    def visit(value,cm,tm,font,size):
        if not value.strip():return
        if state['clip'] is None:
            assert tm[5]*cm[3]+cm[5]>740,value
        else:boxes.add(state['clip'])
    page.extract_text(visitor_text=visit,visitor_operand_before=before)
    return boxes

def read_cards(path):
    rows=[];notes=[];raw=[];family=None;reader=PdfReader(path)
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==10
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text()))
            if pn==1:notes.append([str(pn),text([c for c in page.chars if c['matrix'][5]>740])])
            cells=collections.defaultdict(lambda:['','',''])
            for box in cell_boxes(reader.pages[pn-1]):
                column={36.:0,262.:1,477.:2}[box[0]]
                chars=[c for c in page.chars if box[0]<=c['x0']<box[2] and box[1]<=c['matrix'][5]<=box[3]]
                lines=collections.defaultdict(list)
                for c in chars:lines[round(c['matrix'][5],1)].append(c)
                value=' '.join(text(cs) for y,cs in sorted(lines.items(),reverse=True)).strip()
                key=(box[1],box[3]);assert not cells[key][column],(pn,key,column)
                cells[key][column]=value
            for bounds,values in sorted(cells.items(),key=lambda pair:pair[0][1],reverse=True):
                number,first,second=values
                if number in {'BASE','INSERT','AUTOGRAPH','SKETCH'}:notes.append([str(pn),*values]);continue
                if number in FAMILIES:
                    family=number;assert not first and not second,(pn,values);continue
                assert family,(pn,values)
                artist=family in {'MARVEL COMIC BOOK ARTIST SKETCH CARDS','DEADPOOL SKETCH CARDS'}
                if artist:
                    assert number and not first and not second,(pn,values)
                    first=number;number=''
                else:assert re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and first,(pn,values)
                rows.append([family,number,first,str(pn),first,second,first if artist else ''])
    return rows,raw,notes

def read_odds(path):
    result=[];raw=[];headers=[]
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==31
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text()))
            tables=page.find_tables();assert tables,pn
            for table in tables:
                for physical in table.rows:
                    assert len(physical.cells)==5 and all(physical.cells),(pn,physical)
                    cells=[]
                    for box in physical.cells:
                        chars=[c for c in page.chars if box[0]<=(c['x0']+c['x1'])/2<box[2] and box[1]<=(c['top']+c['bottom'])/2<box[3]]
                        lines=collections.defaultdict(list)
                        for c in chars:lines[round(c['matrix'][5],1)].append(c)
                        cells.append(' '.join(text(cs) for y,cs in sorted(lines.items(),reverse=True)).strip())
                    if cells[0]=='SUBJECT TO CHANGE':assert pn==1 and not any(cells[1:]);continue
                    if not any(cells):assert pn==1;continue
                    if cells[0]=='CARDS':assert cells[1:]==FORMATS;headers.append(pn);continue
                    assert cells[0] and all(v=='-' or re.fullmatch(r'1:[\d,]+',v) for v in cells[1:]),(pn,cells)
                    result.append(dict(name=cells[0],values=dict(zip(FORMATS,[None if v=='-' else v for v in cells[1:]])),page=pn))
    assert len(result)==161 and headers==[1,2,3,4,6,7,8,9,11,12,13,14,16,17,18,20,21,22,23,24,26,27,28,30],(len(result),headers)
    return result,raw


def build():
    proof=json.loads(PROOF.read_text());ph=hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence=dict(source=proof['guideSource'],evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);odds,odds_raw=read_odds(op)
    assert digest==proof['checklistSha256'] and oh==proof['oddsSha256']
    aliases={'Base Cards':'COMIC ACCURATE','Comic Book Gold':'COMIC BOOK GOLD','Cover Stars':'COVER STARS','Future Stars':'FUTURE STARS','Well, you got nothing to say, Mouth':'WELL YOU GOT NOTHING TO SAY MOUTH','10005-Fire':'10005 FIRE','Best Bubs':'BEST BUBS','Looking for Logan':'LOOKING FOR LOGAN','Indestruc^ble':'INDESTRUCTIBLE','Deadpool Reﬂec^ons':'DEADPOOL REFLECTIONS','Hidden Gems':'HIDDEN GEMS','The Void':'THE VOID','Deadpool Sketch Cards':'DEADPOOL SKETCH CARDS','Marvel Comic Ar^st Sketch Cards':'MARVEL COMIC BOOK ARTIST SKETCH CARDS','Best Bubs Autograph Cards':'BEST BUBS AUTOGRAPH CARDS','Topps Chrome Autographs':'TOPPS CHROME AUTOGRAPH CARDS','On-Card Dual Inscrip^ons Book Card':'ON CARD DUAL INSCRIPTIONS BOOK CARD','Marvel Comic Book Ar^st Autographs':'MARVEL COMIC BOOK ARTIST AUTOGRAPHS','Deadpool Icons':'DEADPOOL ICONS','Topps Originals':'TOPPS ORIGINALS','Topps Chrome Dual Autographs':'TOPPS CHROME DUAL AUTOGRAPHS','Deadpool Autographs':'DEADPOOL AUTOGRAPHS'}
    for odd in odds:
        prefix=next((a for a in sorted(aliases,key=len,reverse=True) if odd['name']==a or odd['name'].startswith(a+' ')),None)
        assert prefix,odd['name'];odd.update(family=aliases[prefix],familyBase=odd['name']==prefix)
        if prefix=='Base Cards':odd['familyAliases']=['CHARACTERS','MULTIVERSE AND MORE']
    additions=[]
    for published in proof['guideNumbering']:
        spec={**published,**evidence, 'qualification':'Published for this family; individual-card eligibility is not inferred.'}
        if spec['family']=='BASE SET':
            spec['family']='COMIC ACCURATE';prefix='Base Cards'
        else:prefix=next(a for a,f in aliases.items() if f==spec['family'])
        if spec['name']=='TBC Parallel':
            spec['qualification']+=' Guide names TBC; this does not establish numbering for the separately named Superfractor.'
        else:
            label=spec['name'].replace(' and ',' & ')
            if ' (foil change to RayWave foil)' in label:
                label=label.replace(' (foil change to RayWave foil)','');spec['qualification']+=' Foil change to RayWave foil.'
            if ', foil change to Lava foil)' in label:
                label=label.replace(', foil change to Lava foil)',')');spec['qualification']+=' Foil change to Lava foil.'
            target=prefix+' '+label
            if spec['family']=='TOPPS CHROME AUTOGRAPH CARDS' and label=='Aqua Refractor Parallel':target=prefix+' Aqua Refractor'
            match=[o for o in odds if o['name'].casefold()==target.casefold()]
            assert len(match)==1,(target,match)
            spec['oddsName']=match[0]['name']
        additions.append(spec)
    assert len(additions)==60 and sum('oddsName' in s for s in additions)==59
    assert len(rows)==462 and sum(bool(r[1]) for r in rows)==314
    note=('All 314 numbered subject rows and 148 unnumbered artists across 24 sections are reconciled from original PDF clipping cells. '
          'Separate actor/character columns and all repeated dual signers are retained. Numeric-leading 10005 FIRE is a caption; IQ and John-Paul Howard are artists, not a card row. '
          'All 161 odds categories retain four literal physical columns; repeated disclaimers and headers are excluded from format names. '
          'The official guide joins 59 numbering specifications to exact family odds; its Reflections TBC 1/1 stays separate from the odds Superfractor. '
          'All three base sections share the base odds through explicit aliases. Guide/checklist composition discrepancies and missing NC-7/FO-8 remain explicit. '
          'The guide does not establish exhaustive parallel numbering; no general ratio unit or calendar release date is inferred.')
    data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,dedicatedParser=PARSER,coverageComplete=True,importKind='pdf',sectionColumn=0,odds=odds,formats=FORMATS,oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser=PARSER,formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=additions,
       publishedSpecifications=[dict(name='Manufacturer product fields',worksheet='Store availability and box contents are not pack odds or a general release date',headers=['Published field','Published value','Scope'],rows=proof['productFields'],**{**evidence,'source':proof['productSource']}),dict(name='Manufacturer guide qualifications',worksheet='Read directly from the official guide; exact numbered family joins appear with the published odds',headers=['Published field','Published value','Scope'],rows=proof['guideFields'],**evidence)],
       sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(sourcePage=proof['productSource'],rowCount=len(rows),sections=24,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=161,formats=4,verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser=PARSER,oddsImportIssues=0,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=proof['productSource']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[r for r in inventory if r['slug']!=SLUG]+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=additions;registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]
    registry['conflicts'].append(dict(slug=SLUG,family='Incomplete guide/odds and release-date reconciliation',gap=' '.join(proof['remainingGaps']),**evidence));rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Deadpool: 314 numbered subjects, 148 artists, 24 families, 161 odds/four formats, 59 exact numbered odds joins and one qualified TBC specification.')

if __name__=='__main__':build()
