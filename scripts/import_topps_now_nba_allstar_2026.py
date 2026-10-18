"""Preserve NBA NOW All-Star physical columns and qualified parallel scopes."""
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
SLUG='topps-bowman-2026-nba-topps-now-all-star-game-set'
TITLE='2026 All-Star Game Set - NBA Topps NOW®'
PAGE='https://www.topps.com/products/2026-all-star-game-set-nba-topps-now%C2%AE-26-card-set'
URL='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_NBA_Topps_Now_All-Star_Game_Set_-_Checklist.pdf?v=1787961796'
EVIDENCE='data/parallel-audit-sources/nba-now-all-star-2026-product-20261018.json'
BASE='BASE CARDS'
AUTO='AUTOGRAPH SUBJECTS'
COLORS=[('Gold Foil','/50'),('Orange Foil','/25'),('Black Foil','/10'),('Red Foil','/5'),('FoilFractor','/1')]


def physical_rows(path):
    rows=[];raw=[]
    with pdfplumber.open(path) as doc:
        assert len(doc.pages)==2
        for pn,page in enumerate(doc.pages,1):
            assert (page.width,page.height)==(612,792)
            words=page.extract_words()
            divider=next((w['top'] for w in words if w['text']=='AUTOGRAPH'),0)
            anchors=[w for w in words if w['x0']<120 and re.fullmatch(r'\d+(?:-A)?',w['text']) and (pn>1 or w['top']>100)]
            for anchor in anchors:
                y=anchor['top']
                cells=[(page.crop((lo,y-.5,hi,y+13)).extract_text() or '').strip()
                       for lo,hi in [(50,120),(120,280),(280,325),(325,410)]]
                assert cells[0]==anchor['text'] and all(cells),cells
                assert cells[2] in {'G','F','C'} and cells[3] in {'USA Stars','USA Stripes','World'},cells
                assert all('\n' not in cell for cell in cells),cells
                rows.append([BASE if pn==1 and y<divider else AUTO,*cells,str(pn)])
            raw.append({'page':pn,'text':page.extract_text()})
    assert Counter(r[0] for r in rows)=={BASE:25,AUTO:12}
    assert [r[1] for r in rows if r[0]==BASE]==[str(n) for n in range(1,26)]
    assert len(rows)==len({r[1] for r in rows})==37 and rows[-1]==[AUTO,'21-A','Chet Holmgren','C','USA Stars','2']
    return rows,raw


