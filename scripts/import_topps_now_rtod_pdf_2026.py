"""Import the two RTOD landing-page PDFs by physical columns, never roster order."""
import datetime
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
import pdfplumber
import import_official_catalog as generic

ROOT=Path(__file__).resolve().parents[1]
LANDING='https://www.topps.com/pages/topps-now-road-to-opening-day'
TEAM_TITLE='2026 Topps NOW Road to Opening Day Team Sets Checklist'
BOX_TITLE="2026 Topps NOW Road to Opening Day - Autograph Collector's Box Subjects"
DUAL_TITLE="2026 Topps NOW Road to Opening Day - Autograph Collector's Box Dual-Auto Subjects"
GOLD_TITLE="2026 Topps NOW Road to Opening Day - Autograph Collector's Box Exclusive Gold Foil Parallels"
SLUG='topps-bowman-2026-rtod-topps-now-team-sets'
SOURCES={
 'teams':('https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Road_to_Opening_Day_Team_Sets_Checklist.pdf?v=1773955098','0dad58e985573cbff62ac41adc3ce7f19736446e094c6a326bc82196d201c104'),
 'box':('https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_RTOD_Autograph_Collectors_Box_Subject_List.pdf?v=1773955084','b16831c45302272f26b2e8bf0b94752cac94e28403eb355745f99468c562b03c')}
FAMILY_MAP={'On-card Autographs:':BOX_TITLE,'On-card Dual Autographs':DUAL_TITLE,'Exclusive Base Parallel (1 per box)':GOLD_TITLE}
GAP='The product describes a 300-player base checklist, while the linked Collector’s Box PDF publishes 56 autograph, nine dual-autograph and 194 exclusive Gold Foil rows. All 259 published PDF entries are imported. No separate 300-base-card box roster or unlisted eligibility is inferred from the team-set document.'


def document(kind):
    url,h=SOURCES[kind];path=ROOT/'data/catalog-sources/downloads'/('rtod-2026-'+kind+'-'+h+'.pdf')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==h
    return path,url,h


def parse(path,kind):
    out=[];family=TEAM_TITLE if kind=='teams' else BOX_TITLE;raw=[]
    cuts=[50,101,153,241,357,389,422] if kind=='teams' else [50,94,307,430,470,515]
    with pdfplumber.open(path) as doc:
        assert len(doc.pages)==(7 if kind=='teams' else 6)
        for page in doc.pages:
            raw.append({'page':page.page_number,'text':page.extract_text(x_tolerance=1,y_tolerance=1)})
            headings=[]
            for title in [BOX_TITLE,DUAL_TITLE,GOLD_TITLE] if kind=='box' else [TEAM_TITLE]:
                headings.extend((m['top'],title) for m in page.search(title,regex=False))
            # Crop the number column first: OD-277 touches PARALLELS in whole-page word extraction.
            codes=[w for w in page.crop((50,0,100 if kind=='teams' else 94,792)).extract_words(x_tolerance=1,y_tolerance=1) if re.fullmatch(r'(?:OD-\d+|A-[A-Z]+)',w['text'])]
            words=page.extract_words(x_tolerance=1,y_tolerance=1)
            for code in codes:
                current=[title for y,title in sorted(headings) if y<code['top']]
                if current:family=current[-1]
                cells=[]
                for left,right in zip(cuts,cuts[1:]):
                    cell=page.crop((left,code['top']-.2,right,code['bottom']+.2)).extract_text(x_tolerance=1,y_tolerance=1) or ''
                    assert '\n' not in cell,(kind,page.page_number,code['text'],cell)
                    cells.append(cell.strip())
                assert cells[0]==code['text'] and cells[-1] in {'','RC'},cells
                if kind=='teams':assert cells[1] in {'','PARALLELS'} and cells[2] and cells[3]
                else:assert cells[1] and cells[2]
                # Independent whole-page words: centers tolerate apostrophe font ascenders, while
                # a 3-point band excludes adjacent 15-point rows. Compare every original glyph.
                flow=[w for w in words if abs((w['top']+w['bottom']-code['top']-code['bottom'])/2)<3 and 49<w['x0']<cuts[-1]]
                squeeze=lambda s:re.sub(r'\s+','',s)
                assert squeeze(''.join(cells))==squeeze(''.join(w['text'] for w in sorted(flow,key=lambda w:w['x0']))),(page.page_number,cells,flow)
                out.append({'family':family,'cells':cells,'page':page.page_number})
    if kind=='teams':
        assert len(out)==300 and [r['cells'][0] for r in out]==['OD-'+str(n) for n in range(1,301)]
        assert len(Counter(r['cells'][3] for r in out))==30
        assert set(Counter(r['cells'][3] for r in out).values())=={10}
        assert sum(r['cells'][1]=='PARALLELS' for r in out)==110 and sum(r['cells'][-1]=='RC' for r in out)==50
    else:
        assert Counter(r['family'] for r in out)=={BOX_TITLE:56,DUAL_TITLE:9,GOLD_TITLE:194}
        assert sum(r['cells'][-1]=='RC' for r in out)==63
        assert all(' / ' in r['cells'][1] and r['cells'][3:]==['',''] for r in out if r['family']==DUAL_TITLE)
    return out,raw


