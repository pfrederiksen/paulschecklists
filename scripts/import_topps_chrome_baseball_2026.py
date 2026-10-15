"""Retain Chrome Baseball subject cells and its separately paginated rookie column."""
import hashlib
import json
import re
import subprocess
from pathlib import Path
import pdfplumber

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-chrome-baseball'
PARSER='scripts/import_topps_chrome_baseball_2026.py'
BASE_FAMILIES=['BASE CARDS']

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
        assert len(pdf.pages)==63
        raw=[{'page':pn,'text':p.extract_text()} for pn,p in enumerate(pdf.pages,1)]
        for pn,page in enumerate(pdf.pages[:32],1):
            # Pages 33–63 are the rookie column for name pages 1–31.
            # No continuation for name page 32 is published.
            flags=lines(pdf.pages[pn+31]) if pn<=31 else []
            flags=[(y,cs) for y,cs in flags if not all('Italic' in c['fontname'] for c in cs)]
            assert all(''.join(c['text'] for c in cs)=='Rookie' for y,cs in flags)
            consumed=set()
            for y,chars in lines(page):
                text=''.join(c['text'] for c in chars).strip()
                if pn==1 and y<120:
                    continue
                if all('Bold' in c['fontname'] for c in chars):
                    if text not in ['BASE','INSERT','AUTOGRAPH','RELIC']:
                        section=text
                    continue
                starts=[]
                for column,x in enumerate([132.62,298.01]):
                    indices=[i for i,c in enumerate(chars) if abs(c['x0']-x)<.03]
                    if indices:
                        starts.append((max(indices),column))
                assert starts,(pn,y,text)
                number=''.join(c['text'] for c in chars[:starts[0][0]]).strip()
                assert re.fullmatch(r'\d+|[A-Za-z0-9]+-[A-Za-z0-9]+',number) or not number and section=='FANATICS AUTHENTICS REDEMPTION CARDS',(pn,y,number)
                cells=['','']
                for i,(start,column) in enumerate(starts):
                    end=starts[i+1][0] if i+1<len(starts) else len(chars)
                    cells[column]=''.join(c['text'] for c in chars[start:end]).strip()
                assert section and (cells[0] or cells[1])
                matches=[i for i,(fy,cs) in enumerate(flags) if abs(fy-y)<.1]
                assert len(matches)<=1
                if matches:
                    assert matches[0] not in consumed
                    consumed.add(matches[0])
                rows.append([section,number,cells[0],cells[1],'Rookie' if matches else '',str(pn),str(pn+32) if pn<=31 else ''])
            assert len(consumed)==len(flags),(pn,'Rookie source row has no corresponding subject')
            used_flags+=len(consumed)
    assert len(rows)==1643 and used_flags==412
    assert sum(not r[1] for r in rows)==30
    assert len({r[0] for r in rows})==55
    assert [int(r[1]) for r in rows if r[0] in BASE_FAMILIES]==list(range(1,301))
    return rows,raw

def acquire(url,path):
    temporary=path.with_suffix('.pdf.part')
    try:
        subprocess.run(['curl','-sLf','--retry','2','--max-time','30',url,'-o',str(temporary)],check=True)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    path.with_suffix('.pdf.url').write_text(url)
    return hashlib.sha256(path.read_bytes()).hexdigest()

def pieces(chars):
    starts=[i for i,c in enumerate(chars) if i==0 or
            abs(c['top']-chars[i-1]['top'])>1 or c['x0']<chars[i-1]['x0'] or
            c['x0']-chars[i-1]['x1']>8]
    result=[]
    for a,b in zip(starts,starts[1:]+[len(chars)]):
        chunk=chars[a:b]
        while chunk and chunk[-1]['text'].isspace():chunk=chunk[:-1]
        if chunk:result.append(chunk)
    return result

def read_odds(path):
    """Original right edges join wrapped headers and every literal source cell."""
    odds,formats,raw,exceptions=[],[],[],[]
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==7
        for pn,page in enumerate(pdf.pages,1):
            raw.append({'page':pn,'text':page.extract_text()})
            tables=page.find_tables();assert len(tables)==1
            table=tables[0]
            def chunks(row):
                return pieces([c for c in page.chars if row.bbox[1]<=(c['top']+c['bottom'])/2<=row.bbox[3]])
            probe=chunks(table.rows[1])
            values=[cs for cs in probe if cs[0]['x0']>200]
            assert len(values)==6
            right_edges=[max(c['x1'] for c in cs) for cs in values]
            assert right_edges==sorted(right_edges)
            def column(cs):
                if abs(cs[0]['x0']-14.2)<.1:return 0
                edge=max(c['x1'] for c in cs)
                index=min(range(6),key=lambda i:abs(edge-right_edges[i]))
                assert abs(edge-right_edges[index])<.1,(pn,edge,right_edges)
                return index+1
            headings=[[] for _ in range(7)]
            for cs in chunks(table.rows[0]):headings[column(cs)].append(''.join(c['text'] for c in cs))
            headings=[' '.join(' '.join(parts).split()) for parts in headings]
            assert headings[0]=='Card' and all(headings[1:])
            if formats:assert headings[1:]==formats
            else:formats=headings[1:]
            for row in table.rows[1:]:
                cells=[[] for _ in range(7)]
                boxes={}
                for cs in chunks(row):
                    col=column(cs);cells[col].append(''.join(c['text'] for c in cs))
                    if col:boxes[col]=[min(c['x0'] for c in cs),min(c['top'] for c in cs),max(c['x1'] for c in cs),max(c['bottom'] for c in cs)]
                cells=[' '.join(' '.join(parts).split()) for parts in cells]
                name=cells[0];assert name and all(cells[1:]),(pn,cells)
                item={'name':name,'values':dict(zip(formats,[None if v=='-' else v for v in cells[1:]])),'page':pn}
                for col,value in enumerate(cells[1:],1):
                    if value!='-' and not re.fullmatch(r'[\d,.]+(?::[\d,.]+)+',value):
                        assert pn==6 and name=='2025 WORLD SERIES CHAMPIONS AUTOGRAPHS GOLD REFRACTOR' and col==5 and value=='0.39374999999999999'
                        qualification=('Official PDF prints 0.39374999999999999 in the Breaker Delight cell without a ratio separator. '
                                       'Retained literally; its unit and probability are not inferred.')
                        item['qualification']=qualification
                        exceptions.append({'name':name,'page':pn,'value':value,'format':formats[col-1],
                                           'valueBox':boxes[col],'nameBox':[14.2,row.bbox[1],296.92,row.bbox[3]],'qualification':qualification})
                odds.append(item)
    assert len(odds)==349 and len(formats)==6 and len(exceptions)==1,(len(odds),len(formats),len(exceptions))
    return odds,formats,raw,exceptions

