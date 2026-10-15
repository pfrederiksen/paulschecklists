"""Preserve Disney Sapphire physical character, actor, property and MLB fields."""
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from import_official_catalog import run
from import_topps_tribute_2026 import acquire, text
from official_odds_layout import physical_odds_pdf

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-chrome-disney-sapphire-edition'
PARSER='scripts/import_topps_disney_sapphire_2026.py'
PROOF=ROOT/'data/parallel-audit-sources/disney-sapphire-2026-product-20261015.json'
FAMILIES={'BASE CARDS','MICKEY AND FRIENDS MLB HOME JERSEY SET','BEAUTY AND THE BEAST 35TH ANNIVERSARY',
 'HIDDEN GEMS','INFINITE SAPPHIRE','THE ROSE SHADOWBOX','DISNEY CHROME FACSIMILE AUTOGRAPHS',
 'DISNEY CHROME FACSIMILE DUAL AUTOGRAPHS','DISNEY CHROME FACSIMILE TRIPLE AUTOGRAPHS',
 'DISNEY CHROME FACSIMILE QUAD AUTOGRAPHS','DISNEY CHANNEL AUTOGRAPH VARIATION','AUTHENTIC AUTOGRAPHS',
 'DUAL AUTOGRAPHS','TRIPLE AUTOGRAPHS','QUAD AUTOGRAPHS'}
HEADERS=['Checklist section','Card number','Player / subjects','Source page','Character','Subject','Property',
         'First Name','Last Name','Character Name','Team','Division','Official unlabelled annotation']

def read_cards(path):
    rows,raw,notes=[],[],[];family='BASE CARDS'
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==9
        for pn,page in enumerate(pdf.pages,1):
            raw.append({'page':pn,'text':page.extract_text()})
            groups=[]
            for c in page.chars:
                y=c['matrix'][5];cs=next((cs for baseline,cs in groups if abs(y-baseline)<.6),None)
                if cs is None:cs=[];groups.append((y,cs))
                cs.append(c)
            for y,cs in sorted(groups,reverse=True):
                line=text(cs)
                if not line:continue
                if line.startswith(('Checklists provided','product at the time')):
                    notes.append([str(pn),line]);continue
                if line.startswith('Card Number'):
                    notes.append([str(pn),line]);continue
                if line in FAMILIES:family=line;continue
                char=subject=prop=first=last=character=team=division=annotation=''
                number=text([c for c in cs if c['x0']<140])
                if pn<=5 and family=='BASE CARDS':
                    char=text([c for c in cs if 140<=c['x0']<310])
                    prop=text([c for c in cs if 310<=c['x0']<545])
                    annotation=text([c for c in cs if c['x0']>=545])
                elif family=='MICKEY AND FRIENDS MLB HOME JERSEY SET':
                    subject=text([c for c in cs if 140<=c['x0']<310])
                    team=text([c for c in cs if 310<=c['x0']<480])
                    division=text([c for c in cs if c['x0']>=480])
                elif pn<=7:
                    subject=text([c for c in cs if 140<=c['x0']<370])
                    prop=text([c for c in cs if c['x0']>=370])
                else:
                    first=text([c for c in cs if 140<=c['x0']<250])
                    last=text([c for c in cs if 250<=c['x0']<332])
                    character=text([c for c in cs if 332<=c['x0']<445])
                    prop=text([c for c in cs if c['x0']>=445])
                name=' '.join(c for c in [first,last] if c) or char or subject
                assert re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and name,(pn,line,number,name)
                assert annotation in {'','DEBUT'},(pn,line,annotation)
                rows.append([family,number,name,str(pn),char,subject,prop,first,last,character,team,division,annotation])
    assert len(rows)==394 and len({r[0] for r in rows})==15
    assert {int(r[1]) for r in rows if r[0]=='BASE CARDS'}==set(range(1,201))
    return rows,raw,notes

