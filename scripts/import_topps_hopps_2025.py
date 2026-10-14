"""Retain Hopps subject cells and its separately paginated rookie column."""
import hashlib
import json
import re
import subprocess
from pathlib import Path
import pdfplumber
from official_odds_layout import physical_odds_pdf

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2025-26-topps-hopps-basketball'
PARSER='scripts/import_topps_hopps_2025.py'
BASE_FAMILIES=['BASE CARDS I','BASE CARDS II','BASE CARDS III','HIGHLIGHTS','ALL STARS']

def lines(page):
    groups=[]
    for c in page.chars:
        group=next((cs for y,cs in groups if abs(c['top']-y)<1),None)
        if group is None:
            group=[]
            groups.append((c['top'],group))
        group.append(c)
    return sorted(groups)

def read_cards(path):
    rows=[]
    section=None
    used_flags=0
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==45
        raw=[{'page':pn,'text':p.extract_text()} for pn,p in enumerate(pdf.pages,1)]
        for pn,page in enumerate(pdf.pages[:23],1):
            # The PDF provides 22 rookie continuation pages for the first
            # 22 name pages. No continuation for name page 23 is published.
            flags=lines(pdf.pages[pn+22]) if pn<=22 else []
            assert all(''.join(c['text'] for c in cs)=='Rookie' for y,cs in flags)
            consumed=set()
            for y,chars in lines(page):
                text=''.join(c['text'] for c in chars).strip()
                if pn==1 and y<150:
                    continue
                if all('Bold' in c['fontname'] for c in chars):
                    if text not in ['BASE','INSERT','AUTOGRAPH']:
                        section=text
                    continue
                starts=[]
                for column,x in enumerate([90.38,316.97]):
                    indices=[i for i,c in enumerate(chars) if abs(c['x0']-x)<.03]
                    if indices:
                        starts.append((max(indices),column))
                assert starts and starts[0][1]==0,(pn,y,text)
                number=''.join(c['text'] for c in chars[:starts[0][0]]).strip()
                assert re.fullmatch(r'\d+|[A-Za-z0-9]+-[A-Za-z0-9]+',number),(pn,y,number)
                cells=['','']
                for i,(start,column) in enumerate(starts):
                    end=starts[i+1][0] if i+1<len(starts) else len(chars)
                    cells[column]=''.join(c['text'] for c in chars[start:end]).strip()
                assert section and cells[0]
                matches=[i for i,(fy,cs) in enumerate(flags) if abs(fy-y)<.1]
                assert len(matches)<=1
                if matches:
                    assert matches[0] not in consumed
                    consumed.add(matches[0])
                rows.append([section,number,cells[0],cells[1],'Rookie' if matches else '',str(pn),str(pn+23) if pn<=22 else ''])
            assert len(consumed)==len(flags),(pn,'Rookie source row has no corresponding subject')
            used_flags+=len(consumed)
    assert len(rows)==1091 and used_flags==384
    assert [int(r[1]) for r in rows if r[0] in BASE_FAMILIES]==list(range(1,301))
    return rows,raw

def acquire(url,path):
    subprocess.run(['curl','-sLf','--retry','2','--max-time','30',url,'-o',str(path)],check=True)
    path.with_suffix('.pdf.url').write_text(url)
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    cp=ROOT/'data/set-catalog.json'
    catalog=json.loads(cp.read_text())
    record=next(r for r in catalog['sets'] if r['slug']==SLUG)
    dp=ROOT/record['tableData']
    data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
    fingerprint=acquire(data['source'],path)
    rows,raw=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf')
    odds_hash=acquire(data['oddsSource'],op)
    odds,formats,odds_raw,issues=physical_odds_pdf(op)
    assert not issues and len(odds)==193 and len(formats)==5
    key=lambda value: re.sub(r'[^A-Z0-9]','',value.upper())
    families={r[0] for r in rows}
    for odd in odds:
        if odd['name']=='Base' or odd['name'].startswith('Base '):
            odd.update(family='BASE CARDS I',familyAliases=BASE_FAMILIES[1:],familyBase=odd['name']=='Base')
            continue
        name=odd['name'].replace('Hoops Rookies First Signs','Hoops Rookie First Signs').replace('Hoops Rookies Duals','Hoops Rookie Duals')
        candidates=[family for family in families if key(name).startswith(key(family))]
        if candidates:
            family=max(candidates,key=lambda f:len(key(f)))
            odd.update(family=family,familyBase=key(name)==key(family))
    note=('All 1,091 printed subject rows, 300 base numbers, separate Name/Team cells and 384 literal Rookie flags are reconciled to original glyph origins and matching continuation-page baselines. '
          'Four fused number/name rows omitted by generic text parsing are restored. Source spelling, overlapping codes and repeated dual/triple signer rows remain literal. '
          'Name pages 1–22 correspond to rookie pages 24–45; the PDF publishes no separate rookie continuation for name page 23. Unpublished flags remain blank, not inferred false. '
          'All 193 odds categories and five literal format columns are preserved. The outer BASE heading includes the three BASE CARDS sections, HIGHLIGHTS and ALL STARS; their shared published Base odds are retained. '
          'The official catalog title says Hopps, while the document filename and autograph headings say Hoops; both original labels remain unchanged. Exhaustive parallel-numbering coverage and a release date remain unverified.')
    data.update(headers=['Checklist section','Card number','Name','Team','Rookie','Source page','Rookie source page'],
                rows=rows,rawPages=raw,unclassifiedLines=[],sha256=fingerprint,sectionColumn=0,
                importKind='topps-grid-pdf',dedicatedParser=PARSER,coverageComplete=True,
                odds=odds,formats=formats,oddsRawPages=odds_raw,oddsSha256=odds_hash,oddsIssues=[],
                oddsParser='scripts/official_odds_layout.py',sourceSheets=[{'name':'Official source reconciliation','notes':[['Source scope',note]]}])
    dp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
    record.update(rowCount=len(rows),sections=len(families),sha256=fingerprint,importKind=data['importKind'],
                  dedicatedParser=PARSER,coverageComplete=True,odds=len(odds),formats=len(formats),
                  oddsParser=data['oddsParser'],oddsImportIssues=0,catalogEvidence=note,dataAudit=note)
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json'
    inventory=json.loads(ip.read_text())
    ip.write_text(json.dumps([record if r['slug']==SLUG else r for r in inventory],ensure_ascii=False,indent=2)+'\n')
    print(record['title'],len(rows),'subject rows; 300 base numbers; 384 rookie flags; 193 odds categories')

if __name__=='__main__':
    build()
