"""Reconcile Museum UCC's physical columns, centered signer codes and literal odds."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from import_official_catalog import run, fetch, CACHE, odds_pdf

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2025-26-topps-museum-uefa-club-competitions'
PARSER = 'scripts/import_topps_museum_ucc_2025.py'
URL = 'https://cdn.shopify.com/s/files/1/0739/2015/1805/files/Museum_Checklist_Subject_to_Change.pdf?v=1789660179'
ODDS = 'https://cdn.shopify.com/s/files/1/0739/2015/1805/files/2025-26_Topps_UCC_Museum_Collection_Odds_-_Subject_to_Change.pdf?v=1789660179'
PRODUCT = 'https://www.topps.com/pages/topps-museum-ucc'
PROOF = ROOT / 'data/parallel-audit-sources/museum-ucc-2025-26-20261019.json'
HEADERS = ['Checklist section', 'Card number', 'Name', 'Team', 'Rookie', 'Source page']
MULTI = {'ARCHIVAL DUAL AUTOGRAPHS': 2, 'HAT-TRICK TRIPLE AUTOGRAPHS': 3,
         'SUPREME SCRIPT LEGENDARY AUTOGRAPHED BOOK': 10,
         'SUPREME MATERIALS RELIC BOOK': 10,
         'SUPREME SCRIPT LEGENDARY AUTOGRAPHED RELIC BOOK': 10}
FAMILIES = {'BASE CARDS': 100, 'MUSEUM ROLL OF HONOR': 5, 'THE GRAIL': 1,
 'ARCHIVAL AUTOGRAPHS': 59, 'MUSEUM ROOKIE AUTOGRAPHS': 12, 'SHOWPIECE SIGNATURES': 25,
 'MUSEUM MARBLEIZED AUTOGRAPHS': 36, 'MUSEUM FRAMED AUTOGRAPHS': 26,
 'LEGENDARY INK FRAMED AUTOGRAPHS': 18, 'MARKS OF EXCELLENCE': 9,
 'ARCHIVAL DUAL AUTOGRAPHS': 30, 'HAT-TRICK TRIPLE AUTOGRAPHS': 42,
 'SUPREME SCRIPT LEGENDARY AUTOGRAPHED BOOK': 10,
 'MEANINGFUL MATERIAL SINGLE RELICS': 34, 'MUSEUM ROOKIE RELICS': 11,
 'MOMENTOUS MATERIAL JUMBO RELICS': 16, 'CURATED COLLARS RELICS': 12,
 'MUSEUM NAMEPLATE RELICS': 12, 'UEFA FOUNDATION PATCH CARDS': 10, 'LEGACY BOOT RELICS': 32,
 'SINGLE PLAYER SWATCHES DUAL RELICS': 14, 'HOME/AWAY DUAL RELICS': 5,
 'SINGLE PLAYER TRIPLE RELICS': 14, 'SUPREME MATERIALS RELIC BOOK': 10,
 'MUSEUM AUTOGRAPH RELICS': 71, 'MUSEUM ROOKIE AUTOGRAPH RELICS': 7,
 'MOMENTOUS MATERIAL JUMBO AUTOGRAPHS': 33, 'CURATED COLLARS AUTOGRAPH RELICS': 18,
 'LEGACY LACES AUTOGRAPH RELICS': 29, 'MUSEUM FRAMED AUTOGRAPH PATCH CARDS': 14,
 'SINGLE PLAYER SIGNATURE SWATCHES DUAL RELIC AUTOGRAPHS': 18,
 'HOME/AWAY DUAL RELIC AUTOGRAPHS': 4, 'HAT-TRICK AUTOGRAPH RELICS': 7,
 'KIT CONSTRUCTION TRIPLE RELIC AUTOGRAPH BOOK': 2,
 'SUPREME SCRIPT LEGENDARY AUTOGRAPHED RELIC BOOK': 10}
ALIASES = dict(zip(FAMILIES, [
 'Base Card', 'Museum Roll of Honor', 'The Grail', 'Archival Autograph',
 'Museum Rookie Autograph', 'Showpiece Signatures', 'Museum Marbleized Autograph',
 'Museum Framed Autograph', 'Legendary Ink Framed Autograph', 'Marks of Excellence',
 'Archival Dual Autographs', 'Hat-Trick Triple Autographs', 'Supreme Script Legendary Autographed Book',
 'Meaningful Material Single Relic', 'Museum Rookie Relic', 'Momentous Material Jumbo Relic',
 'Curated Collars Relic', 'Museum Nameplate Relic', 'UEFA Foundation Patch Card', 'Legacy Boot Relic',
 'Single Player Swatches Dual Relics', 'Home/Away Dual Relics', 'Single Player Triple Relics',
 'Supreme Materials Relic Book', 'Museum Autograph Relic', 'Museum Rookie Autograph Relic',
 'Momentous Material Jumbo Autograph', 'Curated Collars Autograph Relic', 'Legacy Laces Autograph Relic',
 'Museum Framed Autograph Patch Card', 'Single Player Signature Swatches Dual Relics Autograph',
 'Home/Away Dual Relics Autograph', 'Hat-Trick Autograph Relic',
 'Kit Construction Triple Relics Autographed Book', 'Supreme Script Legendary Autographed Relic Book']))


def read_cards(path):
    subjects = collections.defaultdict(list)
    anchors = collections.defaultdict(list)
    normal = collections.defaultdict(list)
    family, raw, notes = None, [], []
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 17
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text() or ''})
            groups = collections.defaultdict(list)
            for char in page.chars:
                groups[round(char['matrix'][5], 2)].append(char)
            for y, chars in sorted(groups.items(), reverse=True):
                text = ''.join(c['text'] for c in chars).strip()
                if all('Bold' in c['fontname'] for c in chars):
                    if text not in {'BASE', 'INSERT', 'AUTOGRAPH', 'RELIC', 'AUTOGRAPH-RELIC'}:
                        assert text in FAMILIES, (pn, text)
                        family = text
                    continue
                if all('Italic' in c['fontname'] for c in chars):
                    notes.append([family or 'Set-wide', str(pn), text])
                    continue
                starts = [[i for i, c in enumerate(chars) if abs(c['x0']-x) < .02]
                          for x in [53.04, 113.54, 274.97, 415.75]]
                assert all(len(s) <= 1 for s in starts), (pn, text)
                if family in MULTI and starts[0] and not starts[1]:
                    assert re.fullmatch(r'[A-Z]+-[A-Z0-9]+', text), (pn, text)
                    anchors[family].append((text, pn, y))
                    continue
                assert starts[1] and starts[2], (pn, text)
                indices = [s[0] for s in starts if s]
                assert indices == sorted(indices)
                cells = [''.join(c['text'] for c in chars[a:b]).strip()
                         for a, b in zip(indices, indices[1:]+[len(chars)])]
                if starts[0]:
                    assert family not in MULTI and len(cells) in {3, 4}
                    number, name, team = cells[:3]
                    rookie = cells[3] if len(cells) == 4 else ''
                    assert re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+', number)
                    assert rookie in {'', 'Rookie'}
                    normal[family].append([family, number, name, team, rookie, str(pn)])
                else:
                    assert family in MULTI and len(cells) == 2
                    subjects[family].append((cells, pn, y))
    for family, size in MULTI.items():
        codes = []
        for code, pn, y in anchors[family]:
            if codes and code == codes[-1][0]:
                assert (family, code, pn, y) == ('HAT-TRICK TRIPLE AUTOGRAPHS', 'HTA-AGC', 8, 740.64)
                continue
            codes.append((code, pn, y))
        assert len(subjects[family]) == len(codes)*size
        for i, (code, pn, y) in enumerate(codes):
            group = subjects[family][i*size:(i+1)*size]
            # Codes are vertically centered in the original two/three/ten-person cell.
            same_page = [(p, sy) for _, p, sy in group if p == pn]
            assert same_page and min(sy for _, sy in same_page)-1 <= y <= max(sy for _, sy in same_page)+1
            for (name, team), page, _ in group:
                normal[family].append([family, code, name, team, '', str(page)])
    rows = [row for family in FAMILIES for row in normal[family]]
    assert collections.Counter(r[0] for r in rows) == FAMILIES
    assert len(rows) == 756 and len({tuple(r[:2]) for r in rows}) == 686
    assert sum(r[4] == 'Rookie' for r in rows) == 102
    return rows, raw, notes


def build():
    cp = ROOT/'data/set-catalog.json'
    catalog = json.loads(cp.read_text())
    record = next((r for r in catalog['sets'] if r['slug'] == SLUG), None)
    if record is None:
        record = run(dict(title='Topps® Museum UEFA Club Competitions 2025/26',
                          manufacturer='Topps / Bowman', sport='soccer', year='2025-26',
                          slug=SLUG, page='sets/'+SLUG+'.html', sourcePage=PRODUCT,
                          checklistUrl=URL, releaseStatus='Unverified', releaseDate=None,
                          verified='2026-10-19'))
        assert record.get('tableData'), record
        catalog['sets'].append(record)
    blob = fetch(URL, CACHE/(SLUG+'.pdf'))
    ob = fetch(ODDS, CACHE/(SLUG+'-odds.pdf'))
    rows, raw, notes = read_cards(CACHE/(SLUG+'.pdf'))
    original, formats, odds_raw, issues = odds_pdf(CACHE/(SLUG+'-odds.pdf'))
    assert len(original) == 147 and formats == ['Hobby', 'Hat-Trick'] and not issues
    odds = []
    for entry in original:
        family = next((f for f in sorted(ALIASES, key=lambda f:len(ALIASES[f]), reverse=True)
                       if entry['name'] == ALIASES[f] or entry['name'].startswith(ALIASES[f]+' ')), None)
        assert family, entry['name']
        odds.append(dict(entry, family=family, familyBase=entry['name'] == ALIASES[family]))
    proof = json.loads(PROOF.read_text())
    assert hashlib.sha256(blob).hexdigest() == proof['checklistSha256']
    assert hashlib.sha256(ob).hexdigest() == proof['oddsSha256']
    evidence = dict(evidenceFile=str(PROOF.relative_to(ROOT)), evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
    table = lambda name, headers, values: dict(name=name, headers=headers, rows=values,
                 source=proof['guide']['url'], worksheet='Official guide; exact card scope retained', **evidence)
    specs = []
    for family, number, name, parallel, statement, qualification in proof['cardExamples']:
        assert [r[2] for r in rows if r[0] == family and r[1] == number] == [name]
        specs.append(table(family, ['Card number','Name','Parallel / variation','Published statement','Qualification'],
                           [[number,name,parallel,statement,qualification]]))
    specs.append(dict(name='Official configuration scope', headers=['Checklist family','Published statement','Qualification'],
                      rows=[[f,t,'Published configuration restriction; no numeric pack odds or serial limit inferred.']
                            for f,_,t in notes if t.startswith('EXCLUSIVE')], source=URL))
    note = ('All 756 physical subject rows / 686 family-card identities across 35 sections retain original Name, Team and 102 literal Rookie marks. '
            'Fifteen dual and fourteen triple autograph cards and three ten-subject books retain every signer, including the page-seven/eight continuation. '
            'All 147 odds categories retain Hobby / Hat-Trick columns and nulls. The sheet names no ratio unit; Base Card 4:1 remains literal. '
            'Three guide examples stay card-specific; a 25-copy statement does not establish serial marking or an unnamed color. '
            'September 18 UK availability is regional evidence, not a verified general release. Exhaustive parallel eligibility and numbering remain unverified.')
    data = dict(title=record['title'], headers=HEADERS, rows=rows, originalSubjectHeaders=HEADERS,
                originalSubjectRows=rows, rawPages=raw, sourceDocumentNotes=notes, unclassifiedLines=[],
                source=URL, sha256=hashlib.sha256(blob).hexdigest(), importKind='topps-grid-pdf',
                dedicatedParser=PARSER, sectionColumn=0, rookieColumn=4, coverageComplete=True,
                odds=odds, formats=formats, formatNamesPublished=True, oddsUnitsPublished=False,
                officialOddsTable=original, officialOddsFormats=formats, officialOddsHeader=['Card',*formats],
                oddsRawPages=odds_raw, oddsIssues=issues, oddsSource=ODDS, oddsSha256=hashlib.sha256(ob).hexdigest(),
                publishedSpecifications=specs, parallelSpecifications=[],
                sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=PRODUCT),
                sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp = ROOT/'data/imports'/(SLUG+'.json')
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(status='Source table',tableData=str(dp.relative_to(ROOT)),rowCount=len(rows),sections=35,
                  importKind=data['importKind'],dedicatedParser=PARSER,coverageComplete=True,
                  sha256=data['sha256'],odds=147,formats=2,oddsUrl=ODDS,oddsImportIssues=0,
                  catalogEvidence=note,dataAudit=note,sourceObservation=data['sourceObservation'],
                  description='Browse 100 base cards, multi-signer autographs and memorabilia, with original clubs, Rookie marks and two published odds columns. General release and exhaustive parallel numbering remain unverified.',
                  additionalSources=[dict(title='Official collector guide',url=proof['guide']['url']),
                                     dict(title='UK release announcement (regional)',url=proof['regionalRelease']['url'])])
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    for name in ['topps-product-official-catalog.json']:
        ip=ROOT/'data'/name;inventory=json.loads(ip.read_text())
        inventory=[record if r['slug']==SLUG else r for r in inventory]
        if not any(r['slug']==SLUG for r in inventory):inventory.append(record)
        ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-official-catalog.json';inventory=json.loads(ip.read_text())
    if not any(r['url']==URL for r in inventory):inventory.append(dict(id=SLUG,title=record['title'],url=URL))
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-official-odds.json';inventory=json.loads(ip.read_text())
    if not any(r['url']==ODDS for r in inventory):inventory.append(dict(title=record['title'],url=ODDS,sourcePage=PRODUCT,scope='2025/26 Museum UEFA Club Competitions; Hobby and Hat-Trick only',sha256=data['oddsSha256']))
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/parallel-specifications.json';registry=json.loads(ip.read_text());registry['sets'][SLUG]=[]
    registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Remaining numbering and eligibility',gap=' '.join(proof['remainingGaps']),source=proof['guide']['url'],**evidence)]
    ip.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Museum UCC: 756 original subjects / 686 identities / 35 families; 102 Rookie marks; all 147 two-column odds; three isolated guide examples.')


if __name__ == '__main__':
    build()
