"""Physical imports for the October 15 Chrome Football and GPK checklist drops."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from import_official_catalog import run
from import_topps_tribute_2026 import acquire, text
from official_odds_layout import physical_odds_pdf

ROOT=Path(__file__).resolve().parents[1];PARSER='scripts/import_topps_october15_2026.py'
PROOF=ROOT/'data/parallel-audit-sources/topps-october15-2026-products.json'
FOOTBALL='topps-bowman-2026-topps-chrome-football'
GPK='topps-bowman-2026-garbage-pail-kids-halloween'

def football_rows(path):
    rows=[];notes=[];family=None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==49
        for pn,page in enumerate(pdf.pages,1):
            groups=collections.defaultdict(list)
            for c in page.chars:groups[round(c['matrix'][5],1)].append(c)
            for y,cs in sorted(groups.items(),reverse=True):
                line=text(cs)
                if pn==1 and y>680:notes.append([str(pn),line]);continue
                if any('Bold' in c['fontname'] for c in cs):
                    if line not in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPH RELIC','RELIC'}:family=line
                    continue
                assert family,(pn,line)
                number,name,team,rookie=[text([c for c in cs if a<=c['x0']<b]) for a,b in [(0,130),(130,270),(270,420),(420,620)]]
                assert rookie in {'','Rookie'} and team,(pn,line,rookie)
                assert re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',number) or (not number and family=='FANATICS AUTHENTICS REDEMPTION CARD'),(pn,line)
                rows.append([family,number,name,team,rookie,str(pn)])
    assert len(rows)==2382 and len({r[0] for r in rows})==56
    assert sum(r[4]=='Rookie' for r in rows)==644
    return ['Checklist section','Card number','Name','Team','Rookie','Source page'],rows,notes,[]

def gpk_rows(path):
    rows=[];notes=[];specs=[];family='Base'
    headings={'C NAMES','SLIME BASE PARALLELS','WRAPPERS','WRAPPER PARALLEL','SCREAM QUEENS','ART VARIATION','AUTOGRAPHS','SKETCH CARD ARTIST'}
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==5
        for pn,page in enumerate(pdf.pages,1):
            groups=[]
            # The original table uses different fonts/baselines in adjacent
            # cells. Group within two points, far below the 15-point row pitch.
            for c in sorted(page.chars,key=lambda c:c['top']):
                cs=next((cs for y,cs in groups if abs(y-c['top'])<2),None)
                if cs is None:cs=[];groups.append((c['top'],cs))
                cs.append(c)
            for y,cs in groups:
                line=text(sorted(cs,key=lambda c:c['x0']))
                if pn==1 and y<100:notes.append([str(pn),line]);continue
                if line in headings:family=line;continue
                cells=[text(sorted([c for c in cs if a<=c['x0']<b],key=lambda c:c['x0'])) for a,b in [(0,140),(140,190),(190,325),(325,620)]]
                number,subset,name,back=cells
                if family in {'SLIME BASE PARALLELS','WRAPPERS','WRAPPER PARALLEL'}:
                    specs.append([family,*cells,str(pn)]);continue
                if family=='SKETCH CARD ARTIST':
                    assert not number and not subset and not back
                    rows.append([family,'',name,'',str(pn),'','','',name]);continue
                assert re.fullmatch(r'\d+[ABC]?',number) and subset in {'Base','Insert','Variation','Autos'} and name,(pn,cells)
                rows.append([family,number,name,subset,str(pn),back if family!='AUTOGRAPHS' else '',back if family=='AUTOGRAPHS' else '',back,''])
    assert collections.Counter(r[0] for r in rows)=={'Base':50,'C NAMES':25,'SCREAM QUEENS':10,'ART VARIATION':10,'AUTOGRAPHS':10,'SKETCH CARD ARTIST':53}
    assert len(specs)==7 and len(rows)==158
    return ['Checklist section','Card number','Name','Subset','Source page','Card Back','Autograph artist','Official fourth column','Sketch artist'],rows,notes,specs

def build():
    proof=json.loads(PROOF.read_text());evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());records=[]
    for slug,parser in [(FOOTBALL,football_rows),(GPK,gpk_rows)]:
        src=proof[slug];path=ROOT/'data/catalog-sources/downloads'/(slug+'.pdf');digest=acquire(src['checklistUrl'],path)
        headers,rows,notes,specs=parser(path)
        record=next((s for s in catalog['sets'] if s['slug']==slug),None)
        if record is None:
            record=dict(title=src['title'],manufacturer='Topps / Bowman',sport=src['sport'],year='2026',slug=slug,
              page='sets/'+slug+'.html',sourcePage=src['source'],checklistUrl=src['checklistUrl'],releaseStatus='Upcoming',releaseDate=None,verified=proof['observed'])
            record=run(record);assert record.get('tableData');catalog['sets'].append(record)
        data=json.loads((ROOT/record['tableData']).read_text())
        data.update(headers=headers,rows=rows,originalSubjectHeaders=headers,originalSubjectRows=rows,sha256=digest,
          dedicatedParser=PARSER,sectionColumn=0,unclassifiedLines=[],sourceDocumentNotes=notes,coverageComplete=True,
          odds=[],formats=[],formatNamesPublished=False,oddsUnitsPublished=False)
        ev=dict(source=src['source'],**evidence)
        if slug==FOOTBALL:
            note=('All 2,382 original subject rows across 56 sections retain Name, Team and 644 literal Rookie marks. '
              'Three 300-card veteran programs and three 100-card rookie programs remain separate. All 93 unnumbered Fanatics '
              'Authentics redemption subjects, repeated dual signers, printed team differences and numeric 1991/2016/2017/2018 '
              'section headings are preserved. The October 16 FDI auction is explicitly a preorder, not a verified release date. '
              'No odds PDF or serial-number ladder is linked by the checked product page or global odds catalog; those audits remain pending.')
            data['publishedSpecifications']=[dict(name='First Day Issue box configuration',worksheet='FDI product page only; box contents are not pack odds',headers=['Published field','Published value'],rows=src['boxContents'],**ev)]
            data['importKind']='topps-grid-pdf'
        else:
            op=path.with_name(slug+'-odds.pdf');oh=acquire(src['oddsUrl'],op);odds,formats,raw,issues=physical_odds_pdf(op)
            assert len(odds)==12 and formats==['SINGLE BOX'] and not issues
            for o in odds:
                o['qualification']='Published SINGLE BOX ratio; not a per-pack rate.'
                o['family']=('Base' if o['name'].startswith('BASE CARDS ') else {'WRAPPER RAINBOW FOIL':'WRAPPERS','SKETCH CARDS':'SKETCH CARD ARTIST','ARTWORK VARIATIONS':'ART VARIATION','ARTIST AUTOGRAPHS':'AUTOGRAPHS'}.get(o['name'],o['name']))
            data.update(odds=odds,formats=formats,oddsSource=src['oddsUrl'],oddsSha256=oh,oddsRawPages=raw,
              oddsIssues=[],oddsParser='scripts/official_odds_layout.py',formatNamesPublished=True,oddsUnitsPublished=True,oddsUnitLabel='SINGLE BOX')
            data['importKind']='pdf'
            data['publishedSpecifications']=[dict(name='Original checklist parallel and wrapper rows',worksheet='Original PDF cells; summary rows are not expanded into invented card rosters',headers=['Published heading','Card # / scope','Subset','Name','Card Back / numbering','Source page'],rows=specs,**ev),
              dict(name='Sketch artwork',worksheet='Official product page; artwork uniqueness does not number the artist roster',headers=['Published field','Published value','Qualification'],rows=[['Sketch Cards','1/1 sketches','Artwork uniqueness, not a serial limit on the 53 listed artists.']],**ev)]
            record.update(oddsUrl=src['oddsUrl'],oddsParser=data['oddsParser'],oddsImportIssues=0)
            note=('All 105 numbered card rows and 53 unnumbered sketch artists across six checklist sections retain the printed '
              'Subset, Name and Card Back / autograph-artist cells. The 50 Base, 25 C Names, ten Scream Queens, ten Art Variation '
              'and ten autograph rows remain distinct, including matching A/B codes and five blank Scream Queens backs. '
              'All 12 literal SINGLE BOX odds are imported from the product-page PDF, not converted to per-pack rates. '
              'Five Base Slime limits are joined only to the corresponding Base Foil odds names, preserving both published '
              'names and /50, /25, /10, /5 and /1 limits. Wrapper Rainbow Foil has no published limit; the 25-subject wrapper '
              'summary is not expanded into an inferred roster. Final Artwork Redemption is odds-only. Release is scheduled '
              'October 22; exhaustive parallel reconciliation remains unconfirmed.')
        data['sourceSheets']=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in src['remainingGaps']]])]
        (ROOT/record['tableData']).write_text(json.dumps(data,ensure_ascii=False)+'\n')
        record.update(status='Source table',rowCount=len(rows),sections=len({r[0] for r in rows}),sha256=digest,
          importKind=data['importKind'],dedicatedParser=PARSER,coverageComplete=True,verified=proof['observed'],
          catalogEvidence=note,dataAudit=note,odds=len(data['odds']),formats=len(data['formats']))
        records.append(record)
        print(src['title'],len(rows),'source rows;',len(data['odds']),'published odds categories')
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    p=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(p.read_text())
    for record in records:
        inventory=[r for r in inventory if r['slug']!=record['slug']]+[record]
    p.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    for slug,filename in [(FOOTBALL,'topps-official-catalog.json'),(GPK,'entertainment-topps-catalog.json')]:
        p=ROOT/'data'/filename;inventory=json.loads(p.read_text());src=proof[slug]
        if not any(r['url']==src['checklistUrl'] for r in inventory):inventory.append(dict(title=src['title'],url=src['checklistUrl'],observed=proof['observed']))
        p.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    p=ROOT/'data/topps-official-odds.json';inventory=json.loads(p.read_text());src=proof[GPK]
    if not any(r['url']==src['oddsUrl'] for r in inventory):inventory.append(dict(title=src['title'],url=src['oddsUrl'],source=src['source'],sha256=hashlib.sha256((ROOT/'data/catalog-sources/downloads'/(GPK+'-odds.pdf')).read_bytes()).hexdigest()))
    p.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    p=ROOT/'data/parallel-specifications.json';registry=json.loads(p.read_text())
    registry['sets'][GPK]=[dict(family='Base',name=color+' Slime' if color!='Foil Fractor' else color,numbering=number,
      oddsName=odds_name,source=proof[GPK]['checklistUrl'],qualification='Base subjects only. Checklist Slime wording and the corresponding base Foil odds name are retained; no other family receives this limit.',**evidence)
      for color,number,odds_name in [('Gold','/50','BASE CARDS GOLD FOIL PARALLEL'),('Orange','/25','BASE CARDS ORANGE FOIL PARALLEL'),('Black','/10','BASE CARDS BLACK FOIL PARALLEL'),('Red','/5','BASE CARDS RED FOIL PARALLEL'),('Foil Fractor','/1','BASE CARDS FOILFRACTOR PARALLEL')]]
    registry['conflicts']=[c for c in registry['conflicts'] if c['slug'] not in {FOOTBALL,GPK}]
    for slug in [FOOTBALL,GPK]:registry['conflicts'].append(dict(slug=slug,family='Outstanding source reconciliation',gap=' '.join(proof[slug]['remainingGaps']),source=proof[slug]['source'],**evidence))
    p.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':build()
