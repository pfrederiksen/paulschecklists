"""Preserve WrestleMania NOW physical numbers/subjects and exact base-only foil scope."""
import datetime
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
import pdfplumber
import import_official_catalog as generic

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-wwe-topps-now-wrestlemania-vegas-set'
TITLE='2026 WrestleMania Vegas Set – WWE Topps NOW® - 15-Card Set'
PAGE='https://www.topps.com/products/2026-wrestlemania-vegas-set-wwe-topps-now%C2%AE-15-card-set'
URL='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_WWE_Topps_Now_WrestleMania_Vegas_Checklist_1.pdf?v=1787965944'
EVIDENCE='data/parallel-audit-sources/wwe-now-wrestlemania-2026-product-20261018.json'
BASE='BASE CARDS'
LEGEND='WWE LEGEND SHORT PRINTS'
AUTO='BASE AUTOGRAPH VARIATIONS'
LEGEND_AUTO='LEGEND SP AUTOGRAPH VARIATIONS'
FAMILIES=[BASE,LEGEND,AUTO,LEGEND_AUTO]
COLORS=[('Gold Foil','/50'),('Orange Foil','/25'),('Black Foil','/10'),('Red Foil','/5'),('FoilFractor','/1')]
BOUNDS={AUTO:'Redemption for Base Autograph Variation /5 or lower',LEGEND_AUTO:'Legend SP Autograph Variation /5 or lower'}


def physical_rows(path):
    rows=[];raw=[]
    with pdfplumber.open(path) as doc:
        assert len(doc.pages)==2
        for pn,page in enumerate(doc.pages,1):
            assert (page.width,page.height)==(612,792)
            families=FAMILIES[:3] if pn==1 else FAMILIES[3:]
            headings=[]
            for family in families:
                matches=page.search(family,regex=False);assert len(matches)==1,(pn,family,matches)
                headings.append((matches[0]['top'],family))
            words=page.extract_words()
            anchors=[w for w in words if w['x0']<120 and re.fullmatch(r'(?:\d+(?:-A)?|LSP-\d+A?)',w['text']) and (pn>1 or w['top']>100)]
            for anchor in anchors:
                y=anchor['top'];family=max((h for h in headings if h[0]<y),key=lambda h:h[0])[1]
                cells=[(page.crop((lo,y-.5,hi,y+13)).extract_text() or '').strip() for lo,hi in [(50,120),(120,450)]]
                assert cells[0]==anchor['text'] and all(cells) and all('\n' not in c for c in cells),cells
                rows.append([family,*cells,str(pn)])
            raw.append({'page':pn,'text':page.extract_text()})
    assert Counter(r[0] for r in rows)=={BASE:14,LEGEND:7,AUTO:12,LEGEND_AUTO:7}
    assert len(rows)==len({r[1] for r in rows})==40 and rows[-1]==[LEGEND_AUTO,'LSP-7A','Undertaker','2']
    return rows,raw


