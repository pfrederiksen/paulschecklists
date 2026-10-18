"""Import literal Road to Opening Day rosters, inline marks and qualified bundle terms."""
import datetime
import hashlib
import json
import re
from pathlib import Path
import import_official_catalog as generic

ROOT=Path(__file__).resolve().parents[1]
TEAMS={
 'washington-nationals':('Washington Nationals','649',4),
 'miami-marlins':('Miami Marlins','541',1),
 'baltimore-orioles':('Baltimore Orioles','1141',6),
 'los-angeles-dodgers':('Los Angeles Dodgers','5721',10),
 'san-diego-padres':('San Diego Padres','796',3),
 'arizona-diamondbacks':('Arizona Diamondbacks','643',2),
 'texas-rangers':('Texas Rangers','705',3),
 'toronto-blue-jays':('Toronto Blue Jays','731',2),
 'atlanta-braves':('Atlanta Braves','1095',4),
 'houston-astros':('Houston Astros','759',3),
 'athletics':('Athletics','921',3),
 'new-york-mets':('New York Mets','1301',5),
 'angels':('Angels','720',0)}
FAMILY='Subject List:'
PARALLEL_HEADING='Base Card Parallels (1 per set)'
COMMON=[('/99','Green Foil'),('/50','Gold Foil'),('/25','Orange Foil'),('/10','Black Foil'),('/5','Red Foil'),('1/1','FoilFractor')]
INCLUDED='*Team Set print runs include 356 from the 2026 MLB Topps NOW® Road To Opening Day – Autograph Collector’s Box'
BONUS_INTRO='Purchasers of this set have the chance to earn Topps NOW® bonus cards! The following milestones trigger an exclusive bonus card(s) order over the course of the 2026 season (Opening Day through World Series)'
BONUSES=["Team's player hits for cycle","Team's player hits 3 HRs in a game","Team's pitcher throws 15 Ks in a game","Team's individual pitcher throws a no-hitter or perfect game"]


def identity(key):
    return ('topps-bowman-2026-rtod-topps-now-'+key,
            'https://www.topps.com/products/2026-'+key+'-mlb-topps-now%C2%AE-road-to-opening-day-11-card-team-set',
            'data/parallel-audit-sources/rtod-now-'+key+'-2026-product-20261018.json')


