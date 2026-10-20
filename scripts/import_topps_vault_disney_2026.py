"""Reconcile Vault Disney by original PDF text-object row and column origins."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from import_official_catalog import run
from import_topps_tribute_2026 import acquire

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-vault-disney'
PARSER='scripts/import_topps_vault_disney_2026.py'
PROOF=ROOT/'data/parallel-audit-sources/vault-disney-2026-20261015.json'
REVISION=ROOT/'data/parallel-audit-sources/vault-disney-2026-revision-20261020.json'
FAMILIES={
 'DISNEY DIAMONDS':100,'TRUE GREATNESS':20,'VAULT RELICS':13,'INK 23':26,
 'CHARACTER CALLIGRAPHY':22,'LEAVING A LEGACY':15,'LACED IN GOLD':13,'DISNEY DUALS':38,
 'DISNEY TRIPLES':33,'MAGIC MONTAGE':6,'RETRO BLOCKBUSTER BOOKLET AUTOGRAPHS':19,
 'IMMORTAL AUTOGRAPHS':7,'VAULT CUT SIGNATURES':1,'DISNEY DIAMONDS AUTOGRAPH VARIATION':51,
 'TRUE GREATNESS AUTOGRAPH VARIATION':10,'VAULT AUTOGRAPH RELICS':5,
 'VAULT AUTOGRAPH RELIC DUALS':4,'VAULT AUTOGRAPH RELIC TRIPLES':3,'GEMS OF WONDER':23,
 'PREMIERE SKETCH CARDS':55,'VAULT ORIGINALS':20,'OVERSIZED PREMIERE SKETCH CARDS':27}
HEADERS=['Checklist section','Card number','Player / subjects','Source page',
 'Official text column 1','Official text column 2','Actor','Character','Relic / prop','Artist']

def read_cards(path):
    rows=[];notes=[];family=None
    pdf=pdfplumber.open(path);assert len(pdf.pages)==11
    for pn,page in enumerate(pdf.pages,1):
        groups=collections.defaultdict(list)
        for char in page.chars:groups[round(char['matrix'][5],2)].append(char)
        for y,chars in sorted(groups.items(),reverse=True):
            # Source glyph draw order, rather than x-sort, keeps overlapping
            # text objects intact. Each column starts at its printed origin.
            chunks=[];current=[];origin=None
            for char in chars:
                start=next((x for x in (53.04,132.62,269.45) if abs(char['x0']-x)<.02),None)
                if start is not None and (not current or start!=origin):
                    if current:chunks.append((origin,' '.join(''.join(c['text'] for c in current).split())))
                    current=[];origin=start
                current.append(char)
            if current:chunks.append((origin,' '.join(''.join(c['text'] for c in current).split())))
            line=' '.join(''.join(c['text'] for c in chars).split())
            if pn==1 and y>730:notes.append([str(pn),line]);continue
            if line in FAMILIES:family=line;continue
            if line in {'RELIC','AUTOGRAPH','AUTOGRAPH RELIC','SKETCH','BOXTOPPER'}:continue
            assert family,(pn,y,chunks)
            # Original text objects retain Barnes's clipped final glyph separately
            # from the adjacent Prince Eric cell. X-sorted words merge these cells.
            cells=dict(chunks)
            actor=character=relic=artist=''
            if family in {'PREMIERE SKETCH CARDS','OVERSIZED PREMIERE SKETCH CARDS'}:
                assert abs(chars[0]['x0']-53)<1;number='';first=line;second='';artist=first
            else:
                assert len({x for x,_ in chunks})==len(chunks),(pn,y,chunks)
                assert set(cells)<={53.04,132.62,269.45},(pn,y,chunks)
                number=cells[53.04];first=cells.get(132.62,'');second=cells.get(269.45,'')
                assert re.fullmatch(r'[A-Z0-9]+-[A-Z0-9]+',number) and first,(pn,chunks)
                if family in {'DISNEY DIAMONDS','TRUE GREATNESS'}:character=first;assert not second
                elif family=='VAULT RELICS':character,relic=first,second
                elif family=='VAULT ORIGINALS':character,artist=first,second
                else:actor,character=first,second
            subject=actor or character or artist
            rows.append([family,number,subject,str(pn),first,second,actor,character,relic,artist])
    assert collections.Counter(r[0] for r in rows)==FAMILIES
    assert len(rows)==511 and sum(bool(r[1]) for r in rows)==429
    pdf.close()
    return rows,notes

def read_odds(path):
    """Retain every physical grid cell, including the manufacturer's 1:XX values."""
    result=[];raw=[];formats=['PACK#1','PACK#2','BOX TOPPER']
    aliases={'OVER-SIZED PREMIERE SKETCHES':'OVERSIZED PREMIERE SKETCH CARDS','PREMIERE SKETCHES':'PREMIERE SKETCH CARDS',
      'DISNEY DIAMONDS AUTOGRAPH EDITION':'DISNEY DIAMONDS AUTOGRAPH VARIATION','TRUE GREATNESS AUTOGRAPH EDITION':'TRUE GREATNESS AUTOGRAPH VARIATION',
      'INK-23':'INK 23','RETRO BLOCKBUSTER BOOKLET AUTOGRAPH':'RETRO BLOCKBUSTER BOOKLET AUTOGRAPHS','VAULT AUTOGRAPH RELIC':'VAULT AUTOGRAPH RELICS'}
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==2
        for pn,page in enumerate(pdf.pages,1):
            tables=page.find_tables();assert len(tables)==1
            cells=tables[0].extract();assert cells[0]==['Card',*formats]
            raw.append(dict(page=pn,text=page.extract_text()))
            for row in cells[1:]:
                assert len(row)==4 and row[0]
                name=row[0];base=re.sub(r' (?:ROSE GOLD|BLACK|RED|GOLD|BRONZE|SUPERFRACTOR) PARALLEL$','',name)
                family=aliases.get(base,base);assert family in FAMILIES,(name,family)
                assert all(v=='-' or re.fullmatch(r'1:(?:[\d,]+|XX)',v) for v in row[1:])
                result.append(dict(name=name,values={k:None if v=='-' else v for k,v in zip(formats,row[1:])},page=pn,family=family,familyBase=base==name))
    assert len(result)==76 and sum(v=='1:XX' for o in result for v in o['values'].values())==2
    return result,formats,raw

