"""Keep the Japanese-language team edition and Collector's Box guide evidence distinct."""
import datetime
import hashlib
import json
from pathlib import Path
import import_official_catalog as generic

ROOT=Path(__file__).resolve().parents[1]
JAPAN='topps-bowman-2026-rtod-topps-now-dodgers-japan-edition'
BOX='topps-bowman-2026-rtod-topps-now-autograph-collectors-box'
JPAGE='https://www.topps.com/products/2026-los-angeles-dodgers-mlb-topps-now%C2%AE-road-to-opening-day-10-card-team-set-japan-edition'
BPAGE='https://www.topps.com/products/2026-mlb-topps-now%C2%AE-road-to-opening-day-autograph-collector-s-box'
JPROOF='data/parallel-audit-sources/rtod-now-dodgers-japan-2026-product-20261018.json'
BPROOF='data/parallel-audit-sources/rtod-now-collector-box-2026-product-20261018.json'
FAMILY='Subject List:'
PROGRAMS={'On-card Autographs:':[('/99','Green Foil'),('/50','Gold Foil'),('/25','Orange Foil'),('/10','Black Foil'),('/5','Red Foil'),('1/1','FoilFractor')],
          'On-card Dual Autographs':[('/5','Red Foil'),('1/1','FoilFractor')],
          'Exclusive Base Parallel (1 per box)':[('/26','Gold Foil')]}
GAP='The official product claims a 300-player checklist but does not publish player names, card numbers, an autograph/dual-signer roster or a linked checklist document on the reviewed page. Card-level import remains pending; the 300-player claim is not an imported count.'


def proof(file,page):
    p=ROOT/file;d=json.loads(p.read_text());h=hashlib.sha256(p.read_bytes()).hexdigest()
    assert d['url']==page and d['documentLinks']==[] and d['sourceKind']=='official-browser-product-factual-excerpt'
    fields=dict(d['specs']);assert fields['Available From']=='Mar 20, 2026' and fields['Available Until']=='Apr 6, 2026' and fields['Product Year']=='2026'
    assert fields['Sub Categories']=='Baseball' and fields['Sub Type']=='Online Exclusive Box'
    return d,h,fields,{'evidenceFile':file,'evidenceSha256':h}


def common_record(slug,page,d,h,kind):
    return {'title':d['title'],'manufacturer':'Topps / Bowman','sport':'baseball','year':'2026','slug':slug,'page':'sets/'+slug+'.html',
        'sourcePage':page,'checklistUrl':page,'releaseStatus':'Unverified','releaseDate':None,'verified':datetime.date.today().isoformat(),
        'tableData':'data/imports/'+slug+'.json','status':'Source table','importKind':kind,'dedicatedParser':'scripts/import_topps_now_rtod_special_2026.py',
        'publishedOdds':False,'sha256':h,'coverageComplete':False}


