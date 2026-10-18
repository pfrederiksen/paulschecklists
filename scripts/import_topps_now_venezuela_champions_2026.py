"""Import the four exact Venezuela WBC championship NOW web subject lists."""
import datetime
import hashlib
import json
from collections import Counter
from pathlib import Path
import import_official_catalog as generic

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-venezuela-wbc-championship-topps-now'
TITLE='2026 Topps NOW® Baseball – Team Venezuela – World Baseball Classic Championship Set - PR:1084'
PAGE='https://www.topps.com/products/2026-topps-now%C2%AE-baseball-team-venezuela-world-baseball-classic-championship-set'
EVIDENCE='data/parallel-audit-sources/venezuela-wbc-championship-now-2026-product-20261018.json'
BASE='Team Venezuela Subject List:'
PARALLEL='Parallel Subjects:'
IMAGE='Image Variation Short Print Subjects:'
AUTO='Autograph Subjects:'
FAMILIES=[BASE,PARALLEL,IMAGE,AUTO]
CONFIG='(15) Base Cards PLUS (1) Guaranteed numbered parallel, image variation short print or autograph parallel per set.'
FOILS=[('Green Foil','/99'),('Gold Foil','/50'),('Orange Foil','/25'),('Black Foil','/10'),('Red Foil','/5'),('FoilFractor','/1')]


def source_rows(proof):
    lines=[s.strip() for s in proof['description'].splitlines() if s.strip()]
    paragraphs=[s.strip() for s in proof['descriptionParagraphs'] if s.strip()]
    assert lines==paragraphs
    assert lines[0].endswith(CONFIG) and lines[-1].startswith('All sales are final.')
    headings=[*FAMILIES,lines[-1]];rows=[]
    for heading,end in zip(headings,headings[1:]):
        subjects=lines[lines.index(heading)+1:lines.index(end)]
        assert len(subjects)=={BASE:15,PARALLEL:4,IMAGE:4,AUTO:4}[heading]
        assert all(s and not s.endswith(':') for s in subjects)
        rows.extend([heading,'',subject,subject,PAGE] for subject in subjects)
    assert Counter(r[0] for r in rows)=={BASE:15,PARALLEL:4,IMAGE:4,AUTO:4}
    return rows