def build():
    proof=json.loads(PROOF.read_text());proof_hash=hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence=dict(source=proof['source'],evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=proof_hash)
    revision=json.loads(REVISION.read_text());current=revision['current']
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
    previous=path.with_name(SLUG+'-pre-20261020.pdf')
    assert acquire(revision['previous']['url'],previous)==revision['previous']['sha256']
    digest=acquire(current['url'],path);assert digest==current['sha256'];rows,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');odds_hash=acquire(revision['odds']['url'],op)
    assert odds_hash==revision['odds']['sha256'];odds,formats,odds_raw=read_odds(op)
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text())
    record=next((r for r in catalog['sets'] if r['slug']==SLUG),None)
    if record is None:
        record=dict(title='2026 Topps Vault Disney',manufacturer='Topps / Bowman',sport='disney',year='2026',
          slug=SLUG,page='sets/'+SLUG+'.html',sourcePage=proof['productSource'],checklistUrl=proof['checklistUrl'],
          releaseStatus='Upcoming',releaseDate=None,verified=proof['observed'])
        record=run(record);assert record.get('tableData');catalog['sets'].append(record)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    note=('All 429 numbered subject rows / 384 family-card identities and 82 unnumbered artist entries across 22 sections '
      'are reconciled to original PDF text-object cells. Original unlabelled text columns remain separate from the adapter Actor, '
      'Character, Relic / prop and Artist fields. Repeated dual/triple signers, Christopher Daniel Barnes, printed Pocanhontas '
      'and Ian Mckellen, and both sketch rosters are retained. The revised source adds IA-TZ Tom Holland / Ian Lightfoot. '
      'The October 21 release is upcoming. All 76 odds categories retain PACK#1, PACK#2 and BOX TOPPER columns, null dashes and '
      'two literal 1:XX placeholders. The sheet does not name a ratio unit; no per-pack calculation is made. One explicitly named Immortal Autographs SuperFractor '
      'limit is retained; unnamed card-specific guide examples and sketch artwork uniqueness do not number the other parallels '
      'or artist roster entries. Exhaustive parallel and numbering coverage remains unverified.')
    data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,
      source=current['url'],sha256=digest,importKind='pdf',dedicatedParser=PARSER,sectionColumn=0,sourceDocumentNotes=notes,
      unclassifiedLines=[],coverageComplete=True,odds=odds,formats=formats,formatNamesPublished=True,oddsUnitsPublished=False,
      oddsSource=revision['odds']['url'],oddsSha256=odds_hash,oddsRawPages=odds_raw,oddsIssues=[],oddsParser=PARSER,
      sourceRevision=dict(previous=revision['previous'],current=current,evidenceFile=str(REVISION.relative_to(ROOT)),evidenceSha256=hashlib.sha256(REVISION.read_bytes()).hexdigest()),
      publishedSpecifications=[
        dict(name='Manufacturer Hobby box contents',worksheet='Official guide; box contents are not pack odds',
             headers=['Published field','Published value'],rows=[['Cards per Hobby Box','2']],**evidence),
        dict(name='Card-specific guide examples',worksheet='Official guide examples; unnamed parallels, not family-wide limits',
             headers=['Checklist section','Card number','Actor / character','Published example','Qualification'],
             rows=proof['cardExamples'],**evidence),
        dict(name='Sketch artwork and box toppers',worksheet='Artwork uniqueness is not serial numbering for artist rosters',
             headers=['Published program','Published description','Qualification'],rows=proof['artwork'],**evidence)],
      sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in revision['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(status='Source table',rowCount=len(rows),sections=22,importKind='pdf',dedicatedParser=PARSER,
      checklistUrl=current['url'],sha256=digest,coverageComplete=True,verified=revision['observed'],catalogEvidence=note,dataAudit=note,odds=76,formats=3,oddsUrl=revision['odds']['url'],oddsImportIssues=0,
      sourceObservation=dict(file=evidence['evidenceFile'],sha256=proof_hash,source=proof['productSource']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text())
    inventory=[record if r['slug']==SLUG else r for r in inventory]
    if not any(r['slug']==SLUG for r in inventory):inventory.append(record)
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/entertainment-topps-catalog.json';inventory=json.loads(ip.read_text())
    inventory=[r for r in inventory if r['title']!=record['title']]
    inventory.append(dict(title=record['title'],url=current['url'],source='https://www.topps.com/pages/checklists',observed=revision['observed']))
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text())
    registry['sets'][SLUG]=[dict(family='IMMORTAL AUTOGRAPHS',name='SuperFractor',numbering='1/1',oddsName='IMMORTAL AUTOGRAPHS SUPERFRACTOR PARALLEL',
      qualification='Immortal Autographs only; no other family, unnamed example, or artist roster is assigned this limit.',**evidence)]
    registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]
    registry['conflicts'].append(dict(slug=SLUG,family='Unresolved odds placeholders and incomplete named-parallel inventory',
      gap=' '.join(revision['remainingGaps']),source='https://www.topps.com/pages/odds',evidenceFile=str(REVISION.relative_to(ROOT)),evidenceSha256=hashlib.sha256(REVISION.read_bytes()).hexdigest()))
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Vault Disney: 429 numbered subject rows / 384 identities, 82 artist entries, 22 sections and 76 literal three-column odds rows.')

if __name__=='__main__':build()