def build_japan():
    d,h,fields,e=proof(JPROOF,JPAGE)
    assert d['title']=='2026 Los Angeles Dodgers MLB Topps NOW® Road To Opening Day 10-Card Team Set - Japan Edition - PR: 4693'
    lines=[s.strip() for s in d['description'].splitlines() if s.strip()];cells=[s.strip() for s in d['descriptionParagraphs'] if s.strip()]
    assert lines==cells and lines[1]==FAMILY and lines[-1].startswith('All sales are final.')
    subjects=lines[2:-1];assert len(subjects)==10 and subjects==['Shohei Ohtani','Mookie Betts','Freddie Freeman','Roki Sasaki','Will Smith','Yoshinobu Yamamoto','Edwin Díaz','Teoscar Hernández','Kyle Tucker','Blake Snell']
    assert [s.strip() for s in d['overview'].splitlines() if s.strip()]==[s.strip() for s in d['overviewCells'] if s.strip()]==['Japan Edition Dodgers Team Set featuring Japanese language','Includes (10) Base Cards']
    assert fields['Properties']=='Los Angeles Dodgers' and fields['Product Type']=='Print on Demand'
    rows=[[FAMILY,'',name,name,JPAGE] for name in subjects]
    specs=[{'name':'Set-wide Japan Edition configuration and sale dates','worksheet':'Official title, Overview and Specs · edition scope','source':JPAGE,
        'headers':['Official field','Official value','Qualification'],
        'rows':[['Edition statement','Japan Edition Dodgers Team Set featuring Japanese language','Source roster names are published in English; no Japanese player-name transliterations are invented.'],
                ['Published contents','Includes (10) Base Cards','Separate ten-card Japanese-language edition; no extra parallel is stated in the reviewed page.'],
                ['Published bundle print run','4693','Whole Japan Edition bundle run, not a per-card run.'],
                ['Printed card numbers','Not published','Blank IDs are retained.'],
                ['Parallel / bonus / box-inclusion terms','Not published','Do not transfer the regular eleven-card product’s foil ladder, guarantee, bonus milestones or included-356 statement.'],
                *[[k,v,'Official sale window, not a general release date.' if k.startswith('Available ') else ''] for k,v in fields.items()]],**e}]
    payload={'title':d['title'],'headers':['Checklist section','Card number','Player / subjects','Published subject','Official source'],'rows':rows,
        'source':JPAGE,'sha256':h,'sourceKind':d['sourceKind'],'sourceHashQualification':'SHA-256 of the retained normalized official browser factual snapshot, not raw HTML.',
        'importKind':'topps-web-roster','sectionColumn':0,'publishedSpecifications':specs,'sourceProducts':[{**d,'snapshotFile':JPROOF,'sha256':h}],
        'coverageNote':'All ten published Japan Edition subjects are imported with blank unpublished IDs. No parallel ladder, bonus milestones, pack odds or general release is supplied; historical NOW coverage remains partial.'}
    record=common_record(JAPAN,JPAGE,d,h,'topps-web-roster');record.update(rowCount=10,sections=1,parallelData=False,
        description='All ten official Dodgers Japan Edition subjects are imported with blank unpublished card numbers. The product describes a Japanese-language ten-base-card edition and labels bundle PR4693. No regular-edition parallel ladder, extra-card guarantee, bonus milestones or Collector’s Box contribution is copied. March 20–April 6 sale dates remain separate from an unverified general release; historical coverage stays partial.',
        catalogEvidence='Fresh official product Overview and Description publish the separate Japan Edition, its ten English-language subject cells and no parallel or bonus program. Preserve Edwin Díaz and Teoscar Hernández. Printed IDs, row-level team/rookie fields, pack odds and general release are unverified. The regular Dodgers eleven-card set’s /199-/150 and other foils, bonus terms and included-356 qualifier do not apply to this source.',
        dataAudit='All ten original DOM paragraphs reconcile with the complete Description text; source Overview independently confirms the ten-base-card configuration. Product-language, bundle PR, sale dates and missing fields retain edition scope.')
    return record,payload,[]


