"""Retain Tribute's physical subject/team/rookie cells and literal odds."""
import hashlib
import json
import re
import urllib.request
from pathlib import Path
import pdfplumber
from official_odds_layout import physical_odds_pdf

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-tribute-baseball'
PARSER='scripts/import_topps_tribute_2026.py'
PROOF=ROOT/'data/parallel-audit-sources/tribute-baseball-2026-guide-20261015.json'
FAMILIES={
    'BASE CARDS','TRIBUTE CAREER ACHIEVEMENT AWARD CONTINUITY BARRY BONDS','TRIBUTE AUTOGRAPHS',
    'PILLARS OF THE GAME AUTOGRAPHS','CREST CALLIGRAPHY','LEAGUE INAUGURATION AUTOGRAPHS',
    'TRIBUTE TO TOPPS','CALLING THE SHOT DUAL AUTOGRAPHS','TRIBUTE TANDEM DUAL AUTOGRAPHS',
    'TRUE TO THE GAME','TRIBUTE CAREER ACHIEVEMENT AWARD CONTINUITY BARRY BONDS AUTO','TRIBUTE TO CLEATS',
    'TRIBUTE TO THREADS AUTOGRAPH RELICS','AUTOGRAPH PATCHES','PRIME PATCH AUTOGRAPH RELICS',
    'MILESTONE RELICS JUMBO BLACK AUTOGRAPH','STAMP OF APPROVAL','TRIBUTE JUMBO RELIC','DUAL RELICS',
    'TRIBUTE TRIPLE RELICS','TRIBUTARIES','MILESTONE RELICS',
}

def acquire(url,path):
    with urllib.request.urlopen(url,timeout=45) as response:blob=response.read()
    assert blob.startswith(b'%PDF-')
    temp=path.with_suffix('.part');temp.write_bytes(blob);temp.replace(path)
    path.with_suffix('.pdf.url').write_text(url)
    return hashlib.sha256(blob).hexdigest()

def text(chars):return ' '.join(''.join(c['text'] for c in chars).split())

def read_cards(path):
    rows,raw,notes=[],[],[];family=None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==16
        for pn,page in enumerate(pdf.pages,1):
            raw.append({'page':pn,'text':page.extract_text()})
            groups=[]
            for c in page.chars:
                baseline=c['matrix'][5]
                cs=next((cs for y,cs in groups if abs(y-baseline)<.6),None)
                if cs is None:cs=[];groups.append((baseline,cs))
                cs.append(c)
            for y,cs in sorted(groups,reverse=True):
                line=text(cs)
                if not line:continue
                if pn==1 and y>700:notes.append([str(pn),line]);continue
                if line in FAMILIES:family=line;continue
                if line in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPH RELIC','RELIC'}:continue
                assert family,(pn,line)
                number=text([c for c in cs if c['x0']<130])
                name=text([c for c in cs if 130<=c['x0']<265])
                team=text([c for c in cs if 265<=c['x0']<410])
                rookie=text([c for c in cs if c['x0']>=410])
                assert re.fullmatch(r'\d+|[A-Z]+-[A-Za-z0-9]+',number) and name and rookie in {'','Rookie'},(pn,line,number,name,team,rookie)
                rows.append([family,number,name,team,rookie,str(pn)])
    assert len(rows)==786 and len({r[0] for r in rows})==22
    return rows,raw,notes

