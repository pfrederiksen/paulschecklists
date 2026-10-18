"""Import the official fixed Premier League NOW roster and keep unnamed chase terms unjoined."""
import datetime
import hashlib
import json
import re
from pathlib import Path
import import_official_catalog as generic

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-premier-league-topps-now-team-of-the-season-set'
TITLE='Premier League Team of the Season - Premier League Topps NOW® 12-Card Set'
PAGE='https://www.topps.com/products/premier-league-team-of-the-season-premier-league-topps-now%C2%AE-12-card-set'
EVIDENCE='data/parallel-audit-sources/premier-now-tots-2026-product-20261018.json'
FAMILY='The 2025/26 Premier League Team of the Season includes:'
LIMITS={'Parallel:':['/1','/5','/10','/25','/50','/99'],'or Auto':['/1','/5']}


def source_rows(proof):
    paragraphs=[p.strip() for p in proof['descriptionParagraphs'] if p.strip()]
    start=paragraphs.index(FAMILY)+1;subjects=paragraphs[start:-1]
    assert len(subjects)==11 and paragraphs[-1].startswith('All sales are final.')
    lines=[p.strip() for p in proof['description'].splitlines() if p.strip()]
    assert subjects==lines[lines.index(FAMILY)+1:-1]
    rows=[]
    for literal in subjects:
        m=re.fullmatch(r'(.+) \(([^()]+)\)',literal);assert m,literal
        rows.append([FAMILY,'',m[1],m[2],literal,PAGE])
    assert len({r[2] for r in rows})==11
    return rows