def pdf_fields(payload,kind,raw):
    _,url,h=document(kind)
    payload.update(source=url,sha256=h,sourceKind='official-physical-column-pdf',sourceHashQualification='SHA-256 of the complete original official PDF bytes.',importKind='topps-grid-pdf',rawPages=raw,
        originalPrintedHeaders=['Card #','Parallels?','Player','Team','Pos.','RC'] if kind=='teams' else ['Card #','Player','Team','Pos.','RC'])
    payload.pop('rosterPublished',None)


def build():
    from import_topps_now_rtod_teams_2026 import TEAMS,build_one,FAMILY,identity
    from import_topps_now_rtod_special_2026 import build_box,BOX
    teams,traw=parse(document('teams')[0],'teams');box,braw=parse(document('box')[0],'box');results=[]
    record,payload,mappings=build_box()
    pdf_fields(payload,'box',braw)
    payload.update(headers=['Checklist section','Card number','Player','Team','Pos.','RC','Source page'],
        rows=[[r['family'],*r['cells'],str(r['page'])] for r in box],rookieColumn=5,coverageNote=GAP+' Nine exact guide terms join only their named PDF programs. Numeric pack odds, actual box print run, general release, exhaustive eligibility and historical NOW coverage remain unverified.')
    for s in payload['publishedSpecifications']:
        if s['name'] in FAMILY_MAP:
            s['name']=FAMILY_MAP[s['name']]
            for row in s['rows']:row[2]='Exact named product program, explicitly mapped to its corresponding PDF roster. No limits transfer to another family or to the regular team-set product.'
        else:
            s['name']='Set-wide Collector’s Box configuration and checklist scope'
            for row in s['rows']:
                if row[0]=='Published checklist claim':row[2]=GAP
                if row[0]=='Card and signer rosters':row[1]='259 published PDF entries';row[2]=GAP
    for m in mappings:m.update(family=FAMILY_MAP[m['family']],qualification='Exact named product program mapped to the corresponding PDF roster; no numbering transfers across families.')
    record.pop('rosterPublished',None)
    record.update(checklistUrl=SOURCES['box'][0],sha256=SOURCES['box'][1],rowCount=259,sections=3,status='Source table',importKind='topps-grid-pdf',dedicatedParser='scripts/import_topps_now_rtod_pdf_2026.py',
        description='All 259 published Collector’s Box PDF entries: 56 autograph subjects, nine dual-autograph cards and 194 exclusive Gold Foil parallels. Original card numbers, teams, positions and 63 RC marks are retained. Nine exact product-guide terms stay within their corresponding programs; Gold /26 applies only to the exclusive base parallel. The separate 300-player base claim remains qualified; no unlisted rows, pack odds, box run or general release is inferred.',
        catalogEvidence=GAP+' The official RTOD landing page links this document outside the global checklist catalog. Duals retain both printed signers and the literal Major League Baseball team where printed. Three eight-card packs are box configuration, not pack odds. March 20–April 6 sale dates remain separate from general release.',
        dataAudit='Every PDF cell is extracted inside its physical column and compared with independent whole-page original word flow. All six pages and three exact headings reconcile, including 63 RC marks and final OD-299 Willy Adames. Product proof hashes independently check all nine family-specific guide terms.')
    results.append((record,payload,mappings))
    _,url,h=document('teams')
    record={'title':TEAM_TITLE.removesuffix(' Checklist'),'manufacturer':'Topps / Bowman','sport':'baseball','year':'2026','slug':SLUG,'page':'sets/'+SLUG+'.html','sourcePage':LANDING,'checklistUrl':url,
        'releaseStatus':'Unverified','releaseDate':None,'verified':datetime.date.today().isoformat(),'tableData':'data/imports/'+SLUG+'.json','status':'Source table','importKind':'topps-grid-pdf',
        'dedicatedParser':'scripts/import_topps_now_rtod_pdf_2026.py','rowCount':300,'sections':1,'parallelData':True,'publishedOdds':False,'sha256':h,'coverageComplete':False,
        'description':'All 300 printed OD-1–OD-300 entries across thirty MLB team sets, with original Player, Team, Pos., RC and Parallels? columns. The PDF marks 110 parallel subjects and 50 rookies. Repeated Iván Herrera subjects retain distinct numbers and positions. This document does not publish a universal color ladder, pack odds or general release; exact product-specific terms remain on the reviewed team pages.',
        'catalogEvidence':'The official RTOD landing page links this complete team-set checklist outside the global catalog. PARALLELS marks remain literal eligibility annotations without inferred color combinations. This is the regular team-set PDF; no numbers or parallel terms transfer to the separate Japan Edition or to a missing box base program. Historical NOW coverage and exhaustive numbering audits remain partial.',
        'dataAudit':'All seven pages, 300 consecutive printed OD numbers, thirty ten-row team rosters, 110 PARALLELS and 50 RC marks reconcile by physical cells and independent word flow. OD-277 is split at its actual column boundary. OD-243/244 Iván Herrera retain OF and C/DH respectively.'}
    payload={
        'title':TEAM_TITLE.removesuffix(' Checklist'),'originalPrintedTitle':TEAM_TITLE,'headers':['Checklist section','Card number','Player','Team','Pos.','RC','Parallels?','Source page'],
        'rows':[[r['family'],r['cells'][0],*r['cells'][2:],r['cells'][1],str(r['page'])] for r in teams],'sectionColumn':0,'rookieColumn':5,
        'coverageNote':'Every published row in this PDF is imported. PARALLELS is a literal source mark, not a serial-number or named-color join. Other product-specific terms, historical coverage, general release and exhaustive numbering remain unverified.'}
    pdf_fields(payload,'teams',traw);results.append((record,payload,[]))
    for key in TEAMS:
        r,p=build_one(key);physical=[row for row in teams if re.sub('[®™]','',row['cells'][3])==TEAMS[key][0]]
        assert len(physical)==10
        by_name={row['cells'][2]:row for row in physical};assert len(by_name)==10
        new=[]
        for row in p['rows']:
            pdf=by_name[row[2]];c=pdf['cells']
            if key!='angels':assert bool(row[3])==bool(c[1])
            else:assert not row[3] and bool(c[1])==(c[0] in {'OD-111','OD-112'})
            new.append([FAMILY,c[0],*c[2:],c[1],row[3],row[4],SOURCES['teams'][0],str(pdf['page'])])
        pdf_fields(p,'teams',traw)
        p.update(headers=['Checklist section','Card number','Player','Team','Pos.','RC','Parallels?','Published web parallel-subject mark','Published web subject','Official source','Source page'],rows=new,rookieColumn=5,
            coverageNote='Ten exact team/name joins retain all printed PDF numbers, teams, positions, RC and PARALLELS marks alongside the original web subject cells. Angels has two PDF marks despite no inline web marks; both are retained separately. No subject/color combination is inferred; historical coverage and exhaustive eligibility remain partial.')
        for s in p['publishedSpecifications']:
            for row in s['rows']:
                if row[0]=='Printed card numbers':row[1]='Published in the linked regular team-set PDF';row[2]='Ten exact published team/name joins; no numbers derived from subject order or SKU.'
                if row[0]=='Per-row team / rookie fields':row[1]='Published in the linked regular team-set PDF';row[2]='Original Team, Pos., RC and Parallels? cells retained; blank marks remain blank.'
                if len(row)>1:row[1]=row[1].replace('subject/color combinations and printed card numbers are not supplied.','exact subject/color combinations are not supplied; printed IDs now come from the official team-set PDF.')
        r.update(checklistUrl=url,sha256=h,importKind='topps-grid-pdf',dedicatedParser='scripts/import_topps_now_rtod_pdf_2026.py',
            description=r['description'].replace('and blank unpublished card numbers','and printed PDF card numbers, teams, positions and RC fields'),
            catalogEvidence=r['catalogEvidence'].replace('Printed IDs, per-row team/rookie fields, pack odds and earned bonus rosters are not supplied.','Printed IDs, teams, positions, RC and PARALLELS marks now reconcile with the official regular team-set PDF. Pack odds and earned bonus rosters are not supplied.'),
            dataAudit=r['dataAudit']+' All ten names reconcile with physical PDF columns and exact printed team/name joins; original web cells remain separately exportable. PDF PARALLELS marks match web marks except Angels: its PDF explicitly marks Mike Trout and Christian Moore, while its web roster marks neither.')
        if key=='angels':
            for spec in p['publishedSpecifications']:
                if spec['name']==FAMILY:spec['rows'][0][1]='The web roster prints no inline parallel-subject marks; the official PDF explicitly marks OD-111 Mike Trout and OD-112 Christian Moore PARALLELS. Both fields are retained. Blank marks do not establish ineligibility, and no exact subject/color combinations are inferred.'
            r['description']=r['description'].replace('The source prints no parallel-subject markers despite the guaranteed parallel statement; eligibility remains unresolved.','The web roster has no inline marks, while the PDF explicitly marks Mike Trout and Christian Moore; both fields remain separate.')
        results.append((r,p,[]))
    for r,p,_ in results:
        assert generic.run(r.copy())==r
        (ROOT/r['tableData']).write_text(json.dumps(p,ensure_ascii=False)+'\n')
    for name in ['topps-product-official-catalog.json','set-catalog.json']:
        path=ROOT/'data'/name;catalog=json.loads(path.read_text());sets=catalog['sets'] if isinstance(catalog,dict) else catalog
        for r,_,_ in results:
            i=next((i for i,s in enumerate(sets) if s['slug']==r['slug']),None)
            if i is None:sets.append(r)
            else:sets[i]=r
        path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    path=ROOT/'data/parallel-specifications.json';reg=json.loads(path.read_text())
    for r,_,m in results:reg['sets'][r['slug']]=m
    path.write_text(json.dumps(reg,ensure_ascii=False,indent=2)+'\n')
    print('Imported 300 physical team-set cards and 259 Collector’s Box entries; backfilled exact numbers/teams/RC for 13 existing team pages. Nine box guide limits stay in exact families; Japan Edition and historical gaps remain separate.')

if __name__=='__main__':build()
