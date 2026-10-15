"""Reconcile Marvel Comics Sapphire's physical subjects and exact base-family odds."""
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire, text
from official_odds_layout import physical_odds_pdf

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-chrome-marvel-comics-sapphire-edition'
PARSER='scripts/import_topps_marvel_sapphire_2026.py'
PROOF=ROOT/'data/parallel-audit-sources/marvel-sapphire-2026-product-20261015.json'
HEADERS=['Checklist section','Card number','Name','Source page']
FAMILIES={'CHARACTERS I','CHARACTERS II','HIDDEN GEMS','INFINITE','MARVEL FACSIMILE AUTOGRAPHS',
          'MARVEL FACSIMILE DUAL AUTOGRAPHS','MARVEL FACSIMILE TRIPLE AUTOGRAPHS','MARVEL FACSIMILE QUAD AUTOGRAPHS'}

def read_cards(path):
    rows,raw,notes=[],[],[];family=None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==8
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text()))
            groups=[]
            for c in page.chars:
                y=c['matrix'][5];cs=next((cs for baseline,cs in groups if abs(y-baseline)<.6),None)
                if cs is None:cs=[];groups.append((y,cs))
                cs.append(c)
            for y,cs in sorted(groups,reverse=True):
                line=text(cs)
                if not line:continue
                if line.startswith(('Checklists provided','production,')):
                    notes.append([str(pn),line]);continue
                if line in {'BASE','INSERT'}:continue
                if line in FAMILIES:family=line;continue
                # The 101/Angela row is indented; 104–108 names start farther left.
                # Original draw order within the physical baseline retains both fields.
                match=re.fullmatch(r'(\d+|[A-Z]+-[A-Z0-9]+)\s+(.+)',line)
                assert family and match,(pn,line)
                number,name=match.groups()
                rows.append([family,number,name,str(pn)])
    assert len(rows)==262 and len({tuple(r[:2]) for r in rows})==242
    assert {int(r[1]) for r in rows if r[0] in {'CHARACTERS I','CHARACTERS II'}}==set(range(1,201))
    return rows,raw,notes

def build():
    proof=json.loads(PROOF.read_text());proof_hash=hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence=dict(source=proof['source'],evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=proof_hash)
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(r for r in catalog['sets'] if r['slug']==SLUG)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(proof['checklistUrl'],path)
    rows,raw,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');odds_hash=acquire(proof['oddsUrl'],op)
    odds,formats,odds_raw,issues=physical_odds_pdf(op)
    assert len(odds)==23 and formats==['Sapphire'] and not issues
    for odd in odds:
        if odd['name'].startswith('Base - Characters '):
            odd.update(family='CHARACTERS I',familyAliases=['CHARACTERS II'])
        else:
            matches=[f for f in FAMILIES if odd['name'].upper()==f or odd['name'].upper().startswith(f+' ')]
            assert matches,odd['name'];odd['family']=max(matches,key=len)
    note=('All 262 printed subject rows / 242 family-card identities across eight sections are reconciled against physical PDF columns. '
          'The 200 base numbers retain Characters I and Characters II; both sections share the eight published Base - Characters odds. '
          'Seventeen parenthetical DEBUT annotations remain literal Name text, not rookie flags. Repeated facsimile signatures retain '
          'every printed subject and number. All 23 Sapphire ratios are literal; the named format publishes no ratio unit. '
          'Named serial-number limits and an exact calendar release date remain unverified; regular Chrome limits are not applied.')
    data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,
                sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,importKind='pdf',dedicatedParser=PARSER,
                sectionColumn=0,odds=odds,formats=formats,oddsSource=proof['oddsUrl'],oddsRawPages=odds_raw,
                oddsSha256=odds_hash,oddsIssues=[],oddsParser='scripts/official_odds_layout.py',
                formatNamesPublished=True,oddsUnitsPublished=False,
                sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(rowCount=262,sections=8,importKind='pdf',dedicatedParser=PARSER,sha256=digest,odds=23,formats=1,
                  oddsParser=data['oddsParser'],oddsImportIssues=0,verified=proof['observed'],dataAudit=note,
                  sourceObservation=dict(file=evidence['evidenceFile'],sha256=proof_hash,source=proof['source']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text())
    ip.write_text(json.dumps([record if r['slug']==SLUG else r for r in inventory],ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());family='Unverified Sapphire numbering and calendar release date'
    registry['conflicts']=[c for c in registry['conflicts'] if not(c['slug']==SLUG and c['family']==family)]
    registry['conflicts'].append(dict(slug=SLUG,family=family,gap=' '.join(proof['remainingGaps']),**evidence))
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Marvel Comics Sapphire: 262 subject rows / 242 identities, both 100-card base sections, 23 literal ratios. Numbering and release-date audits remain incomplete.')

if __name__=='__main__':build()
