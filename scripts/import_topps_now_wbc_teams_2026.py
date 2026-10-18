"""Import five separate official WBC NOW team-set web rosters and bundle facts."""
import datetime
import hashlib
import json
from pathlib import Path
import import_official_catalog as generic

ROOT=Path(__file__).resolve().parents[1]
TEAMS={
 'united-states':('United States','20322',(12,12,4)),
 'venezuela':('Venezuela','1424',(12,3,3)),
 'dominican-republic':('Dominican Republic','4207',(12,4,3)),
 'japan':('Japan','34993',(12,12,4)),
 'korea':('Korea','1086',(10,2,1))}
PARALLEL='Parallel Subjects:'
AUTO='Autograph Subjects:'
FOILS=[('Green Foil','/99'),('Gold Foil','/50'),('Orange Foil','/25'),('Black Foil','/10'),('Red Foil','/5'),('FoilFractor','/1')]
LOGO='Unnumbered WBC Logo Parallel'


def identity(key):
    return ('topps-bowman-2026-wbc-topps-now-team-'+key,
            'https://www.topps.com/products/2026-topps-now-baseball-team-'+key+'-world-baseball-classic-team-sets',
            'data/parallel-audit-sources/wbc-now-team-'+key+'-2026-product-20261018.json')


def build_one(key):
    country,run,counts=TEAMS[key];slug,page,evidence_file=identity(key)
    p=ROOT/evidence_file;proof=json.loads(p.read_text());ph=hashlib.sha256(p.read_bytes()).hexdigest()
    title='2026 Topps NOW® Baseball – Team '+country+' – World Baseball Classic Team Sets - PR: '+run
    base='Team '+country+' Subject List:';families=[base,PARALLEL,AUTO]
    assert proof['title']==title and proof['url']==page and proof['documentLinks']==[]
    assert proof['sourceKind']=='official-browser-product-factual-excerpt'
    fields=dict(proof['specs']);assert fields['Available From']=='Mar 5, 2026' and fields['Available Until']=='Mar 16, 2026'
    assert fields['Product Year']=='2026' and fields['Sub Categories']=='Baseball' and fields['Sub Type']=='Online Exclusive Box'
    lines=[s.strip() for s in proof['description'].splitlines() if s.strip()]
    cells=[s.strip() for s in proof['descriptionParagraphs'] if s.strip()];assert lines==cells
    config=f'({counts[0]}) Base Cards PLUS (1) Guaranteed parallel or autograph parallel per set.'
    assert lines[0]=='2026 Topps NOW Baseball – World Baseball Classic team sets! '+config
    assert lines[-1].startswith('All sales are final.')
    headings=[*families,lines[-1]];rows=[]
    for (family,stop),count in zip(zip(headings,headings[1:]),counts):
        subjects=lines[lines.index(family)+1:lines.index(stop)]
        assert len(subjects)==count and len(set(subjects))==count and all(not s.endswith(':') for s in subjects)
        rows.extend([family,'',subject,subject,page] for subject in subjects)
    overview=[s.strip() for s in proof['overview'].splitlines() if s.strip()]
    overview_cells=[s.strip() for s in proof['overviewCells'] if s.strip()]
    start=overview.index('Parallels/Variations:')+1
    terms=[LOGO,*[n+' '+name for name,n in FOILS]]
    assert overview[start:start+7]==terms and overview_cells[start:start+7]==terms and config in overview
    evidence={'evidenceFile':evidence_file,'evidenceSha256':ph};specifications=[]
    for family,count in zip(families,counts):
        qualification='Only this separately printed roster is imported. Membership in another program is not inferred.'
        if family==PARALLEL:qualification+=' The roster does not enumerate individual subject/color combinations.'
        if family==AUTO:qualification+=' No autograph numbering or color ladder is published.'
        specifications.append({'name':family,'worksheet':'Official Description · '+family,'source':page,
            'headers':['Published roster','Qualification','Official source'],
            'rows':[[str(count)+' separately published '+('subject' if count==1 else 'subjects'),qualification,page]],**evidence})
    specifications.append({'name':'Unjoined product foil and WBC Logo terms','worksheet':'Official Overview · Parallels/Variations:','source':page,
        'headers':['Published parallel','Published numbering','Qualification','Official source'],
        'rows':[['WBC Logo Parallel','Unnumbered','Explicitly unnumbered product parallel. The separate Parallel Subjects roster does not enumerate subject/color combinations; no autograph eligibility is inferred.',page]]+
            [[name,n,'Product foil term. The separate Parallel Subjects roster does not enumerate subject/color combinations or publish an autograph ladder; no base or autograph limit is inferred.',page] for name,n in FOILS],**evidence})
    specifications.append({'name':'Set-wide bundle configuration and sale dates','worksheet':'Official title, Overview and Specs · product scope','source':page,
        'headers':['Official field','Published term','Qualification'],
        'rows':[['Published bundle contents',config,str(counts[0])+' base cards plus one additional card; the combined program row count is not the number of cards in one bundle.'],
                ['Published bundle print run',run,'PR labels this whole team-set bundle, not each subject, parallel or autograph.'],
                ['Printed card numbers','Not published','Blank IDs remain blank; roster order and SKU are not printed numbers.'],
                ['Team assignments / rookie flags','Not published','Team-set branding does not create per-row team or Rookie fields.'],
                *[[k,v,'Official sale window, not a general release date.' if k.startswith('Available ') else ''] for k,v in fields.items()]],**evidence})
    payload={'title':title,'headers':['Checklist section','Card number','Player / subjects','Published subject','Official source'],
        'rows':rows,'source':page,'sha256':ph,'sourceKind':proof['sourceKind'],
        'sourceHashQualification':'SHA-256 of the retained normalized official browser factual snapshot, not raw HTML.',
        'importKind':'topps-web-roster','sectionColumn':0,'publishedSpecifications':specifications,
        'sourceProducts':[{**proof,'snapshotFile':evidence_file,'sha256':ph}],
        'coverageNote':'All three original subject lists are imported. Printed card numbers and per-row team/rookie fields are absent. Six foil limits and the explicitly unnumbered WBC Logo parallel retain product scope without inferred subject/color joins. Pack odds, general release, exhaustive numbering and historical NOW coverage remain unverified.'}
    record={'title':title,'manufacturer':'Topps / Bowman','sport':'baseball','year':'2026','slug':slug,'page':'sets/'+slug+'.html',
        'sourcePage':page,'checklistUrl':page,'releaseStatus':'Unverified','releaseDate':None,'verified':datetime.date.today().isoformat(),
        'tableData':'data/imports/'+slug+'.json','status':'Source table','importKind':'topps-web-roster',
        'dedicatedParser':'scripts/import_topps_now_wbc_teams_2026.py','rowCount':len(rows),'sections':3,'parallelData':True,'publishedOdds':False,'sha256':ph,'coverageComplete':False,
        'description':f'The official Team {country} WBC product publishes {counts[0]} base subjects, {counts[1]} Parallel Subjects and {counts[2]} autograph subjects. All {len(rows)} entries are imported under their original headings with blank unpublished numbers. Six product foil limits and explicitly unnumbered WBC Logo terms retain their scope. Bundle PR{run} and March 5–16 sale dates are separate from an unverified general release; historical coverage remains partial.',
        'catalogEvidence':f'Fresh official product Description paragraphs publish three distinct Team {country} subject lists. Original spellings and accents are retained. Only the separately named parallel and autograph rosters establish those memberships; no subject/color combinations or autograph numbering are inferred. No printed IDs, per-row teams, Rookie marks, linked checklist document or pack odds are published on the reviewed page. Bundle PR{run}, the {counts[0]}-plus-one configuration and store dates remain product-level facts. Venezuela team-set and championship products have separate sources, rosters, runs and sale windows.',
        'dataAudit':'All original DOM paragraph subject cells reconcile independently with the complete Description text. Six foil number/name pairs and the unnumbered WBC Logo statement reconcile with original Overview paragraph cells. Exact roster membership remains visible and exportable; unavailable numbers, per-row teams/rookies, odds and exhaustive eligibility are not invented.'}
    assert generic.run(record.copy())==record
    return record,payload


def build():
    results=[build_one(key) for key in TEAMS]
    for record,payload in results:(ROOT/record['tableData']).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
    for name in ['topps-product-official-catalog.json','set-catalog.json']:
        p=ROOT/'data'/name;catalog=json.loads(p.read_text());sets=catalog['sets'] if isinstance(catalog,dict) else catalog
        for record,_ in results:
            i=next((i for i,s in enumerate(sets) if s['slug']==record['slug']),None)
            if i is None:sets.append(record)
            else:sets[i]=record
        p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    p=ROOT/'data/parallel-specifications.json';registry=json.loads(p.read_text())
    for record,_ in results:registry['sets'][record['slug']]=[]
    p.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Imported five WBC NOW team sets: 106 source entries across 15 exact rosters; separate bundle runs, sale dates and qualified seven-term parallel programs retained. History remains partial.')

if __name__=='__main__':build()