def build():
    proof=json.loads(PROOF.read_text());proof_hash=hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence=dict(source=proof['source'],evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=proof_hash)
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
    digest=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');odds_hash=acquire(proof['oddsUrl'],op)
    odds,formats,odds_raw,issues=physical_odds_pdf(op)
    assert len(odds)==54 and formats==['Sapphire'] and not issues
    aliases={f.title():f for f in FAMILIES}
    aliases.update({'Base Card':'BASE CARDS','The Rose':'THE ROSE SHADOWBOX',
                    'Facsimile Autographs':'DISNEY CHROME FACSIMILE AUTOGRAPHS',
                    'Dual Facsimile Autographs':'DISNEY CHROME FACSIMILE DUAL AUTOGRAPHS',
                    'Triple Facsimile Autographs':'DISNEY CHROME FACSIMILE TRIPLE AUTOGRAPHS',
                    'Quad Facsimile Autographs':'DISNEY CHROME FACSIMILE QUAD AUTOGRAPHS',
                    'Mickey & Friends MLB Home Jersey Set':'MICKEY AND FRIENDS MLB HOME JERSEY SET',
                    'Disney Dual Autographs':'DUAL AUTOGRAPHS','Disney Triple Autographs':'TRIPLE AUTOGRAPHS',
                    'Disney Quad Autographs':'QUAD AUTOGRAPHS'})
    for odd in odds:
        matches=[k for k in aliases if odd['name'].casefold()==k.casefold() or odd['name'].casefold().startswith(k.casefold()+' ')]
        assert matches,odd['name'];odd['family']=aliases[max(matches,key=len)]
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text())
    record=next((r for r in catalog['sets'] if r['slug']==SLUG),None)
    if record is None:
        record=dict(title='2026 Topps Chrome Disney Sapphire Edition',manufacturer='Topps / Bowman',sport='entertainment',year='2026',
                    slug=SLUG,page='sets/'+SLUG+'.html',sourcePage=proof['productSource'],checklistUrl=proof['checklistUrl'],
                    oddsUrl=proof['oddsUrl'],releaseStatus='Unverified',releaseDate=None,verified=proof['observed'],
                    catalogEvidence='Official product page links a separate 2026 Sapphire checklist; exact release date is unverified.')
        record=run(record)
        assert record.get('tableData');catalog['sets'].append(record)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    note=('All 394 printed subject rows / 336 family-card identities across 15 sections retain physical Character, Subject, Property, '
          'First Name, Last Name, Character Name, Team, Division and unlabelled DEBUT fields. All 200 base numbers and the 30 '
          'MLBH-31 through MLBH-60 team assignments remain as printed; teams are blank outside the jersey program. Repeated dual, '
          'triple and quad actor/character rows retain every signer. BASE CARDS labels the unheaded first table; no rookie flags '
          'or absent Property values are inferred. All 54 Sapphire odds preserve literal 01:14:00, 1:26854 and Padpradascha spelling. '
          'The Sapphire format is published but no ratio unit is named; box contents do not establish per-pack odds. Named serial '
          'limits and an exact release date are unverified; no regular Chrome numbering is copied into Sapphire.')
    data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,
                rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,
                importKind='pdf',dedicatedParser=PARSER,sectionColumn=0,odds=odds,formats=formats,
                oddsSource=proof['oddsUrl'],oddsRawPages=odds_raw,oddsSha256=odds_hash,oddsIssues=[],oddsParser='scripts/official_odds_layout.py',
                formatNamesPublished=True,oddsUnitsPublished=False,
                publishedSpecifications=[dict(name='Manufacturer box distribution',worksheet='Official product page; box distribution is not pack odds',
                  headers=['Published field','Published value'],rows=proof['boxContents'],**evidence)],
                sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(rowCount=len(rows),sections=15,importKind=data['importKind'],dedicatedParser=PARSER,sha256=digest,odds=54,formats=1,
                  oddsParser=data['oddsParser'],oddsImportIssues=0,verified=proof['observed'],catalogEvidence=note,dataAudit=note,
                  sourceObservation=dict(file=evidence['evidenceFile'],sha256=proof_hash,source=proof['productSource']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text())
    inventory=[record if r['slug']==SLUG else r for r in inventory]
    if not any(r['slug']==SLUG for r in inventory):inventory.append(record)
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    oddsp=ROOT/'data/topps-official-odds.json';odds_inventory=json.loads(oddsp.read_text())
    # Preserve previously observed global catalog records verbatim.
    if not any(o['url']==proof['oddsUrl'] and o.get('sha256')==odds_hash for o in odds_inventory):
        odds_inventory.append(dict(title=record['title'],url=proof['oddsUrl'],source=proof['productSource'],sha256=odds_hash))
    oddsp.write_text(json.dumps(odds_inventory,ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text())
    family='Unverified Sapphire numbering and calendar release date'
    registry['conflicts']=[c for c in registry['conflicts'] if not(c['slug']==SLUG and c['family']==family)]
    registry['conflicts'].append(dict(slug=SLUG,family=family,gap=' '.join(proof['remainingGaps'][:3]),**evidence))
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print(f'Disney Sapphire: {len(rows)} source rows, {len({tuple(r[:2]) for r in rows})} identities, {sum(r[12]=="DEBUT" for r in rows)} DEBUT annotations, 54 literal Sapphire ratios. Numbering and release-date audits remain incomplete.')

if __name__=='__main__':build()
