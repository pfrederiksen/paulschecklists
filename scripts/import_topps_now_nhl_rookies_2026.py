"""Import literal NHL Rookie Collection web roster; retain unjoined Ice terms."""
import datetime
import hashlib
import json
from pathlib import Path
import import_official_catalog as generic

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-nhl-topps-now-rookie-collection'
TITLE='2025-26 NHL Topps NOW® Rookie Collection 10-Sticker Set - PR: 600'
PAGE='https://www.topps.com/products/2025-26-nhl-topps-now%C2%AE-rookie-collection-10-sticker-set'
EVIDENCE='data/parallel-audit-sources/nhl-now-rookie-collection-product-20261018.json'
FAMILY='CHECKLIST:'
CONFIG='Includes 10 stickers PLUS one guaranteed numbered or unnumbered parallel.'
TERMS=['• Unnumbered parallels','• /10 Black Ice Parallels','• /5 Red Ice Parallels','• /1 Gold Ice Parallel']


def source_rows(proof):
    paragraphs=[p.strip() for p in proof['overviewCells'] if p.strip()]
    start=paragraphs.index(FAMILY)+1
    subjects=paragraphs[start:-1]
    assert len(subjects)==10 and paragraphs[-1].startswith('The processing time for this item')
    lines=[line.strip() for line in proof['overview'].splitlines() if line.strip()]
    assert subjects==lines[lines.index(FAMILY)+1:-1]
    assert paragraphs[:start]==[CONFIG,'Look for:',*TERMS,FAMILY]
    rows=[]
    for literal in subjects:
        parts=literal.split(' -- ');assert len(parts)==2 and all(parts)
        rows.append([FAMILY,'',*parts,literal,PAGE])
    assert len({r[2] for r in rows})==10
    return rows


def build():
    path=ROOT/EVIDENCE;proof=json.loads(path.read_text());ph=hashlib.sha256(path.read_bytes()).hexdigest()
    assert proof['url']==PAGE and proof['title']==TITLE and proof['documentLinks']==[]
    assert proof['sourceKind']=='official-browser-product-factual-excerpt'
    fields=dict(proof['specs'])
    assert fields['Available From']=='Apr 20, 2026' and fields['Available Until']=='Apr 27, 2026'
    assert fields['Product Year']=='2026' and fields['Sub Categories']=='Hockey' and fields['Sub Type']=='Stickers'
    assert 'This 10-sticker checklist' in proof['description']
    rows=source_rows(proof);evidence={'evidenceFile':EVIDENCE,'evidenceSha256':ph}
    qualification='Product-level look-for term; no exact per-subject eligibility or printed sticker numbers are supplied. Retained without a roster-family or individual-sticker numbering join.'
    specifications=[{'name':'Unjoined product Ice parallel terms','worksheet':'Official Overview · Look for:','source':PAGE,
        'headers':['Published statement','Published numbering','Qualification','Official source'],
        'rows':[[term,number,qualification,PAGE] for term,number in zip(TERMS,['Unnumbered','/10','/5','/1'])],**evidence},
        {'name':'Set-wide sticker configuration and sale dates','worksheet':'Official title, Overview and Specs · product scope','source':PAGE,
        'headers':['Official field','Published term','Qualification'],
        'rows':[['Published bundle contents',CONFIG,'Retain the printed PLUS configuration; no eleventh base subject is listed. This is not pack odds.'],
                ['Published bundle print run','600','The title labels PR: 600 for the whole set. This is not a per-sticker print run or pack odds.'],
                ['Printed sticker numbers','Not published','Blank IDs remain blank; roster order and SKU are not numbers.'],
                ['Per-sticker rookie marks','Not published','Rookie Collection is the set title, not a published row-level Rookie field.'],
                ['Season in title','2025-26','Separate from Product Year 2026 in Specs.'],
                *[[k,v,'Official sale window, not a general release date.' if k.startswith('Available ') else ''] for k,v in fields.items()]],**evidence}]
    payload={'title':TITLE,'headers':['Checklist section','Card number','Player / subjects','Team','Published subject','Official source'],
        'rows':rows,'source':PAGE,'sha256':ph,'sourceKind':proof['sourceKind'],
        'sourceHashQualification':'SHA-256 of the retained normalized official browser factual snapshot, not raw HTML.',
        'importKind':'topps-web-roster','sectionColumn':0,'publishedSpecifications':specifications,
        'sourceProducts':[{**proof,'snapshotFile':EVIDENCE,'sha256':ph}],
        'coverageNote':'All ten published sticker subjects and teams are imported. Sticker numbers and row-level rookie marks are not published. Product Ice terms are retained without per-subject eligibility joins; pack odds, general release and historical NOW coverage remain unverified.'}
    record={'title':TITLE,'manufacturer':'Topps / Bowman','sport':'hockey','year':'2026','slug':SLUG,'page':'sets/'+SLUG+'.html',
        'sourcePage':PAGE,'checklistUrl':PAGE,'releaseStatus':'Unverified','releaseDate':None,'verified':datetime.date.today().isoformat(),
        'tableData':'data/imports/'+SLUG+'.json','status':'Source table','importKind':'topps-web-roster',
        'dedicatedParser':'scripts/import_topps_now_nhl_rookies_2026.py','rowCount':10,'sections':1,'parallelData':True,'publishedOdds':False,'sha256':ph,'coverageComplete':False,
        'description':'All ten official sticker subjects and teams are imported, retaining blank unpublished sticker numbers and the original subject/team cells. The bundle includes ten stickers PLUS one parallel; PR600 belongs to the bundle. Unnumbered, Black Ice /10, Red Ice /5 and Gold Ice /1 terms remain qualified product context without inferred individual eligibility. The 2025–26 title, Product Year 2026 and April 20–27 sale dates remain separate; general release and historical coverage are unverified.',
        'catalogEvidence':'Fresh official product Overview publishes ten subject/team pairs, four look-for terms and the literal PLUS configuration. Preserve Montréal Canadiens and the complete double-hyphen subject cells. No sticker IDs or row-level Rookie marks are supplied. The title labels bundle PR600; do not assign 600 to each subject. Product-level Ice terms lack per-subject eligibility and remain unjoined. No checklist document or pack odds is linked in the reviewed page.',
        'dataAudit':'Ten original official DOM paragraph cells reconcile independently with the full Overview text; literal subjects, teams and delimiters remain visible and exportable. Product-year, season, sale dates, bundle run and qualified Ice limits retain their original scope. Missing numbers and rookie flags are not inferred.'}
    assert generic.run(record.copy())==record
    (ROOT/record['tableData']).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
    for name in ['topps-product-official-catalog.json','set-catalog.json']:
        p=ROOT/'data'/name;catalog=json.loads(p.read_text());sets=catalog['sets'] if isinstance(catalog,dict) else catalog
        index=next((i for i,s in enumerate(sets) if s['slug']==SLUG),None)
        if index is None:sets.append(record)
        else:sets[index]=record
        p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    p=ROOT/'data/parallel-specifications.json';registry=json.loads(p.read_text());registry['sets'][SLUG]=[];p.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Imported 10 NHL Rookie Collection sticker subjects/teams, blank IDs, four unjoined Ice terms, bundle PR600 and April 20–27 sale dates; history remains partial.')

if __name__=='__main__':build()