def build_one(key):
    team,run,marked=TEAMS[key];slug,page,evidence_file=identity(key)
    p=ROOT/evidence_file;proof=json.loads(p.read_text());ph=hashlib.sha256(p.read_bytes()).hexdigest()
    title='2026 '+team+' MLB Topps NOW® Road To Opening Day 11-Card Team Set - PR: '+run
    assert proof['title']==title and proof['url']==page and proof['documentLinks']==[] and proof['sourceKind']=='official-browser-product-factual-excerpt'
    fields=dict(proof['specs']);assert fields['Available From']=='Mar 20, 2026' and fields['Available Until']=='Apr 6, 2026'
    assert fields['Product Year']=='2026' and fields['Properties']==team and fields['Sub Categories']=='Baseball' and fields['Sub Type']=='Online Exclusive Box'
    lines=[s.strip() for s in proof['description'].splitlines() if s.strip()]
    cells=[s.strip() for s in proof['descriptionParagraphs'] if s.strip()]
    subjects=lines[lines.index(FAMILY)+1:lines.index(PARALLEL_HEADING)]
    assert len(subjects)==10 and subjects==cells[cells.index(FAMILY)+1:cells.index(PARALLEL_HEADING)]
    rows=[]
    for literal in subjects:
        m=re.fullmatch(r'(.+?)\s+- (parallel subject)',literal)
        player=m[1] if m else literal;mark=m[2] if m else ''
        rows.append([FAMILY,'',player,mark,literal,page])
    assert len({r[2] for r in rows})==10 and sum(bool(r[3]) for r in rows)==marked
    foils=([('/199','Aqua Foil'),('/150','Blue Foil')] if key=='los-angeles-dodgers' else [])+COMMON
    terms=[n+' '+name for n,name in foils]
    assert lines[lines.index(PARALLEL_HEADING)+1:lines.index('Earn Bonus Cards!')]==terms
    assert cells[cells.index(PARALLEL_HEADING)+1:cells.index('Earn Bonus Cards!')]==terms
    assert proof['descriptionListItems']==BONUSES and BONUS_INTRO in lines and BONUS_INTRO in cells
    # Independent list-node text must also be present, in order, in the full visible panel.
    i=lines.index(BONUS_INTRO)+1;assert lines[i:i+4]==BONUSES
    overview=[s.strip() for s in proof['overview'].splitlines() if s.strip()]
    assert overview==[s.strip() for s in proof['overviewCells'] if s.strip()]
    bound='(1) Parallel /'+('199' if key=='los-angeles-dodgers' else '99')+' or lower'
    assert overview==[INCLUDED,'Each Team Set includes:',bound,'(10) Base Cards','Earn bonus cards from in-season milestones! See below for details.','Limited Quantities - Available while supplies last']
    evidence={'evidenceFile':evidence_file,'evidenceSha256':ph}
    eligibility=f'The source explicitly marks {marked} of ten subjects as parallel subject. Blank marks do not establish eligibility or ineligibility; subject/color combinations and printed card numbers are not supplied.'
    if not marked:eligibility+=' The guaranteed parallel statement and absence of any roster marks remain an unresolved source gap; do not assume all ten subjects are eligible.'
    specs=[{'name':FAMILY,'worksheet':'Official Description · inline parallel-subject marks','source':page,
        'headers':['Published specification','Qualification','Official source'],
        'rows':[[str(marked)+' explicit parallel-subject marks',eligibility,page]],**evidence},
        {'name':'Unjoined '+PARALLEL_HEADING,'worksheet':'Official Description · '+PARALLEL_HEADING,'source':page,
        'headers':['Published parallel','Published numbering','Qualification','Official source'],
        'rows':[[name,n,'Exact product base-parallel term. Inline parallel-subject marks are retained in card rows; no subject/color combinations or per-card numbering joins are inferred.',page] for n,name in foils],**evidence},
        {'name':'Set-wide bundle configuration and print-run scope','worksheet':'Official title, Overview and Specs','source':page,
        'headers':['Official field','Published term','Qualification'],
        'rows':[['Published bundle print run',run,'Whole team-set run, including the stated Collector’s Box contribution; not a print run for each subject or parallel.'],
                ['Print-run inclusion statement',INCLUDED,'Retain 356 as the published included box contribution. Do not subtract it to invent a separate direct-sale run or turn it into serial numbering.'],
                ['Published base contents','(10) Base Cards','Ten listed base subjects plus one additional parallel; eleven-card bundle does not establish an eleventh base subject.'],
                ['Published parallel distribution',bound,'One parallel per set and qualified upper bound; not pack odds or an exact selected card limit.'],
                ['Availability qualifier','Limited Quantities - Available while supplies last','Original product qualifier; not a serial limit or actual remaining quantity.'],
                ['Printed card numbers','Not published','Blank IDs remain blank; subject order and SKU do not supply numbers.'],
                ['Per-row team / rookie fields','Not published','Specs Properties remains a product-level field, not an invented row-level team assignment.'],
                *[[k,v,'Official sale window, not a general release date.' if k.startswith('Available ') else ''] for k,v in fields.items()]],**evidence},
        {'name':'Set-wide conditional bonus-card terms','worksheet':'Official Description · Earn Bonus Cards!','source':page,
        'headers':['Published milestone','Qualification','Official source'],
        'rows':[[term,BONUS_INTRO+' No earned bonus-card roster, quantity or odds is inferred.',page] for term in BONUSES],**evidence}]
    payload={'title':title,'headers':['Checklist section','Card number','Player / subjects','Published parallel-subject mark','Published subject','Official source'],
        'rows':rows,'source':page,'sha256':ph,'sourceKind':proof['sourceKind'],
        'sourceHashQualification':'SHA-256 of the retained normalized official browser factual snapshot, not raw HTML.',
        'importKind':'topps-web-roster','sectionColumn':0,'publishedSpecifications':specs,
        'sourceProducts':[{**proof,'snapshotFile':evidence_file,'sha256':ph}],
        'coverageNote':'All ten original subject cells and explicit inline parallel-subject marks are imported. Blank marks do not establish eligibility or ineligibility. Named base-parallel limits, qualified bundle distribution and conditional bonus terms retain their original scope. Printed IDs, exhaustive subject/color joins, pack odds, general release and historical NOW coverage remain unverified.'}
    record={'title':title,'manufacturer':'Topps / Bowman','sport':'baseball','year':'2026','slug':slug,'page':'sets/'+slug+'.html',
        'sourcePage':page,'checklistUrl':page,'releaseStatus':'Unverified','releaseDate':None,'verified':datetime.date.today().isoformat(),
        'tableData':'data/imports/'+slug+'.json','status':'Source table','importKind':'topps-web-roster',
        'dedicatedParser':'scripts/import_topps_now_rtod_teams_2026.py','rowCount':10,'sections':1,'parallelData':True,'publishedOdds':False,'sha256':ph,'coverageComplete':False,
        'description':f'All ten official {team} subjects are imported, with {marked} explicit parallel-subject marks and blank unpublished card numbers. {len(foils)} named base-parallel limits, the qualified one-parallel-per-set statement and four conditional bonus milestones retain their source scope. Bundle PR{run} includes the stated 356 Collector’s Box sets; no direct-sale remainder or per-card run is inferred. March 20–April 6 store dates remain separate from general release. Historical coverage and exhaustive eligibility remain partial.'+(' The source prints no parallel-subject markers despite the guaranteed parallel statement; eligibility remains unresolved.' if not marked else ''),
        'catalogEvidence':'Fresh official Description paragraphs publish ten literal subject cells, original accents and inline parallel subject suffixes. Original nonbreaking spaces are preserved in the Published subject cells. The Dodgers-only Aqua /199 and Blue /150 terms never transfer to other teams. Every product retains the 356-included Collector’s Box qualifier without subtraction. Printed IDs, per-row team/rookie fields, pack odds and earned bonus rosters are not supplied. Four seasonal milestone conditions do not establish actual bonus-card releases. '+eligibility,
        'dataAudit':'Ten independent DOM paragraph roster cells reconcile with the full Description panel; foil number/name cells, four list-node milestones and the complete Overview reconcile independently. Original label/whitespace cells remain exportable. Upper bounds, bundle runs, box contributions, store dates and conditional distributions remain distinct from per-card numbering and pack odds.'}
    assert generic.run(record.copy())==record
    return record,payload


def build():
    # Validate and construct all physical and web joins before replacing prior imports.
    from import_topps_now_rtod_pdf_2026 import build as apply_pdf
    apply_pdf()

if __name__=='__main__':build()
