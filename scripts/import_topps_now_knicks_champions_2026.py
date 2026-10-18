"""Import literal official NOW web rosters without inventing card IDs or foil joins."""
import datetime
import hashlib
import json
from collections import Counter
from pathlib import Path
import import_official_catalog as generic

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-nba-topps-now-knicks-champions-team-set'
TITLE='2026 NBA Champions - New York Knicks - NBA Topps NOW® 16-Card Team Set'
PAGE='https://www.topps.com/products/2026-nba-champions-new-york-knicks-nba-topps-now-r-16-card-team-set'
EVIDENCE='data/parallel-audit-sources/nba-now-knicks-champions-2026-product-20261018.json'
BASE='Subject List:'
IMAGE='Image Variation Subjects:'
AUTO='Autograph Subjects:'
REDEMPTIONS=[
 ('Jalen Brunson/Karl-Anthony Towns 1/1 Dual Autograph Redemption','Jalen Brunson/Karl-Anthony Towns'),
 ('Jalen Brunson/Walt Frazier 1/1 Dual Autograph-Relic Redemption','Jalen Brunson/Walt Frazier'),
 ('Knicks Starting 5 1/1 Quintuple Autograph Redemption','Knicks Starting 5')]
FOILS=[('Green Foil','/99'),('Blue & Orange Foil','/73'),('Gold Foil','/50'),('Orange Foil','/25'),('Black Foil','/10'),('Red Foil','/5'),('FoilFractor','/1')]


def roster_rows(proof):
    lines=[line.strip() for line in proof['description'].splitlines() if line.strip()]
    paragraphs=[line.strip() for line in proof['descriptionParagraphs'] if line.strip()]
    end='Your Hero. Your Team. Your Moment. ™'
    assert lines[:lines.index(end)+1]==paragraphs[:paragraphs.index(end)+1]
    rows=[]
    statements={BASE:'(15) Base Cards PLUS (1) Parallel, SP, Auto, or Auto-Relic per Championship Set.',
                IMAGE:'Image Variation Short Prints',AUTO:'On-Card Autograph Redemptions /10 or less'}
    headings=[BASE,IMAGE,AUTO,end]
    for start,stop in zip(headings,headings[1:]):
        subjects=paragraphs[paragraphs.index(start)+1:paragraphs.index(stop)]
        assert len(subjects)=={BASE:15,IMAGE:8,AUTO:9}[start]
        assert all(s and not s.endswith(':') for s in subjects)
        rows.extend([start,'',subject,statements[start],PAGE] for subject in subjects)
    for term,subjects in REDEMPTIONS:
        assert term in proof['overview'].splitlines()
        rows.append([term,'',subjects,term,PAGE])
    assert len(rows)==35 and Counter(r[0] for r in rows)=={BASE:15,IMAGE:8,AUTO:9,**{term:1 for term,_ in REDEMPTIONS}}
    return rows


