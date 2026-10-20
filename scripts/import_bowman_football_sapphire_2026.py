"""Import the original Bowman Football Sapphire number/name/team/Rookie cells."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from import_official_catalog import run
from import_topps_tribute_2026 import acquire

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-bowman-football-sapphire-edition'
PARSER='scripts/import_bowman_football_sapphire_2026.py'
PROOF=ROOT/'data/parallel-audit-sources/bowman-football-sapphire-2026-20261020.json'
HEADERS=['Checklist section','Card number','Name','Team','Rookie','Source page']

def read_cards(path):
    rows=[];notes=[];family=None
    origins=[53.04,133.32,295.56,447.36]
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==13
        for pn,page in enumerate(pdf.pages,1):
            groups=collections.defaultdict(list)
            for c in page.chars:groups[round(c['matrix'][5],2)].append(c)
            for y,chars in sorted(groups.items(),reverse=True):
                line=' '.join(''.join(c['text'] for c in chars).split())
                if pn==1 and y>680:notes.append([str(pn),line]);continue
                if line in {'BASE','INSERT','AUTOGRAPH'}:continue
                if abs(chars[0]['x0']-53.16)<.02:family=line;continue
                assert family,(pn,line)
                # Use drawing order and the printed column starts. Long names
                # can cross the Team column without changing their source cell.
                cells={};column=None
                for c in chars:
                    match=next((i for i,x in reversed(list(enumerate(origins))) if abs(c['x0']-x)<.02),None)
                    if match is not None and (column is None or match>column):column=match
                    assert column is not None,(pn,line)
                    cells.setdefault(column,[]).append(c['text'])
                values=[' '.join(''.join(cells.get(i,[])).split()) for i in range(4)]
                assert re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',values[0]) and values[1] and values[2]
                assert values[3] in {'','Rookie'}
                rows.append([family,*values,str(pn)])
    assert len(rows)==608 and sum(r[4]=='Rookie' for r in rows)==146
    return rows,notes

def build():
    proof=json.loads(PROOF.read_text());url=proof['checklist']['url']
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(url,path)
    assert digest==proof['checklist']['sha256'];rows,notes=read_cards(path)
    assert dict(collections.Counter(r[0] for r in rows))==proof['familyCounts']
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text())
    record=next((r for r in catalog['sets'] if r['slug']==SLUG),None)
    if record is None:
        record=dict(title='2026 Bowman Football Sapphire Edition',manufacturer='Topps / Bowman',sport='football',year='2026',
          slug=SLUG,page='sets/'+SLUG+'.html',sourcePage=proof['source'],checklistUrl=url,releaseStatus='Upcoming',releaseDate=None,verified=proof['observed'])
        record=run(record);assert record.get('tableData');catalog['sets'].append(record)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    note=proof['statement']+' '+' '.join(proof['remainingGaps'])
    data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,source=url,sha256=digest,
      dedicatedParser=PARSER,importKind='topps-grid-pdf',sectionColumn=0,sourceDocumentNotes=notes,unclassifiedLines=[],coverageComplete=True,
      odds=[],formats=[],formatNamesPublished=False,oddsUnitsPublished=False,sourceSheets=[dict(name='Official source reconciliation',notes=[[note]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(status='Source table',rowCount=608,sections=11,checklistUrl=url,importKind='topps-grid-pdf',dedicatedParser=PARSER,
      sha256=digest,coverageComplete=True,verified=proof['observed'],catalogEvidence=note,dataAudit=note,odds=0,formats=0,
      sourceObservation=dict(file=str(PROOF.relative_to(ROOT)),sha256=hashlib.sha256(PROOF.read_bytes()).hexdigest(),source=proof['source']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[r for r in inventory if r['slug']!=SLUG]+[record]
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    print('Imported 608 physical subjects / 11 families / 146 literal Rookie marks. Odds and serial limits remain unavailable.')

if __name__=='__main__':build()
