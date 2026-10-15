"""Independently reconcile every new checklist glyph and literal odds cell."""
import collections
import hashlib
import json
import re
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
F='topps-bowman-2026-topps-chrome-football';G='topps-bowman-2026-garbage-pail-kids-halloween'
norm=lambda s:re.sub(r'\s+','',s)
catalog={s['slug']:s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets']}
for slug in [F,G]:
    d=json.loads((ROOT/'data/imports'/(slug+'.json')).read_text());p=ROOT/'data/catalog-sources/downloads'/(slug+'.pdf')
    assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']==catalog[slug]['sha256']
    assert d['originalSubjectRows']==d['rows'] and d['dedicatedParser']=='scripts/import_topps_october15_2026.py'
    families={norm(r[0]) for r in d['rows']};reader=PdfReader(p)
    for pn,page in enumerate(reader.pages,1):
        lines=page.extract_text(extraction_mode='layout').splitlines()
        actual=[];started=pn!=1
        for line in lines:
            s=norm(line)
            if not s:continue
            if not started:
                if s==('BASE' if slug==F else 'Card#SubsetNameCardBack'):started=True
                continue
            if s in families|{norm(x) for x in ['BASE','INSERT','AUTOGRAPH','AUTOGRAPH RELIC','RELIC','SLIME BASE PARALLELS','WRAPPERS','WRAPPER PARALLEL']}:continue
            actual.append(s)
        if slug==F:expected=[norm(''.join(r[1:5])) for r in d['rows'] if r[5]==str(pn)]
        else:
            expected=[norm(r[1]+r[3]+r[2]+r[7]) for r in d['rows'] if r[4]==str(pn)]
            original=next(s for s in d['publishedSpecifications'] if s['name']=='Original checklist parallel and wrapper rows')
            summary=[norm(''.join(r[1:5])) for r in original['rows'] if r[5]==str(pn)]
            # Summary rows have original page positions among the card tables.
            assert collections.Counter(actual)==collections.Counter(expected+summary),(slug,pn,'Every printed row must be retained')
            continue
        assert actual==expected,(slug,pn,'Independent full-page glyph comparison')
    if slug==F:
        assert len(d['rows'])==2382 and len(families)==56 and sum(r[4]=='Rookie' for r in d['rows'])==644
        assert sum(not r[1] for r in d['rows'])==93
        for family,start,end in [('BASE CARDS',1,300),('BASE CARDS LIGHTBOARD LOGO VARIATION',1,300),('BASE CARDS TEAM CAMO VARIATION',1,300),('ROOKIE',301,400),('ROOKIE LIGHTBOARD LOGO VARIATION',301,400),('ROOKIE TEAM CAMO VARIATION',301,400)]:
            assert {int(r[1]) for r in d['rows'] if r[0]==family}==set(range(start,end+1))
        assert next(r for r in d['rows'] if r[0]=='BASE CARDS' and r[1]=='71')[3]=='Los Angeles Rams'
        assert next(r for r in d['rows'] if r[0]=='AWARD WINNERS BASE VARIATION' and r[1]=='71')[3]=='Cleveland Browns'
        assert next(r for r in d['rows'] if r[1]=='LT-1')[2:5]==['','Seattle Seahawks','']
        assert len([r for r in d['rows'] if r[0]=='DUAL AUTOGRAPHS'])==30
        assert any(r[2]=='QB Bills' for r in d['rows'])
        assert all(r[1] not in {'1991','2016','2017','2018'} for r in d['rows'])
        assert d['odds']==[] and d['formats']==[] and not d.get('parallelSpecifications')
        assert catalog[slug]['releaseStatus']=='Upcoming' and catalog[slug]['releaseDate'] is None
    else:
        assert len(d['rows'])==158 and len(families)==6
        assert sum(bool(r[1]) for r in d['rows'])==105
        base=[r for r in d['rows'] if r[0]=='Base'];assert {r[1] for r in base}=={str(n)+side for n in range(1,26) for side in 'AB'}
        scream=[r for r in d['rows'] if r[0]=='SCREAM QUEENS'];assert sum(not r[5] for r in scream)==5
        assert next(r for r in scream if r[1]=='5B')[2]=='Nightmre NANCY'
        assert next(r for r in base if r[1]=='25B')[2]=='Muggin’ MEGAN'
        assert next(r for r in d['rows'] if r[0]=='AUTOGRAPHS' and r[1]=='3')[6]=='Neil Camera'
        artists=[r for r in d['rows'] if not r[1]];assert len(artists)==53
        assert artists[-1][8]=='Vincenzo D’ippolito' and any(r[8]=='Niel Camera' for r in artists)
        assert len(d['odds'])==12 and d['formats']==['SINGLE BOX'] and d['oddsUnitLabel']=='SINGLE BOX' and d['oddsUnitsPublished'] is True
        op=p.with_name(slug+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
        source=[]
        for line in PdfReader(op).pages[0].extract_text(extraction_mode='layout').splitlines():
            m=re.fullmatch(r'\s*(.+?)\s+(1:\d+)\s*',line)
            if m:source.append((norm(m[1]),m[2]))
        assert source==[(norm(o['name']),o['values']['SINGLE BOX']) for o in d['odds']]
        assert {s['oddsName']:s['numbering'] for s in d['parallelSpecifications']}==dict(zip([o['name'] for o in d['odds'][:5]],['/50','/25','/10','/5','/1']))
        assert all(s['family']=='Base' for s in d['parallelSpecifications'])
        assert 'WRAPPERS' not in {r[0] for r in d['rows']}
        assert catalog[slug]['releaseStatus']=='Upcoming' and catalog[slug]['releaseDate']=='2026-10-22'
    assert catalog[slug]['coverageComplete'] is True
proof=ROOT/'data/parallel-audit-sources/topps-october15-2026-products.json'
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text())
for s in registry['sets'][G]:assert hashlib.sha256(proof.read_bytes()).hexdigest()==s['evidenceSha256']
assert {c['slug'] for c in registry['conflicts'] if c['slug'] in {F,G}}=={F,G}
print('Verified 2,382 Chrome Football rows, six complete programs, 644 Rookie marks, 93 redemptions; 105 GPK cards, 53 artists, 12 literal SINGLE BOX odds and five Base-only limits. Preorder/release distinctions retained.')