def build():
    path=ROOT/EVIDENCE;proof=json.loads(path.read_text());ph=hashlib.sha256(path.read_bytes()).hexdigest()
    assert proof['url']==PAGE and proof['title']==TITLE and proof['documentLinks']==[]
    assert proof['sourceKind']=='official-browser-product-factual-excerpt'
    fields=dict(proof['specs']);assert fields['Available From']=='Jun 11, 2026' and fields['Available Until']=='Jun 18, 2026'
    assert fields['Category']=='Sports' and fields['Sub Categories']=='Soccer' and fields['Product Year']=='2026' and fields['Sub Type']=='Set'
    rows=source_rows(proof)
    overview=[line.strip() for line in proof['overview'].splitlines() if line.strip()]
    start=overview.index('Parallel:');end=overview.index('or Auto')
    assert overview[start+1:end]==LIMITS['Parallel:'] and overview[end+1:end+3]==LIMITS['or Auto']
    fixed="11 Base Cards (Fixed) PLUS 1 Guaranteed 'hit' (parallel, unnumbered parallel or autograph) per set."
    assert fixed in proof['descriptionParagraphs'] and '11 base cards (fixed)' in overview and '1 chase card guarantee:' in overview
    evidence={'evidenceFile':EVIDENCE,'evidenceSha256':ph}
    qualification='Unnamed product chase term; no color, exact checklist-family join or per-player eligibility is published. The autograph signer roster remains unverified.'
    terms=[[heading,limit,qualification,PAGE] for heading,limits in LIMITS.items() for limit in limits]
    terms.append(['unnumbered parallel','Unnumbered','The Description explicitly names an unnumbered parallel without a parallel name or eligibility roster.',PAGE])
    specifications=[{'name':FAMILY,'worksheet':'Official Description · fixed base roster','source':PAGE,
        'headers':['Published statement','Qualification','Official source'],
        'rows':[['11 base cards (fixed)','Only the eleven listed fixed-base subjects are imported. The extra chase card does not establish a twelfth base subject or autograph eligibility.',PAGE]],**evidence},
        {'name':'Unjoined product chase numbering','worksheet':'Official Overview · Parallel: / or Auto; Description · unnumbered parallel','source':PAGE,
        'headers':['Published program','Published numbering','Qualification','Official source'],'rows':terms,**evidence},
        {'name':'Set-wide product configuration and sale dates','worksheet':'Official Description and Specs · product scope','source':PAGE,
        'headers':['Official field','Published term','Qualification'],
        'rows':[['Published bundle contents',fixed,'Product configuration, not pack odds or a twelve-subject roster.'],
                ['Printed card numbers','Not published','Blank IDs are preserved; roster order and SKU do not supply card numbers.'],
                ['Published print run','Not published','No run is printed in the reviewed title or Specs.'],
                ['Autograph roster','Not published','Do not assign the eleven fixed-base subjects to the unnamed autograph program.'],
                ['Season in Description','2025/26','Separate from Product Year 2026 in Specs.'],
                *[[k,v,'Official sale window, not a general release date.' if k.startswith('Available ') else ''] for k,v in fields.items()]],**evidence}]
    payload={'title':TITLE,'headers':['Checklist section','Card number','Player / subjects','Team','Published subject','Official source'],
        'rows':rows,'source':PAGE,'sha256':ph,'sourceKind':proof['sourceKind'],'sourceHashQualification':'SHA-256 of the retained normalized official browser factual snapshot, not raw HTML.',
        'importKind':'topps-web-roster','sectionColumn':0,'publishedSpecifications':specifications,
        'sourceProducts':[{**proof,'snapshotFile':EVIDENCE,'sha256':ph}],
        'coverageNote':'All eleven published fixed-base roster entries are imported. Printed card numbers, actual print run, autograph roster, chase eligibility, pack odds, general release and historical NOW coverage remain unpublished or unverified.'}
    record={'title':TITLE,'manufacturer':'Topps / Bowman','sport':'soccer','year':'2026','slug':SLUG,'page':'sets/'+SLUG+'.html',
        'sourcePage':PAGE,'checklistUrl':PAGE,'releaseStatus':'Unverified','releaseDate':None,'verified':datetime.date.today().isoformat(),
        'tableData':'data/imports/'+SLUG+'.json','status':'Source table','importKind':'topps-web-roster',
        'dedicatedParser':'scripts/import_topps_now_premier_tots_2026.py','rowCount':11,'sections':1,'parallelData':True,'publishedOdds':False,'sha256':ph,'coverageComplete':False,
        'description':'A made-to-order 12-card bundle: eleven fixed base cards plus one guaranteed chase card. All eleven published subjects and clubs are imported with blank card numbers. Six unnamed Parallel limits, two Auto limits and an explicitly unnumbered parallel remain unjoined product terms. The Description names the 2025/26 season; Specs publishes Product Year 2026 and June 11–18 sale dates. Print run, autograph roster and general release remain unverified.',
        'catalogEvidence':'The official product Description publishes eleven fixed-base subject/club pairs. Preserve Gabriel Magalhães, Jurriën Timber, Nico O’Reilly, Liverpool FC and the complete original parenthetical cells. No card numbers, print run or checklist document are published in the reviewed page. Parallel: /1,/5,/10,/25,/50,/99 and or Auto /1,/5 retain their literal headings; the unnamed unnumbered parallel stays separate. No colors, exact family joins or autograph eligibility are inferred. Product configuration is not pack odds, store dates are not general release, and historical NOW coverage remains partial.',
        'dataAudit':'Eleven official DOM paragraph roster cells reconcile independently with the retained Description text. Original subjects and parenthetical clubs remain visible and exportable. Missing numbers, rookies, print runs, colors, autograph subjects and pack odds are not invented.'}
    assert generic.run(record.copy())==record
    (ROOT/record['tableData']).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
    for name in ['topps-product-official-catalog.json','set-catalog.json']:
        p=ROOT/'data'/name;catalog=json.loads(p.read_text());sets=catalog['sets'] if isinstance(catalog,dict) else catalog
        index=next((i for i,s in enumerate(sets) if s['slug']==SLUG),None)
        if index is None:sets.append(record)
        else:sets[index]=record
        p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    # Empty mappings are intentional: source programs are not exact roster-family joins.
    p=ROOT/'data/parallel-specifications.json';registry=json.loads(p.read_text());registry['sets'][SLUG]=[];p.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Imported all 11 Premier League NOW fixed-base subjects/clubs, blank IDs and nine unjoined chase terms; autograph roster and actual print run remain unpublished.')

if __name__=='__main__':build()
