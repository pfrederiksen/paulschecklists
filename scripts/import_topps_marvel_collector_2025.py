"""Read Marvel The Collector's original PDF clipping cells and literal odds."""
import collections,hashlib,json,logging,re
from pathlib import Path
import pdfplumber
from pypdf import PdfReader
from import_topps_tribute_2026 import acquire,text
from official_odds_layout import physical_odds_pdf
logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-marvel-the-collector'
PARSER='scripts/import_topps_marvel_collector_2025.py';PROOF=ROOT/'data/parallel-audit-sources/marvel-collector-2025-20261015.json'
HEADERS=['Checklist section','Card number','Player / subjects','Source page','Official text column 1','Official text column 2','Character','Property','Artist Name']
FAMILIES={'MCU PERFECTION','MARVEL TOMORROW','VILLAINY','SHOW STOPPERS','INFINITY GAUNTLET','MCU PERFECTION AUTOGRAPH VARIATION','DUAL AUTOGRAPHS','TREASURES OF ASGARD','INFINITY GAUNTLET AUTOGRAPH VARIATION','THE COLLECTORS MUSEUM','MILLER MAGNIFICENCE','MARVEL ARTHOUSE'}
FORMAT='Published odds (format not named)'

def cell_boxes(page):
    state={'clip':None,'pending':None};stack=[];boxes=set()
    def before(op,args,cm,tm):
        if op==b'q':stack.append(state.copy())
        elif op==b'Q':state.clear();state.update(stack.pop())
        elif op==b're':
            x,y,w,h=map(float,args)
            assert abs(cm[1])+abs(cm[2])<.001
            state['pending']=(x*cm[0]+cm[4],y*cm[3]+cm[5],(x+w)*cm[0]+cm[4],(y+h)*cm[3]+cm[5])
        elif op in {b'W',b'W*'}:state['clip']=state['pending']
    def visit(value,cm,tm,font,size):
        if value.strip():
            assert state['clip'] is not None
            boxes.add(state['clip'])
    page.extract_text(visitor_text=visit,visitor_operand_before=before)
    return boxes

def read_cards(path):
    rows=[];notes=[];raw=[];family=None;reader=PdfReader(path)
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==7
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text()))
            cells=collections.defaultdict(lambda:['','',''])
            for box in cell_boxes(reader.pages[pn-1]):
                column={36.:0,172.:1,344.:2}[box[0]]
                chars=[c for c in page.chars if box[0]<=c['x0']<box[2] and box[1]<=c['matrix'][5]<=box[3]]
                lines=collections.defaultdict(list)
                for c in chars:lines[round(c['matrix'][5],1)].append(c)
                value=' '.join(text(cs) for y,cs in sorted(lines.items(),reverse=True)).strip()
                key=(box[1],box[3]);assert not cells[key][column],(pn,key,column)
                cells[key][column]=value
            for bounds,values in sorted(cells.items(),key=lambda pair:pair[0][1],reverse=True):
                number,first,second=values
                if number in {'INSERT','AUTOGRAPH','SKETCH CARDS'}:notes.append([str(pn),*values]);continue
                if number in FAMILIES:
                    family=number
                    if first or second:notes.append([str(pn),*values])
                    continue
                assert family,(pn,values)
                artist=family in {'MILLER MAGNIFICENCE','MARVEL ARTHOUSE'}
                assert (not number and artist) or re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number),(pn,values)
                assert first and (not artist or not second),(pn,values)
                labeled=family in {'MCU PERFECTION','MARVEL TOMORROW'}
                rows.append([family,number,first,str(pn),first,second,first if labeled else '',second if labeled else '',first if artist else ''])
    assert sum(bool(r[1]) for r in rows)==262
    assert len({r[0] for r in rows})==12
    assert {int(r[1]) for r in rows if r[0]=='MCU PERFECTION'}==set(range(1,86))
    return rows,raw,notes

def build():
    proof=json.loads(PROOF.read_text());ph=hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence=dict(source=proof['productSource'],evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(record['checklistUrl'],path);rows,raw,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');oh=acquire(record['oddsUrl'],op);original,formats,odds_raw,issues=physical_odds_pdf(op)
    assert len(original)==59 and formats==['2025 Marvel The Collector'] and not issues
    odds=[]
    for odd in original:
        name=odd['name']
        family=next((f for f in sorted(FAMILIES,key=len,reverse=True) if name==f or name.startswith(f+' ')),None)
        if name.startswith("THE COLLECTOR'S MUSEUM AUTOGRAPH"):family='THE COLLECTORS MUSEUM'
        if name=='SKETCH CARD MARVEL ARTHOUSE':family='MARVEL ARTHOUSE'
        if name=='SKETCH CARD MILLER MAGNIFICENCE':family='MILLER MAGNIFICENCE'
        assert family,name
        odds.append({**odd,'family':family,'values':{FORMAT:odd['values'][formats[0]]}})
    artists=sum(not r[1] for r in rows)
    note=(f'All 262 numbered subject rows and {artists} unnumbered artists across 12 sections are reconciled using the original PDF clipping cells. '
          'Physical columns retain Character/Property values for MCU Perfection and Marvel Tomorrow and both unlabelled autograph text columns. '
          'Show Stoppers ST-8 retains its full two-line Black Widow Emerges Victorious caption. Wrapped autograph, Asgard, Museum and sketch headings remain single programs; '
          'all five duals retain both subjects. All 59 odds categories and literal ratios are preserved. The printed odds column names the product, not a pack format or ratio unit; '
          'the format control is disabled and no per-pack rate is inferred. Store Product Year 2026, Available From February 4, 2026 and the guide Debut Year 2026 remain separate '
          'from the 2025 checklist title and an unverified calendar release date. Serial-number specifications and exhaustive parallel reconciliation remain unverified.')
    data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,
      sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,dedicatedParser=PARSER,coverageComplete=True,
      importKind='pdf',sectionColumn=0,odds=odds,formats=[FORMAT],oddsSource=record['oddsUrl'],oddsSha256=oh,
      oddsRawPages=odds_raw,oddsIssues=[],oddsParser='scripts/official_odds_layout.py',officialOddsTable=original,
      officialOddsFormats=formats,officialOddsHeader=['Card',formats[0]],formatHeaderIsProductTitle=True,
      formatNamesPublished=False,oddsUnitsPublished=False,
      publishedSpecifications=[dict(name='Manufacturer product fields',worksheet='Store availability and box contents are not pack odds or a general release date',headers=['Published field','Published value','Scope'],rows=proof['productFields'],**evidence),
       dict(name='Manufacturer product guide',worksheet='Official guide read in the in-app browser',headers=['Published field','Published value','Scope'],rows=proof['guideFields'],source=proof['guideSource'],evidenceFile=evidence['evidenceFile'],evidenceSha256=ph)],
      sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(sourcePage=proof['productSource'],rowCount=len(rows),sections=12,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,
      odds=59,formats=1,verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser=data['oddsParser'],oddsImportIssues=0,
      sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=proof['productSource']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[r for r in inventory if r['slug']!=SLUG]+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]
    registry['conflicts'].append(dict(slug=SLUG,family='Unverified numbering, odds units and calendar release date',gap=' '.join(proof['remainingGaps']),**evidence));rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Marvel The Collector:',collections.Counter(r[0] for r in rows),';59 literal odds with product-title header, no inferred units.')

if __name__=='__main__':build()
