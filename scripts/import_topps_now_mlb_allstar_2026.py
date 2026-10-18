"""Import the official MLB NOW All-Star roster and exact base foil terms."""
import datetime
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

import pdfplumber
import import_official_catalog as generic

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-mlb-topps-now-all-star-game-set'
TITLE = '2026 All-Star Game Set - MLB Topps NOW®'
PAGE = 'https://www.topps.com/products/2026-all-star-game-set-mlb-topps-now%C2%AE-19-card-set'
URL = 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Now_MLB_ASG_Set_Checklist.pdf?v=1787973837'
EVIDENCE = 'data/parallel-audit-sources/mlb-now-all-star-2026-product-20261017.json'
BASE = '2026 Topps NOW MLB All-Star Game Set'
AUTO = 'AUTOGRAPH CONTENT'
COLORS = [('Green Foil','/99'),('Gold Foil','/50'),('Orange Foil','/25'),
          ('Black Foil','/10'),('Red Foil','/5'),('FoilFractor','/1')]


def physical_rows(path):
    rows = []
    with pdfplumber.open(path) as doc:
        assert len(doc.pages) == 1 and (doc.pages[0].width,doc.pages[0].height) == (612,792)
        page = doc.pages[0]
        words = page.extract_words()
        divider = next(w['top'] for w in words if w['text']=='AUTOGRAPH')
        anchors = [w for w in words if w['x0'] < 110 and re.fullmatch('ASG-[A-Z]+',w['text'])]
        for anchor in anchors:
            y = anchor['top']
            cells = [(page.crop((left,y-.5,right,y+13)).extract_text() or '').strip()
                     for left,right in [(50,118),(118,233),(233,350),(350,382),(382,420)]]
            assert cells[0] == anchor['text'] and all(cells[:4]) and cells[4] in {'','RC'}, cells
            assert all('\n' not in cell for cell in cells),cells
            rows.append([BASE if y<divider else AUTO,*cells,'1'])
        raw = [{'page':1,'text':page.extract_text()}]
    assert Counter(r[0] for r in rows) == {BASE:18,AUTO:17}
    assert len(rows)==len({r[1] for r in rows})==35 and sum(r[5]=='RC' for r in rows)==8
    return rows,raw