def build_box():
    d,h,fields,e=proof(BPROOF,BPAGE)
    assert d['title']=='2026 MLB Topps NOW® Road To Opening Day – Autograph Collector’s Box' and fields['Properties']=='Major League Baseball' and fields['Product Type']=='Hobby'
    lines=[s.strip() for s in d['description'].splitlines() if s.strip()];cells=[s.strip() for s in d['descriptionParagraphs'] if s.strip()];assert lines==cells
    assert lines[0]=='2026 Topps NOW Road to Opening Day kicks off the 2026 MLB season with a checklist featuring 300 players across the League and exclusive Spring Training photography.'
    headings=[*PROGRAMS,lines[-1]];specs=[];mappings=[]
    for family,stop in zip(headings,headings[1:]):
        terms=PROGRAMS[family];assert lines[lines.index(family)+1:lines.index(stop)]==[n+' '+name for n,name in terms]
        qualifier='Exact named product program only. Player/signer eligibility and the card roster remain unpublished; no limits transfer to another family.'
        specs.append({'name':family,'worksheet':'Official Description · '+family,'source':BPAGE,
            'headers':['Published parallel','Published numbering','Qualification','Official source'],
            'rows':[[name,n,qualifier,BPAGE] for n,name in terms],**e})
        mappings.extend(dict(family=family,name=name,numbering=n,qualification=qualifier,sourceHeading=family,source=BPAGE,**e) for n,name in terms)
    overview=[s.strip() for s in d['overview'].splitlines() if s.strip()]
    assert overview==[s.strip() for s in d['overviewCells'] if s.strip()]
    assert 'three 8-card packs' in overview[1] and 'gold foil parallel numbered to 26' in overview[1] and 'on-card autograph numbered to 99 or less' in overview[1]
    assert 'numbered to five or less' in overview[2]
    specs.append({'name':'Set-wide Collector’s Box configuration and roster gap','worksheet':'Official Overview, Description and Specs · box scope','source':BPAGE,
        'headers':['Official field','Official value','Qualification'],
        'rows':[['Published checklist claim','300 players',GAP],
                ['Published box configuration',overview[1],'Box contents and guaranteed box-level categories, not pack odds. Do not compute a per-pack rate.'],
                ['Published dual-autograph statement',overview[2],'Qualified five-or-less statement; only the two separately printed dual colors receive exact limits.'],
                ['Actual box print run','Not published','No labelled actual print run is present in the reviewed product title or Specs; do not infer 356 from another product’s included-box qualifier.'],
                ['Card and signer rosters','Not published',GAP],
                *[[k,v,'Official sale window, not a general release date.' if k.startswith('Available ') else 'Hobby is retained as Product Type, not an invented pack-odds format.' if k=='Product Type' else ''] for k,v in fields.items()]],**e})
    payload={'title':d['title'],'headers':['Checklist section','Card number','Player / subjects','Official source'],'rows':[],
        'rosterPublished':False,'publishedChecklistClaim':'300 players','source':BPAGE,'sha256':h,'sourceKind':d['sourceKind'],
        'sourceHashQualification':'SHA-256 of the retained normalized official browser factual snapshot, not raw HTML.',
        'importKind':'topps-web-specifications','sectionColumn':0,'oddsUnitsPublished':False,'formatNamesPublished':False,
        'publishedSpecifications':specs,'sourceProducts':[{**d,'snapshotFile':BPROOF,'sha256':h}],
        'coverageNote':GAP+' Nine exact program/parallel terms are imported. Numeric pack odds, actual box print run, general release and historical NOW coverage remain unverified.'}
    record=common_record(BOX,BPAGE,d,h,'topps-web-specifications');record.update(rowCount=0,sections=0,parallelData=True,rosterPublished=False,status='Official source',
        description='Source-only: card roster pending. The official product claims 300 players but supplies no player/card-number or signer list and no linked checklist document. Nine exact terms are imported across on-card autographs, dual autographs and the exclusive base parallel. Three eight-card packs and box guarantees retain their original units; no pack odds, actual box run or general release is inferred.',
        catalogEvidence=GAP+' Six on-card autograph colors, two dual-autograph colors and exclusive base Gold /26 retain exact scopes. Gold /26 does not number the autograph families. March 20–April 6 store dates are separate from general release. Hobby is a Product Type, not a named pack-odds column. Historical coverage stays partial.',
        dataAudit='The full Description and independent DOM paragraph cells reconcile all nine exact family terms. Empty card rows explicitly mean roster unavailable, not a zero-card product. The 300-player claim is retained as context and never used as an imported-row count.')
    return record,payload,mappings


def build():
    results=[build_japan()]
    for record,payload,_ in results:
        assert generic.run(record.copy())==record
        (ROOT/record['tableData']).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
    for name in ['topps-product-official-catalog.json','set-catalog.json']:
        p=ROOT/'data'/name;catalog=json.loads(p.read_text());sets=catalog['sets'] if isinstance(catalog,dict) else catalog
        for record,_,_ in results:
            i=next((i for i,s in enumerate(sets) if s['slug']==record['slug']),None)
            if i is None:sets.append(record)
            else:sets[i]=record
        p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    p=ROOT/'data/parallel-specifications.json';registry=json.loads(p.read_text())
    for record,_,mappings in results:registry['sets'][record['slug']]=mappings
    p.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    from import_topps_now_rtod_pdf_2026 import build as apply_pdf
    apply_pdf()
    print('Imported ten distinct Japan Edition subjects and reconciled the Collector’s Box physical PDF with exact product guide terms.')

if __name__=='__main__':build()
