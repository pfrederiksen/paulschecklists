"""Read Star Wars Chrome original glyph origins and every ruled odds category."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-star-wars-chrome'
PARSER='scripts/import_topps_star_wars_chrome_2026.py';PROOF=ROOT/'data/parallel-audit-sources/star-wars-chrome-2026-20261015.json'
HEADERS=['Checklist section','Card number','Player / subjects','Source page','Official text column 1','Official text column 2','Official text column 3','Artist Name']
FAMILIES={'CHARACTERS','CHARACTERS HOTHFRACTOR','CHARACTERS AUREBESH','BASE PRINTING PLATE BOOK CARDS I','CHARACTERS AUTOGRAPHS','TRIPLE AUTOGRAPHS','COSMIC CRYSTALS','MANDO AND GROGU CHARACTERS','STORMTROOPER COMMAND','ANDOR SEASON 2 CHARACTERS','MANDO AND GROGU MOMENTS','OBLIVION','GALAXYS CUTEST','VISIONS SEASON 3 CHARACTERS','ANDOR SEASON 2 CHARACTERS AUTOGRAPHS','ANDOR SEASON 2 MOMENTS','BONUS STAGE','FACTIONS','KYBER LIGHT','VISIONS SEASON 3 MOMENTS','GALATIC MAXIMALISTS','ERAS','HIDDEN GEMS','REFLECTIONS','COMICFRACTOR','MANDO AND GROGU CHARACTERS AUTOGRAPHS','VISIONS SEASON 3 CHARACTERS AUTOGRAPHS','DUO AUTOGRAPHS','SKETCH ARTISTS'}

def read_cards(path):
    rows=[];raw=[];notes=[];family=None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==31
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
            for c in page.chars:groups[round(c['matrix'][5],1)].append(c)
            for y,cs in sorted(groups.items(),reverse=True):
                line=text(cs)
                if not line:continue
                if line.startswith(('Checklists provided','production, but actual','but actual contents')):notes.append([str(pn),line]);continue
                if line in FAMILIES:family=line;continue
                if line in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPHS'}:continue
                assert family,(pn,line)
                if family=='SKETCH ARTISTS':rows.append([family,'',line,str(pn),line,'','',line]);continue
                # Original drawing order, not glyph x-sort, separates long
                # codes/names from adjacent cells even when their ink overlaps.
                starts=[max([i for i,c in enumerate(cs) if abs(c['matrix'][4]-x)<.16],default=-1) for x in [129.38,273.35,425.25]]
                assert starts[0]>=1,(pn,line,starts)
                anchors=[0,*[i for i in starts if i>=0],len(cs)]
                assert anchors==sorted(set(anchors)),(pn,line,anchors)
                number=text(cs[:starts[0]]);values=[]
                for i,start in enumerate(starts):
                    end=next((j for j in starts[i+1:] if j>=0),len(cs));values.append(text(cs[start:end]) if start>=0 else '')
                assert re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',number) and values[0],(pn,number,values)
                rows.append([family,number,values[0],str(pn),*values,''])
    return rows,raw,notes

def read_odds(path):
    odds=[];raw=[];formats=['HOBBY','DELIGHT','SAPPHIRE','VALUE BOX','CLUB SUPER BOX'];notes=[]
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==5
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text()));tables=page.find_tables();assert len(tables)==1
            for i,row in enumerate(tables[0].rows):
                assert len(row.cells)==6 and all(row.cells),(pn,i)
                cells=[]
                for box in row.cells:
                    lines=collections.defaultdict(list)
                    for c in page.chars:
                        if box[0]<=(c['x0']+c['x1'])/2<box[2] and box[1]<=(c['top']+c['bottom'])/2<box[3]:lines[round(c['matrix'][5],1)].append(c)
                    cells.append(' '.join(text(cs) for y,cs in sorted(lines.items(),reverse=True)).strip())
                if i==0:assert cells==['Card',*formats];continue
                if not cells[0]:assert all(v in {'','-'} for v in cells[1:]),(pn,cells);notes.append([str(pn),*cells]);continue
                assert all(v in {'','-'} or re.fullmatch(r'[\d,.]+(?::[\d,.]+)+',v) for v in cells[1:]),(pn,cells)
                odds.append(dict(name=cells[0],values=dict(zip(formats,[None if v in {'','-'} else v for v in cells[1:]])),page=pn))
    assert len(odds)==186,(len(odds),len(notes))
    return odds,formats,raw,notes


def build():
    proof=json.loads(PROOF.read_text());ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();evidence=dict(source=proof['productSource'],evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);odds,formats,odds_raw,odds_notes=read_odds(op)
    assert digest==proof['checklistSha256'] and oh==proof['oddsSha256'] and len(rows)==1502 and sum(bool(r[1]) for r in rows)==1369
    aliases={f:f for f in FAMILIES if f not in {'SKETCH ARTISTS','DUO AUTOGRAPHS','TRIPLE AUTOGRAPHS','CHARACTERS AUTOGRAPHS','BASE PRINTING PLATE BOOK CARDS I','GALAXYS CUTEST','GALATIC MAXIMALISTS','MANDO AND GROGU CHARACTERS','MANDO AND GROGU MOMENTS','MANDO AND GROGU CHARACTERS AUTOGRAPHS','ANDOR SEASON 2 CHARACTERS AUTOGRAPHS','VISIONS SEASON 3 CHARACTERS AUTOGRAPHS'}}
    aliases.update({'CHARACTERS AUTOGRAPH':'CHARACTERS AUTOGRAPHS','CHARACTERS HOTH FROZENFRACTOR':'CHARACTERS HOTHFRACTOR','PRINTING PLATE BOOK CARD':'BASE PRINTING PLATE BOOK CARDS I','GALACTIC MAXIMALISTS':'GALATIC MAXIMALISTS',"THE GALAXY'S CUTEST":'GALAXYS CUTEST','MANDO & GROGU CHARACTERS':'MANDO AND GROGU CHARACTERS','MANDO & GROGU MOMENTS':'MANDO AND GROGU MOMENTS','MANDO & GROGU CHARACTERS AUTOGRAPH':'MANDO AND GROGU CHARACTERS AUTOGRAPHS','ANDOR SEASON 2 CHARACTERS AUTOGRAPH':'ANDOR SEASON 2 CHARACTERS AUTOGRAPHS','VISIONS SEASON 3 CHARACTERS AUTOGRAPH':'VISIONS SEASON 3 CHARACTERS AUTOGRAPHS','DUO AUTOS':'DUO AUTOGRAPHS','TRIO AUTOS':'TRIPLE AUTOGRAPHS','SKETCH CARDS':'SKETCH ARTISTS','KYBER CARVINGS':'KYBER CARVINGS','CHARACTERS DESIGN VARIATION':'CHARACTERS DESIGN VARIATION'})
    for odd in odds:
        prefix=next((a for a in sorted(aliases,key=len,reverse=True) if odd['name']==a or odd['name'].startswith(a+' ')),None)
        assert prefix,odd['name'];odd.update(family=aliases[prefix],familyBase=odd['name']==prefix)
    additions=[dict(family='BASE PRINTING PLATE BOOK CARDS I',name='Printing Plate Book Card',numbering='1/1',oddsName='PRINTING PLATE BOOK CARD',qualification='Published for this family; individual-card eligibility is not inferred.',**evidence)]
    note=('All 1,369 coded subject rows and 133 unnumbered artists across 29 sections are reconciled using original glyph drawing order and physical column origins. '
          'All four 200-card programs remain separate, including the printed PALTE-194 code; actor/character cells and literal DEBUT columns are retained without rookie flags. '
          'GMAX-CHEWIE Chewbacca is restored, long actor names retain their overlapping source cells, and every duo/triple signer is kept. '
          'All 186 named odds categories retain five literal format columns; 11 entirely unnamed spacer rows are retained as source notes, not invented categories. '
          'Printing Plate Book Cards alone retain the product’s explicit 1/1 claim. Other numbering, odds-only roster joins, ratio units and a general calendar release date remain unverified.')
    data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,dedicatedParser=PARSER,coverageComplete=True,importKind='pdf',sectionColumn=0,odds=odds,formats=formats,oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsSourceNotes=odds_notes,oddsIssues=[],oddsParser=PARSER,formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=additions,publishedSpecifications=[dict(name='Manufacturer product fields',worksheet='Store availability, box contents and exact named-program numbering retain their separate scopes',headers=['Published field','Published value','Scope'],rows=proof['productFields'],**evidence)],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=proof['productSource'],rowCount=len(rows),sections=29,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=186,formats=5,verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser=PARSER,oddsImportIssues=0,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=proof['productSource']));cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());ip.write_text(json.dumps([r for r in inventory if r['slug']!=SLUG]+[record],ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=additions;registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG];registry['conflicts'].append(dict(slug=SLUG,family='Unjoined odds-only rosters, unverified numbering and ratio units',gap=' '.join(proof['remainingGaps']),**evidence));rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Star Wars Chrome: 1,369 coded subjects, 133 artists, 29 families, all 186 odds/five formats and the exact Printing Plate Book 1/1 scope.')

if __name__=='__main__':build()