def build():
    path=ROOT/EVIDENCE;proof=json.loads(path.read_text());ph=hashlib.sha256(path.read_bytes()).hexdigest()
    assert proof['url']==PAGE and proof['title']==TITLE and proof['documentLinks']==[]
    assert proof['sourceKind']=='official-browser-product-factual-excerpt'
    fields=dict(proof['specs'])
    assert fields['Available From']=='Mar 18, 2026' and fields['Available Until']=='Mar 25, 2026'
    assert fields['Product Year']=='2026' and fields['Sub Categories']=='Baseball' and fields['Sub Type']=='Online Exclusive Box'
    rows=source_rows(proof);evidence={'evidenceFile':EVIDENCE,'evidenceSha256':ph}
    overview=[line.strip() for line in proof['overview'].splitlines() if line.strip()]
    cells=[s.strip() for s in proof['overviewCells'] if s.strip()]
    start=overview.index('Parallels/Variations:')+1
    assert overview[start:start+7]==['Image Variation Short print',*[n+' '+name for name,n in FOILS]]
    assert cells[start:start+7]==overview[start:start+7] and CONFIG in overview
    specifications=[]
    for family in FAMILIES:
        names=[r[2] for r in rows if r[0]==family]
        qualification='Only this separately printed roster is imported. A name in one list is not automatically eligible in another program.'
        if family==IMAGE:qualification+=' Short print does not publish a print quantity or serial limit.'
        if family==AUTO:qualification+=' No autograph numbering or color ladder is published.'
        if family==PARALLEL:qualification+=' The four-subject roster does not establish every subject/color combination.'
        specifications.append({'name':family,'worksheet':'Official Description · '+family,'source':PAGE,
            'headers':['Published roster','Qualification','Official source'],
            'rows':[[str(len(names))+' separately published subjects',qualification,PAGE]],**evidence})
    specifications.append({'name':'Unjoined product foil numbering','worksheet':'Official Overview · Parallels/Variations:','source':PAGE,
        'headers':['Published parallel','Published numbering','Qualification','Official source'],
        'rows':[[name,n,'Product foil term. The page separately lists four Parallel Subjects but does not enumerate subject/color combinations or assign these limits to base, short-print or autograph programs.',PAGE] for name,n in FOILS]+[
            ['Image Variation Short print','Not stated','The separate four-subject image-variation roster is published; no numeric or explicitly unnumbered specification is stated.',PAGE]],**evidence})
    specifications.append({'name':'Set-wide bundle configuration and sale dates','worksheet':'Official title, Overview and Specs · product scope','source':PAGE,
        'headers':['Official field','Published term','Qualification'],
        'rows':[['Published bundle contents',CONFIG,'15 base cards plus one additional card; 27 roster entries are not 27 cards in one bundle.'],
                ['Published bundle print run','1084','PR:1084 labels the whole bundle, not each listed subject or parallel.'],
                ['Printed card numbers','Not published','Blank IDs remain blank; subject order and SKU do not supply card numbers.'],
                ['Team assignments / rookie flags','Not published','No team or Rookie column is supplied; team-set branding does not create per-row fields.'],
                *[[k,v,'Official sale window, not a general release date.' if k.startswith('Available ') else ''] for k,v in fields.items()]],**evidence})
    payload={'title':TITLE,'headers':['Checklist section','Card number','Player / subjects','Published subject','Official source'],
        'rows':rows,'source':PAGE,'sha256':ph,'sourceKind':proof['sourceKind'],
        'sourceHashQualification':'SHA-256 of the retained normalized official browser factual snapshot, not raw HTML.',
        'importKind':'topps-web-roster','sectionColumn':0,'publishedSpecifications':specifications,
        'sourceProducts':[{**proof,'snapshotFile':EVIDENCE,'sha256':ph}],
        'coverageNote':'All 27 original entries across four separately published rosters are imported. Card numbers and per-row team/rookie fields are absent. Six product foil limits are retained without inferred subject/color joins. Pack odds, general release, exhaustive numbering and historical NOW coverage remain unverified.'}
    record={'title':TITLE,'manufacturer':'Topps / Bowman','sport':'baseball','year':'2026','slug':SLUG,'page':'sets/'+SLUG+'.html',
        'sourcePage':PAGE,'checklistUrl':PAGE,'releaseStatus':'Unverified','releaseDate':None,'verified':datetime.date.today().isoformat(),
        'tableData':'data/imports/'+SLUG+'.json','status':'Source table','importKind':'topps-web-roster',
        'dedicatedParser':'scripts/import_topps_now_venezuela_champions_2026.py','rowCount':27,'sections':4,'parallelData':True,'publishedOdds':False,'sha256':ph,'coverageComplete':False,
        'description':'The official championship product publishes 15 base subjects, four Parallel Subjects, four image-variation subjects and four autograph subjects. All 27 entries are imported under their original headings with blank unpublished card numbers. Six product foil limits /99 to /1 retain their scope without inferred subject/color joins. PR1084 and March 18–25 sale dates belong to the bundle; general release and historical coverage remain unverified.',
        'catalogEvidence':'Fresh official Description paragraphs publish four distinct rosters, preserving Ronald Acuña Jr., Eugenio Suárez, separate William/Willson Contreras names and the collective Team Venezuela base entry. Maikel Garcia is in Parallel Subjects but not the image/autograph lists; Wilyer Abreu is in the autograph list but not Parallel Subjects. No card numbers, team columns, Rookie marks or linked checklist document are published on the reviewed page. Six foil limits and image-variation context remain qualified; no autograph ladder or short-print quantity is invented. Bundle configuration, bundle PR1084, sale dates and general release remain separate.',
        'dataAudit':'All 27 original DOM paragraph subject cells reconcile independently with the complete Description text. The six original foil/number pairs reconcile with Overview paragraph cells. Exact roster membership and accents remain visible and exportable; no numbering, teams, rookies, pack odds or subject/color combinations are inferred.'}
    assert generic.run(record.copy())==record
    (ROOT/record['tableData']).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
    for name in ['topps-product-official-catalog.json','set-catalog.json']:
        p=ROOT/'data'/name;catalog=json.loads(p.read_text());sets=catalog['sets'] if isinstance(catalog,dict) else catalog
        index=next((i for i,s in enumerate(sets) if s['slug']==SLUG),None)
        if index is None:sets.append(record)
        else:sets[index]=record
        p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    p=ROOT/'data/parallel-specifications.json';registry=json.loads(p.read_text());registry['sets'][SLUG]=[];p.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Imported 27 Venezuela WBC championship source entries across four exact rosters, six qualified product foil limits, bundle PR1084 and March 18–25 sale dates; history remains partial.')

if __name__=='__main__':build()