def build():
    path=generic.CACHE/(SLUG+'.pdf')
    subprocess.run(['curl','-fsSL','--retry','2','--max-time','60',URL,'-o',str(path)],check=True);path.with_suffix('.pdf.url').write_text(URL)
    rows,raw=physical_rows(path)
    record={'title':TITLE,'manufacturer':'Topps / Bowman','sport':'wrestling','year':'2026','slug':SLUG,'page':'sets/'+SLUG+'.html',
        'sourcePage':PAGE,'checklistUrl':URL,'releaseStatus':'Unverified','releaseDate':None,'verified':datetime.date.today().isoformat()}
    dest=ROOT/'data/imports'/(SLUG+'.json');prior=dest.read_bytes() if dest.exists() else None
    try:
        record=generic.run(record);assert 'importIssue' not in record,record
        baseline=json.loads(dest.read_text())
    finally:
        if prior is not None:dest.write_bytes(prior)
        elif dest.exists():dest.unlink()
    captions=[r for r in baseline['rows'] if r[1]=='2026'];assert len(captions)==1 and captions[0][2]=='WWE Topps Now WrestleMania Vegas Set'
    assert [r[1:] for r in rows]==[r[1:] for r in baseline['rows'] if r[1]!='2026'] and not baseline.get('odds')
    proof_path=ROOT/EVIDENCE;proof=json.loads(proof_path.read_text());ph=hashlib.sha256(proof_path.read_bytes()).hexdigest()
    assert proof['url']==PAGE and proof['title']==TITLE+' - PR: 5847' and proof['checklistUrl']==URL
    fields=dict(proof['specs']);assert fields['Available From']=='Apr 13, 2026' and fields['Available Until']=='Apr 20, 2026'
    assert fields['Sub Categories']=='Combat' and fields['Product Year']=='2026'
    lines=[line.strip() for line in proof['overview'].splitlines() if line.strip()]
    for name,limit in COLORS:assert limit+' '+name in lines
    assert 'Serial-numbered base card parallel' in lines and all(term in lines for term in BOUNDS.values())
    evidence={'evidenceFile':EVIDENCE,'evidenceSha256':ph}
    qualification='Base-card foil program only; no Legend Short Print or autograph color eligibility is inferred. The two autograph programs retain separate qualified /5-or-lower statements.'
    specs=[{'name':BASE,'worksheet':'Official product Overview · base-only foil terms','source':PAGE,
        'headers':['Published parallel','Published numbering','Qualification','Official source'],
        'rows':[[name,limit,qualification,PAGE] for name,limit in COLORS],**evidence}]
    for family,term in BOUNDS.items():
        specs.append({'name':family,'worksheet':'Official product Overview · exact qualified autograph program','source':PAGE,
            'headers':['Published statement','Qualification','Official source'],
            'rows':[[term,'Upper bound only; no named autograph colors or exact per-card serial limit is inferred.',PAGE]],**evidence})
    specs.append({'name':LEGEND,'worksheet':'Official product Overview · Legend Short Prints','source':PAGE,
        'headers':['Published statement','Qualification','Official source'],
        'rows':[['WWE Legend Short Print','The seven printed roster entries do not establish a print run, serial ladder or autograph eligibility outside the separate published variation roster.',PAGE]],**evidence})
    specs.append({'name':'Set-wide product configuration, sale dates and event context','worksheet':'Official product title, Overview, Description and Specs · bundle scope','source':PAGE,
        'headers':['Official field','Published term','Qualification'],
        'rows':[['Published bundle print run (title)','5847','Bundle-level only; not assigned to each of the forty checklist entries.'],
                ['Published bundle contents',lines[1],'14 base cards plus one additional card; the PDF lists forty entries across four programs.'],
                ['Event context','WrestleMania 42 · April 18–19','Event dates in Description, not a general product release date.'],
                *[[k,v,'Official sale window, not a general release date.' if k.startswith('Available ') else ''] for k,v in fields.items()]],**evidence})
    payload={'title':TITLE,'headers':['Checklist section','Card number','Subject','Source page'],'originalPrintedHeaders':['Card No.','Subject'],
        'rows':rows,'source':URL,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rawPages':raw,'importKind':'topps-grid-pdf','sectionColumn':0,
        'publishedSpecifications':specs,'sourceProducts':[{**proof,'snapshotFile':EVIDENCE,'sha256':ph}]}
    mappings=[dict(family=BASE,name=name,numbering=limit,qualification=qualification,sourceHeading='Parallels:',source=PAGE,**evidence) for name,limit in COLORS]
    record.update(importKind='topps-grid-pdf',dedicatedParser='scripts/import_topps_now_wrestlemania_2026.py',rowCount=40,sections=4,parallelData=True,publishedOdds=False,sha256=payload['sha256'],coverageComplete=False,
        description='A made-to-order 15-card bundle: fourteen base cards plus one additional parallel, Legend short print, autograph or redemption. The PDF lists forty numbered entries across four programs. Five base-only foil limits are published; both autograph programs retain separate /5-or-lower qualifications. Bundle PR5847 and April 13–20 sale dates are product-level facts; WrestleMania event dates are not a general release date.',
        catalogEvidence='All forty physical number/Subject cells retain the four exact program headings. Base 1 closes Cody Rhodes’s nickname with a double quote; autograph 1-A prints a closing apostrophe. LSP-4A prints Bret "Hit Man" without Hart; do not copy the surname from LSP-4. Five base foil limits /50,/25,/10,/5,/1 never number Legend short prints or either autograph program. Separate qualified /5-or-lower terms apply to BASE AUTOGRAPH VARIATIONS and LEGEND SP AUTOGRAPH VARIATIONS without named color joins. No teams, rookie flags, pack formats, pack odds, per-card print runs or general release are invented. Exhaustive eligibility and historical NOW coverage remain unverified.',
        dataAudit='All 14 base, seven Legend short print, twelve base autograph and seven Legend autograph rows reconcile with independent PDF text. The year-leading title is not a card; original quote differences and the omitted autograph surname remain literal.')
    dest.write_text(json.dumps(payload,ensure_ascii=False)+'\n')
    for name in ['topps-product-official-catalog.json','set-catalog.json']:
        p=ROOT/'data'/name;catalog=json.loads(p.read_text());sets=catalog['sets'] if isinstance(catalog,dict) else catalog
        index=next((i for i,s in enumerate(sets) if s['slug']==SLUG),None)
        if index is None:sets.append(record)
        else:sets[index]=record
        p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    p=ROOT/'data/parallel-specifications.json';registry=json.loads(p.read_text());registry['sets'][SLUG]=mappings;p.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Imported 40 WrestleMania NOW physical rows, five base-only foil limits and separate qualified autograph bounds; original printed subject differences preserved.')

if __name__=='__main__':build()