def build():
    cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text())
    record=next(r for r in catalog['sets'] if r['slug']==SLUG)
    dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
    path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
    fingerprint=acquire(data['source'],path)
    rows,raw=read_cards(path)
    op=path.with_name(SLUG+'-odds.pdf');odds_hash=acquire(data['oddsSource'],op)
    odds,formats,odds_raw,exceptions=read_odds(op)
    families={r[0] for r in rows}
    canonical=lambda value:re.sub(r'[^A-Z0-9]','',value.upper())
    aliases={
        'CHROME RADIATING ROOKIES':'TOPPS CHROME RADIATING ROOKIES',
        'MVP BUYBACKS':'2025 CHROME MVP BUYBACKS',
        'TOPPS CHROME CHAMPION GOLD':'TOPPS CHROME CHAMPION REFRACTORS',
        'TOPPS CHROME ROOKIE AUTOGRAPHS':'ROOKIE AUTOGRAPHS',
        'TOPPS CHROME RETAIL ROOKIE AUTOGRAPHS':'RETAIL ROOKIE AUTOGRAPHS',
        'TOPPS CHROME LEGENDS AUTOGRAPHS':'CHROME LEGEND AUTOGRAPHS',
        'TOPPS CHROME MVP BUYBACKS AUTOGRAPHS':'2025 CHROME MVP BUYBACKS AUTOGRAPHS',
        '1991 TOPPS CHROME AUTOGRAPHS':'1991 TOPPS BASEBALL AUTOGRAPHS',
        '2025 WORLD SERIES CHAMPIONS AUTOGRAPHS':'2025 WORLD CHAMPIONS AUTOGRAPH REFRACTOR',
    }
    for odd in odds:
        candidates=[(f,f) for f in families if canonical(odd['name']).startswith(canonical(f))]
        candidates.extend((prefix,family) for prefix,family in aliases.items()
                          if odd['name']==prefix or odd['name'].startswith(prefix+' '))
        if candidates:
            prefix,family=max(candidates,key=lambda pair:len(canonical(pair[0])))
            odd.update(family=family,familyBase=canonical(odd['name'])==canonical(prefix) and prefix!='TOPPS CHROME CHAMPION GOLD')
    assert all(o.get('family') in families for o in odds),'Unreconciled source-family caption'
    note=('All 1,643 original subject rows, 300 base numbers, 300 Lightboard Logo entries and 412 literal Rookie flags '
          'are reconciled to physical number/name/team columns and matching continuation-page baselines. '
          'All 30 unnumbered Fanatics Authentics redemption entries, repeated signer numbers, literal spellings and the blank '
          'Commissioners Trophy subject remain unchanged. Numeric section headings are captions, not card numbers. '
          'Name pages 1–31 correspond to rookie pages 33–63; no rookie continuation for name page 32 is published. '
          'All 349 odds categories and six printed format headings are retained, including the Breaker Delight decimal '
          '0.39374999999999999 and printed 1:1,2175 ratio without correction. Six printed Sapphire image-variation categories have blank values in every listed format and remain present. The decimal has no inferred unit or probability. '
          'Exhaustive supplementary parallel numbering and a calendar release date remain unverified.')
    data.update(headers=['Checklist section','Card number','Name','Team','Rookie','Source page','Rookie source page'],
                rows=rows,rawPages=raw,unclassifiedLines=[],sha256=fingerprint,sectionColumn=0,
                importKind='topps-grid-pdf',dedicatedParser=PARSER,coverageComplete=True,
                odds=odds,formats=formats,oddsRawPages=odds_raw,oddsSha256=odds_hash,oddsIssues=[],
                oddsParser=PARSER,oddsLiteralExceptions=exceptions,
                sourceSheets=[{'name':'Official source reconciliation','notes':[['Source scope',note]]}])
    dp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
    record.update(rowCount=len(rows),sections=len(families),sha256=fingerprint,importKind=data['importKind'],
                  dedicatedParser=PARSER,coverageComplete=True,odds=len(odds),formats=len(formats),
                  oddsParser=PARSER,oddsImportIssues=0,catalogEvidence=note,dataAudit=note)
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text())
    inventory=[record if r['slug']==SLUG else r for r in inventory]
    if not any(r['slug']==SLUG for r in inventory):inventory.append(record)
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    print('Imported Chrome Baseball: 1,643 source rows, 30 unnumbered redemptions, 412 rookie flags and all 349 odds categories.')

if __name__=='__main__':build()