def build():
    path=generic.CACHE/(SLUG+'.pdf')
    subprocess.run(['curl','-fsSL','--retry','2','--max-time','60',URL,'-o',str(path)],check=True)
    path.with_suffix('.pdf.url').write_text(URL)
    rows,raw=physical_rows(path)
    record={'title':TITLE,'manufacturer':'Topps / Bowman','sport':'basketball','year':'2026',
            'slug':SLUG,'page':'sets/'+SLUG+'.html','sourcePage':PAGE,'checklistUrl':URL,
            'releaseStatus':'Unverified','releaseDate':None,'verified':datetime.date.today().isoformat()}
    dest=ROOT/'data/imports'/(SLUG+'.json');prior=dest.read_bytes() if dest.exists() else None
    try:
        record=generic.run(record);assert 'importIssue' not in record,record
        baseline=json.loads(dest.read_text())
    finally:
        if prior is not None:dest.write_bytes(prior)
        elif dest.exists():dest.unlink()
    captions=[r for r in baseline['rows'] if r[1]=='2026']
    assert len(captions)==1 and captions[0][2]=='NBA Topps Now All-Star Game Set'
    baseline_rows=[r for r in baseline['rows'] if r[1]!='2026']
    assert [r[1] for r in rows]==[r[1] for r in baseline_rows]
    compact=lambda text:re.sub(r'\s+','',text)
    assert [compact(''.join(r[2:5])) for r in rows]==[compact(r[2]) for r in baseline_rows]
    proof_path=ROOT/EVIDENCE;proof=json.loads(proof_path.read_text());ph=hashlib.sha256(proof_path.read_bytes()).hexdigest()
    assert proof['url']==PAGE and proof['checklistUrl']==URL and proof['title']==TITLE+' - 26 Card Set - PR: 4967'
    fields=dict(line.split('  | ',1) for line in proof['lines'] if '  | ' in line)
    assert fields['Available From']=='Feb 9, 2026' and fields['Available Until']=='Feb 16, 2026'
    assert fields['Product Year']=='2026' and fields['Sub Type']=='Set'
    for name,limit in COLORS:assert limit+' '+name in proof['lines']
    auto_term='Redemption for autographed base card parallel /5 or lower'
    assert auto_term in proof['lines'] and 'Sequentially numbered base card parallel' in proof['lines']
    assert 'All-Star Parallel' in proof['lines'] and 'Parallels:' in proof['lines']
    evidence={'evidenceFile':EVIDENCE,'evidenceSha256':ph}
    qualification='Base-card parallel program only; individual-card eligibility is not inferred. Autograph redemptions have a separate /5-or-lower statement without named color joins.'
    unknown='The official page names All-Star Parallel without a numeric limit or an explicitly unnumbered status.'
    terms=[['All-Star Parallel','Not stated',unknown,PAGE],*[[name,limit,qualification,PAGE] for name,limit in COLORS]]
    specifications=[{'name':BASE,'worksheet':'Official product page · base-card parallel terms','source':PAGE,
                     'headers':['Published parallel','Published numbering','Qualification','Official source'],'rows':terms,**evidence},
                    {'name':AUTO,'worksheet':'Official product page · qualified autograph statement','source':PAGE,
                     'headers':['Published statement','Qualification','Official source'],
                     'rows':[[auto_term,'Upper bound only; no named autograph colors or exact per-card numbering is inferred.',PAGE]],**evidence},
                    {'name':'Set-wide product configuration and sale dates','worksheet':'Official product page · bundle scope','source':PAGE,
                     'headers':['Official field','Published term','Qualification'],
                     'rows':[['Published bundle print run (title)','4967','Published for the bundle; not assigned to every checklist card.'],
                             ['Published bundle contents',proof['lines'][proof['lines'].index('Overview')+2],'25 base cards plus one additional parallel/redemption; the PDF lists 37 entries across two programs.'],
                             *[[k,v,'Official sale window, not a general release date.' if k in {'Available From','Available Until'} else ''] for k,v in fields.items()]],**evidence}]
    payload={'title':TITLE,'headers':['Checklist section','Card number','Player','Position','Team','Source page'],
             'originalPrintedHeaders':['Card No.','Player','Position','Team'],
             'rows':rows,'source':URL,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
             'rawPages':raw,'importKind':'topps-grid-pdf','sectionColumn':0,'publishedSpecifications':specifications,
             'sourceProducts':[{**proof,'snapshotFile':EVIDENCE,'sha256':ph}]}
    mappings=[dict(family=BASE,name=name,numbering=limit,qualification=qual,sourceHeading='Parallels:',source=PAGE,**evidence)
              for name,limit,qual,_ in terms]
    dest.write_text(json.dumps(payload,ensure_ascii=False)+'\n')
    record.update(importKind='topps-grid-pdf',dedicatedParser='scripts/import_topps_now_nba_allstar_2026.py',
                  rowCount=37,sections=2,parallelData=True,publishedOdds=False,sha256=payload['sha256'],
                  description='A made-to-order 26-card bundle: 25 selected All-Stars plus one additional parallel or autograph redemption. The PDF lists 37 entries across two programs, with literal USA Stars, USA Stripes and World teams. Five base foil limits are published; All-Star Parallel numbering and exact autograph numbering remain unstated. Bundle print run 4967 and February 9–16 sale dates remain product-level facts.',
                  catalogEvidence='All 37 original PDF rows retain Player, Position and Team, including the second-page Chet Holmgren 21-A continuation. USA Stars, USA Stripes and World are the published teams; NBA club assignments and rookie flags are not supplied. Five foil limits /50, /25, /10, /5 and /1 stay in BASE CARDS. All-Star Parallel has no published numbering status; AUTOGRAPH SUBJECTS retains only the qualified /5-or-lower upper bound. Bundle PR4967 and February 9–16, 2026 availability do not establish per-card print runs, pack odds or a general release date. Exhaustive eligibility and historical NOW coverage remain unverified.',
                  dataAudit='All 25 base and 12 autograph rows reconcile with independent PDF text. The year-leading title is not a card; accents, positions and All-Star team cells remain literal. No teams, rookies, print runs, autograph ladders or odds are inferred.')
    for name in ['topps-product-official-catalog.json','set-catalog.json']:
        file=ROOT/'data'/name;catalog=json.loads(file.read_text());sets=catalog['sets'] if isinstance(catalog,dict) else catalog
        index=next((i for i,s in enumerate(sets) if s['slug']==SLUG),None)
        if index is None:sets.append(record)
        else:sets[index]=record
        file.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    file=ROOT/'data/parallel-specifications.json';registry=json.loads(file.read_text());registry['sets'][SLUG]=mappings
    file.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Imported 37 NBA All-Star NOW rows, five base foil limits and named All-Star Parallel with unstated numbering; autograph scope stays qualified.')


if __name__=='__main__':build()
