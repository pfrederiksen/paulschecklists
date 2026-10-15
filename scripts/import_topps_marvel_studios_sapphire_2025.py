"""Reconcile tagged physical cells in the 2025 MCU Sapphire checklist sold in 2026."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
from official_odds_layout import physical_odds_pdf

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2025-topps-marvel-studios-chrome-sapphire'
PARSER='scripts/import_topps_marvel_studios_sapphire_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/marvel-studios-sapphire-2025-20261015.json'
HEADERS=['Checklist section','Card number','Player / subjects','Source page','Name','Secondary Name','Subject','Property','Phase','Debut','First Name','Last Name','Character Name','Artist Name']
FAMILIES={'BASE','SAPPHIRE SELECTIONS','SKETCH CARDS','SINGLE AUTOGRAPHS','DUAL AUTOGRAPHS','TRIO AUTOGRAPHS'}

def read_cards(path):
    rows=[];raw=[];notes=[];family=None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==8
        for pn,page in enumerate(pdf.pages,1):
            raw.append(dict(page=pn,text=page.extract_text()))
            groups=collections.defaultdict(list)
            for c in page.chars:
                assert c['mcid'] is not None,(pn,c)
                groups[c['mcid']].append(c)
            current=None
            def flush():
                if current is None:return
                if family=='BASE':
                    number,name,secondary,prop,phase,debut=current
                    row=[family,number,name,str(pn),name,secondary,'',prop,phase,debut,'','','','']
                elif family=='SAPPHIRE SELECTIONS':
                    number,subject,prop=current
                    row=[family,number,subject,str(pn),'','',subject,prop,'','','','','','']
                else:
                    number,first,last,character,prop,debut=current
                    row=[family,number,' '.join(x for x in [first,last] if x),str(pn),'','','',prop,'',debut,first,last,character,'']
                assert re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and row[2],row
                assert row[9] in {'','DEBUT'},row
                rows.append(row)
            for mid,cs in groups.items():
                value=text(cs);x=cs[0]['x0']
                if any('Bold' in c['fontname'] for c in cs):
                    if value in FAMILIES:
                        flush();current=None;family=value
                    else:notes.append([str(pn),value])
                    continue
                assert family,(pn,mid,value)
                if family=='SKETCH CARDS':
                    assert current is None
                    rows.append([family,'',value,str(pn),'','','','','','','','','',value]);continue
                origins=[55.8,90.504,169.46,248.45,349.63,418.39] if family=='BASE' else [56.4,119.42,328.99] if family=='SAPPHIRE SELECTIONS' else [56.04,102.38,155.78,220.97,331.39,489.58]
                column=min(range(len(origins)),key=lambda i:abs(x-origins[i]))
                assert abs(x-origins[column])<.05,(pn,mid,value,x,origins)
                if column==0:
                    flush();current=['']*len(origins)
                assert current is not None and not current[column],(pn,mid,value)
                # Each tagged MCID is one original cell. Its full glyphs stay
                # together even when they cross the next cell's physical x.
                current[column]=value
            flush()
    assert len(rows)==452 and sum(bool(r[1]) for r in rows)==334
    assert {int(r[1]) for r in rows if r[0]=='BASE'}==set(range(1,201))
    assert len({r[0] for r in rows})==6
    return rows,raw,notes

def build():
    proof=json.loads(PROOF.read_text());ph=hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence=dict(source=proof['productSource'],evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(record['checklistUrl'],path)
    rows,raw,notes=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');oh=acquire(record['oddsUrl'],op)
    odds,formats,odds_raw,issues=physical_odds_pdf(op)
    assert len(odds)==28 and formats==['Sapphire Pack Rate'] and not issues
    for odd in odds:
        prefix=next(p for p in ['Base Set','Single Autos','Dual Autos','Trio Autos','Sapphire Selections','Sketch Card'] if odd['name'].startswith(p+' ') or odd['name']==p)
        odd['family']={'Base Set':'BASE','Single Autos':'SINGLE AUTOGRAPHS','Dual Autos':'DUAL AUTOGRAPHS','Trio Autos':'TRIO AUTOGRAPHS','Sapphire Selections':'SAPPHIRE SELECTIONS','Sketch Card':'SKETCH CARDS'}[prefix]
    note=('All 334 numbered subject rows plus 118 unnumbered sketch artists across six sections are reconciled to tagged physical PDF cells. '
          'The 200-card Base retains separate Name, Secondary Name, Property, Phase and Debut columns; actor first/last names and Character Name remain separate on autographs. '
          'All repeated dual and trio signers, overlapping Shang-Chi property glyphs, clipped Doctor Strange property text, apparent source spellings and literal DEBUT marks are retained. '
          'All 28 odds categories preserve the complete Sapphire Pack Rate header and literal ratios. The product page mentions a 1/1 Padparadscha parallel without an exact family scope; '
          'that statement stays qualified, not propagated to every Padpradascha family. Other serial limits and the exact calendar release date remain unverified; product year 2025 is separate from the 2026 catalog listing.')
    data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,
      sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,importKind='pdf',dedicatedParser=PARSER,
      coverageComplete=True,sectionColumn=0,odds=odds,formats=formats,oddsSource=record['oddsUrl'],oddsSha256=oh,
      oddsRawPages=odds_raw,oddsIssues=[],oddsParser='scripts/official_odds_layout.py',formatNamesPublished=True,oddsUnitsPublished=True,
      publishedSpecifications=[dict(name='Manufacturer product specifications',worksheet='Official U.S. product page; no exact family join is asserted',headers=['Published field','Published value','Scope / qualification'],
        rows=[['Base checklist','200 cards','Matches the 200 printed base numbers.'],['Padparadscha parallel','1/1','Product-level statement; no exact family is specified. Not applied to Base, Single, Dual, Trio or Selections categories.'],['Hand-illustrated sketches','One-of-kind','Artwork uniqueness, not a serial-number limit on artist roster entries.']],**evidence),
        dict(name='Japan product configuration',worksheet='Official Japan product; regional fields and box contents are separate from pack odds and calendar release date',headers=['Published field','Published value'],rows=proof['regionalFields'],source=proof['regionalSource'],evidenceFile=evidence['evidenceFile'],evidenceSha256=ph)],
      sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(sourcePage=proof['productSource'],rowCount=len(rows),sections=6,dedicatedParser=PARSER,sha256=digest,
      odds=28,formats=1,oddsParser=data['oddsParser'],oddsImportIssues=0,coverageComplete=True,verified=proof['observed'],
      dataAudit=note,catalogEvidence=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=proof['productSource']))
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[r for r in inventory if r['slug']!=SLUG]+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]
    registry['conflicts'].append(dict(slug=SLUG,family='Unresolved Sapphire numbering and release scope',gap=' '.join(proof['remainingGaps']),**evidence))
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Marvel Studios Sapphire:',collections.Counter(r[0] for r in rows),'; DEBUT marks:',sum(r[9]=='DEBUT' for r in rows),'; 28 complete Sapphire Pack Rate categories.')

if __name__=='__main__':build()