def build():
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text())
    record=next(r for r in catalog['sets'] if r['slug']==SLUG)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
    digest=acquire(record['checklistUrl'],path);rows,raw,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');odds_hash=acquire(record['oddsUrl'],op)
    odds,formats,odds_raw,issues=physical_odds_pdf(op)
    assert len(odds)==143 and formats==['Hobby'] and not issues
    aliases={
        'Tribute Career Achievement Award Continuity Insert':'TRIBUTE CAREER ACHIEVEMENT AWARD CONTINUITY BARRY BONDS',
        'Tribute Career Achievement Award Continuity Autographs':'TRIBUTE CAREER ACHIEVEMENT AWARD CONTINUITY BARRY BONDS AUTO',
        'Pillars of the Game':'PILLARS OF THE GAME AUTOGRAPHS',
        'Tribute to Threads':'TRIBUTE TO THREADS AUTOGRAPH RELICS',
        'Tribute Tandem Autographs':'TRIBUTE TANDEM DUAL AUTOGRAPHS',
        'Calling the Shots Dual Autographs':'CALLING THE SHOT DUAL AUTOGRAPHS',
        'Prime Patch Autograph Relics':'PRIME PATCH AUTOGRAPH RELICS',
        'Triple Relics':'TRIBUTE TRIPLE RELICS',
        'Jumbo Relic':'TRIBUTE JUMBO RELIC',
        'Milestone Relics Jumbo Black Autograph Variation':'MILESTONE RELICS JUMBO BLACK AUTOGRAPH',
    }
    aliases.update({f.title():f for f in FAMILIES})
    for odd in odds:
        matches=[k for k in aliases if odd['name'].casefold()==k.casefold() or odd['name'].casefold().startswith(k.casefold()+' ')]
        if not matches:
            assert odd['name'].startswith('2026 Tribute Career Achievement Award Continuity'),odd['name']
            continue
        odd['family']=aliases[max(matches,key=len)]
    proof=json.loads(PROOF.read_text());proof_hash=hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence=dict(source=proof['source'],evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=proof_hash)
    note=('All 786 printed subject rows across 22 sections retain their physical Name, Team and Rookie cells, including all '
          '100 base numbers, repeated multi-subject card numbers, 15 blank broadcaster teams, literal Cleveland team cells and '
          'mixed-case TTR-Jd. Published team assignments, accents and marks are retained without correction. Rookie flags are '
          'literal source values and are not propagated between cards or subjects. All 143 categories retain literal Hobby ratios; '
          'the odds sheet does not name a ratio unit, so no per-pack probability is inferred. The July 27 official guide explicitly '
          'announces July 29 release and base Blue /150 / Black 1/1. Those limits are not applied to other families or colors. '
          'The three odds-only 2026 Tribute Career Achievement Award Continuity categories remain unjoined: they do not '
          'explicitly identify the insert or the separate Auto roster. Box contents remain separate from ratios; exhaustive parallel numbering is not confirmed.')
    data.update(headers=['Checklist section','Card number','Name','Team','Rookie','Source page'],rows=rows,
                originalSubjectHeaders=['Checklist section','Card number','Name','Team','Rookie','Source page'],
                originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,
                importKind='topps-grid-pdf',dedicatedParser=PARSER,sectionColumn=0,odds=odds,formats=formats,
                oddsRawPages=odds_raw,oddsSha256=odds_hash,oddsIssues=[],oddsParser='scripts/official_odds_layout.py',
                formatNamesPublished=True,oddsUnitsPublished=False,
                publishedSpecifications=[dict(name='Manufacturer Hobby box contents',worksheet='Official guide; box contents are not category odds',
                  headers=['Published field','Published value'],rows=proof['boxContents'],**evidence)],
                sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(rowCount=786,sections=22,importKind=data['importKind'],dedicatedParser=PARSER,sha256=digest,
                  odds=143,formats=1,oddsParser=data['oddsParser'],oddsImportIssues=0,verified=proof['observed'],
                  releaseStatus='Released',releaseDate=proof['releaseDate'],releaseDateSource=proof['source'],
                  releaseDateEvidence=dict(file=evidence['evidenceFile'],sha256=proof_hash),catalogEvidence=note,dataAudit=note)
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text())
    inventory=[record if r['slug']==SLUG else r for r in inventory]
    if not any(r['slug']==SLUG for r in inventory):inventory.append(record)
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text())
    registry['sets'][SLUG]=[dict(s,qualification='Base cards only; no matching color limit is inferred for any insert, autograph or relic family.',**evidence) for s in proof['numbering']]
    family='Career Achievement odds family reconciliation'
    registry['conflicts']=[c for c in registry['conflicts'] if not(c['slug']==SLUG and c['family']==family)]
    registry['conflicts'].append(dict(slug=SLUG,family=family,gap=proof['remainingGaps'][0],sources=[record['checklistUrl'],record['oddsUrl']]))
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Tribute:',len(rows),'subject rows;',sum(r[4]=='Rookie' for r in rows),'Rookie marks;',sum(not r[3] for r in rows),'blank teams; 143 literal odds categories.')

if __name__=='__main__':build()