def build():
    path = generic.CACHE/(SLUG+'.pdf')
    subprocess.run(['curl','-fsSL','--retry','2','--max-time','60',URL,'-o',str(path)],check=True)
    path.with_suffix('.pdf.url').write_text(URL)
    rows,raw = physical_rows(path)
    record = {'title':TITLE,'manufacturer':'Topps / Bowman','sport':'baseball','year':'2026',
              'slug':SLUG,'page':'sets/'+SLUG+'.html','sourcePage':PAGE,'checklistUrl':URL,
              'releaseStatus':'Unverified','releaseDate':None,'verified':datetime.date.today().isoformat()}
    dest = ROOT/'data/imports'/(SLUG+'.json')
    prior = dest.read_bytes() if dest.exists() else None
    try:
        record=generic.run(record)
        assert 'importIssue' not in record,record
        baseline=json.loads(dest.read_text())
    finally:
        if prior is not None:dest.write_bytes(prior)
        elif dest.exists():dest.unlink()
    assert [r[1] for r in rows]==[r[1] for r in baseline['rows']]
    compact=lambda s:re.sub(r'\s+','',s)
    assert [compact(''.join(r[2:6])) for r in rows]==[compact(r[2]) for r in baseline['rows']]
    proof_path=ROOT/EVIDENCE;proof=json.loads(proof_path.read_text());ph=hashlib.sha256(proof_path.read_bytes()).hexdigest()
    assert proof['url']==PAGE and proof['checklistUrl']==URL and proof['title']==TITLE+' - 19 Card Set - PR: 16306'
    fields=dict(l.split('  | ',1) for l in proof['lines'] if '  | ' in l)
    assert fields['Available From']=='Jul 9, 2026' and fields['Available Until']=='Jul 16, 2026'
    assert fields['Product Year']=='2026' and fields['Sub Type']=='Set'
    for name,numbering in COLORS:assert numbering+' '+name in proof['lines']
    assert 'Unnumbered All-Star Game LogoFractor' in proof['lines']
    auto_term='Redemption for autographed base card parallel /10 or lower'
    assert auto_term in proof['lines']
    evidence={'evidenceFile':EVIDENCE,'evidenceSha256':ph}
    qualification='Only the base-card parallel program; individual-card eligibility in every color is not inferred. Autograph redemptions have a separate /10-or-lower statement with no named color ladder.'
    guide_rows=[[name,limit,qualification,PAGE] for name,limit in COLORS]
    guide_rows.append(['All-Star Game LogoFractor','Unnumbered','Explicitly unnumbered; individual-card eligibility is not inferred.',PAGE])
    specs=[{'name':BASE,'worksheet':'Official product page · base-card parallels only','source':PAGE,
            'headers':['Published parallel','Published numbering','Qualification','Official source'],
            'rows':guide_rows,**evidence},
           {'name':AUTO,'worksheet':'Official product page · qualified autograph statement','source':PAGE,
            'headers':['Published statement','Qualification','Official source'],
            'rows':[[auto_term,'Upper bound only; no named autograph color ladder or exact per-card numbering is inferred.',PAGE]],**evidence},
           {'name':'Set-wide product configuration and sale dates','worksheet':'Official product page · bundle scope','source':PAGE,
            'headers':['Official field','Published term','Qualification'],
            'rows':[['Published bundle print run (title)','16306','Published for the bundle; not assigned to every checklist entry.'],
                    ['Published bundle contents',proof['lines'][proof['lines'].index('Overview')+2],'18 base cards plus one additional parallel/redemption; the PDF lists 35 entries across two programs.'],
                    *[[k,v,'Official sale window, not a general release date.' if k in {'Available From','Available Until'} else ''] for k,v in fields.items()]],**evidence}]
    payload={'title':TITLE,'headers':['Checklist section','Card number','Player','Team','Pos.','RC','Source page'],
             'originalPrintedHeaders':['Card #','Player','Team','Pos.',''],
             'sourceColumnNotes':'The final flag column has no printed header; all eight literal RC marks are retained without adding flags to other rows.',
             'rows':rows,'source':URL,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
             'rawPages':raw,'importKind':'topps-grid-pdf','sectionColumn':0,'publishedSpecifications':specs,
             'sourceProducts':[{**proof,'snapshotFile':EVIDENCE,'sha256':ph}]}
    mappings=[dict(family=BASE,name=name,numbering=limit,qualification=qualification,
                   sourceHeading='Foil-Numbered Parallel Card numbered to /99 or lower:',source=PAGE,**evidence)
              for name,limit in COLORS]
    mappings.append(dict(family=BASE,name='All-Star Game LogoFractor',numbering='Unnumbered',
                         qualification='Explicitly unnumbered; individual-card eligibility is not inferred.',
                         sourceHeading='Unnumbered All-Star Game LogoFractor',source=PAGE,**evidence))
    dest.write_text(json.dumps(payload,ensure_ascii=False)+'\n')
    record.update(importKind='topps-grid-pdf',dedicatedParser='scripts/import_topps_now_mlb_allstar_2026.py',
                  rowCount=35,sections=2,parallelData=True,publishedOdds=False,sha256=payload['sha256'],
                  description='A made-to-order 19-card bundle: 18 base cards plus one additional parallel or autograph redemption. The PDF lists 35 entries across two programs. Base foil numbering and an unnumbered LogoFractor are published; autograph numbering remains a qualified upper bound. Bundle print run 16306 and July 9–16 sale dates remain product-level facts.',
                  catalogEvidence='All 35 product-linked PDF entries retain original Player, Team, Pos. and eight literal unlabelled RC marks. Exact base foil terms /99, /50, /25, /10, /5 and /1 do not apply to AUTOGRAPH CONTENT. Autograph redemptions have a /10-or-lower upper bound without named parallel joins. Bundle PR16306 is not a per-card print run or pack probability. July 9–16, 2026 store availability establishes calendar-year scope, not a verified general release date. Numeric pack odds and exhaustive parallel eligibility remain unverified; historical NOW coverage stays partial.',
                  dataAudit='Every physical cell reconciles with independent PDF text. The source has 18 base entries and 17 autograph entries, eight RC marks and Ohtani P/DH in base versus DH in autographs. No teams, flags, print runs or autograph color numbering are inferred.')
    for name in ['topps-product-official-catalog.json','set-catalog.json']:
        file=ROOT/'data'/name;catalog=json.loads(file.read_text());sets=catalog['sets'] if isinstance(catalog,dict) else catalog
        index=next((i for i,s in enumerate(sets) if s['slug']==SLUG),None)
        if index is None:sets.append(record)
        else:sets[index]=record
        file.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    file=ROOT/'data/parallel-specifications.json';registry=json.loads(file.read_text());registry['sets'][SLUG]=mappings
    file.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Imported 35 MLB All-Star NOW entries, eight literal RC marks and seven exact base-parallel terms; autograph scope remains qualified.')


if __name__=='__main__':build()