def build():
    path=ROOT/EVIDENCE;proof=json.loads(path.read_text());ph=hashlib.sha256(path.read_bytes()).hexdigest()
    assert proof['url']==PAGE and proof['title']==TITLE+' - PR: 65941' and proof['documentLinks']==[]
    assert proof['sourceKind']=='official-browser-product-factual-excerpt'
    fields=dict(proof['specs']);assert fields['Available From']=='Jun 13, 2026' and fields['Available Until']=='Jun 20, 2026'
    assert fields['Category']=='Sports' and fields['Sub Categories']=='Basketball' and fields['Product Year']=='2026' and fields['Sub Type']=='Set'
    rows=roster_rows(proof)
    lines=[line.strip() for line in proof['overview'].splitlines() if line.strip()]
    for name,numbering in FOILS:assert numbering+' '+name in lines
    assert 'Serial-Numbered Parallel /99 or less' in lines and 'On-Card Autograph Redemptions /10 or less' in lines
    evidence={'evidenceFile':EVIDENCE,'evidenceSha256':ph}
    specifications=[{'name':AUTO,'worksheet':'Official product Overview · qualified autograph bound','source':PAGE,
        'headers':['Published statement','Qualification','Official source'],
        'rows':[['On-Card Autograph Redemptions /10 or less','Upper bound only. No exact color limit or per-subject numbering is inferred.',PAGE]],**evidence},
        {'name':IMAGE,'worksheet':'Official product Overview · image variations','source':PAGE,
        'headers':['Published statement','Qualification','Official source'],
        'rows':[['Image Variation Short Prints','Only the eight separately published image-variation subjects are imported. No print quantity or color eligibility is stated.',PAGE]],**evidence},
        {'name':'Unjoined product foil and parallel terms','worksheet':'Official product Overview · Parallels/Variations:','source':PAGE,
        'headers':['Published parallel','Published numbering','Qualification','Official source'],
        'rows':[[name,numbering,'The product lists this foil without an exact checklist-family heading. No base, image-variation or autograph subject eligibility is inferred.',PAGE] for name,numbering in FOILS]+[
            ['Serial-Numbered Parallel','/99 or less','Qualified product-level upper bound; not an exact selected family limit.',PAGE]],**evidence},
        {'name':'Set-wide product configuration and sale dates','worksheet':'Official product Overview, title and Specs · bundle scope','source':PAGE,
        'headers':['Official field','Published term','Qualification'],
        'rows':[['Published bundle print run (title)','65941','Bundle-level only; not a print run for every subject, parallel or redemption.'],
                ['Published bundle contents',lines[1],'15 base cards plus one additional card; 35 imported source entries do not mean 35 cards in one bundle.'],
                ['Printed card numbers','Not published','All imported card-number cells remain blank; neither SKU nor subject order supplies an ID.'],
                ['Quintuple redemption signer roster','Knicks Starting 5','Only this collective caption is published. Five individual signer names are not inferred.'],
                *[[k,v,'Official sale window, not a general release date.' if k.startswith('Available ') else ''] for k,v in fields.items()]],**evidence}]
    mappings=[]
    for term,subjects in REDEMPTIONS:
        qualification='Exact named redemption only; no other autograph or subject inherits 1/1.'
        if subjects=='Knicks Starting 5':qualification+=' The five individual signers are not named in this source and remain unexpanded.'
        mappings.append(dict(family=term,name='Named redemption',numbering='1/1',qualification=qualification,sourceHeading='Look For:',source=PAGE,**evidence))
        specifications.append({'name':term,'worksheet':'Official product Overview · exact named redemption','source':PAGE,
            'headers':['Published statement','Qualification','Official source'],'rows':[[term,qualification,PAGE]],**evidence})
    payload={'title':TITLE,'headers':['Checklist section','Card number','Player / subjects','Published statement','Official source'],
             'rows':rows,'source':PAGE,'sha256':ph,'sourceKind':proof['sourceKind'],
             'importKind':'topps-web-roster','sectionColumn':0,'publishedSpecifications':specifications,
             'sourceProducts':[{**proof,'snapshotFile':EVIDENCE,'sha256':ph}],
             'sourceHashQualification':'SHA-256 of the retained normalized official browser factual snapshot, not raw HTML.',
             'coverageNote':'All three published subject lists and three named redemption captions are imported. Card numbers, individual quintuple signers, exhaustive foil eligibility, pack odds and general release remain unpublished or unverified.'}
    record={'title':TITLE,'manufacturer':'Topps / Bowman','sport':'basketball','year':'2026','slug':SLUG,'page':'sets/'+SLUG+'.html',
            'sourcePage':PAGE,'checklistUrl':PAGE,'releaseStatus':'Unverified','releaseDate':None,'verified':datetime.date.today().isoformat(),
            'tableData':'data/imports/'+SLUG+'.json','status':'Source table','importKind':'topps-web-roster',
            'dedicatedParser':'scripts/import_topps_now_knicks_champions_2026.py','rowCount':35,'sections':6,'parallelData':True,'publishedOdds':False,
            'sha256':ph,'coverageComplete':False,
            'description':'A made-to-order 16-card bundle with 15 base cards and one additional parallel, SP, autograph or autograph-relic. The official page supplies 15 base, eight image-variation and nine autograph subject rows, plus three named redemption programs. All card numbers remain blank. Seven unjoined foil limits and three exact named 1/1 redemptions are retained; bundle PR65941 and June 13–20 sale dates are product-level facts.',
            'catalogEvidence':'The complete published web subject lists are imported with their exact headings and literal names, including Pacôme Dadiet and the autograph list’s Miles McBride nonbreaking space. No checklist document is linked on the reviewed product page. Seven foil limits lack an exact family heading and remain unjoined context. The three named 1/1 redemptions have isolated family mappings; Knicks Starting 5 remains a collective caption without inferred signer names. On-card autograph /10-or-less is an upper bound. Printed IDs, individual quintuple signers, exhaustive eligibility, pack odds, general release and historical NOW coverage remain unverified.',
            'dataAudit':'35 source entries: 32 rows across three literal published subject lists and three named redemption captions. Independent DOM paragraph boundaries match the retained description text. Every card number remains blank; no teams, rookie flags, per-card print runs or pack odds are invented.'}
    # The generic catalog importer must preserve this dedicated web-roster adapter.
    assert generic.run(record.copy())==record
    (ROOT/record['tableData']).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
    for name in ['topps-product-official-catalog.json','set-catalog.json']:
        p=ROOT/'data'/name;catalog=json.loads(p.read_text());sets=catalog['sets'] if isinstance(catalog,dict) else catalog
        index=next((i for i,s in enumerate(sets) if s['slug']==SLUG),None)
        if index is None:sets.append(record)
        else:sets[index]=record
        p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    p=ROOT/'data/parallel-specifications.json';registry=json.loads(p.read_text());registry['sets'][SLUG]=mappings;p.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Imported 35 Knicks championship NOW source entries; blank IDs, three exact named 1/1 redemptions, seven unjoined foil limits and bundle-only PR65941 retained.')

if __name__=='__main__':build()
