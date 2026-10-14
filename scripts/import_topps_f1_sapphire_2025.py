"""Join horizontally paginated F1 fields by verified physical row boxes."""
import hashlib
import json
import re
import subprocess
from pathlib import Path
import pdfplumber
from official_odds_layout import physical_odds_pdf

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2025-topps-chrome-formula-1-sapphire-edition'
PARSER = 'scripts/import_topps_f1_sapphire_2025.py'
PRODUCT = 'https://www.topps.com/pages/formula-1-chrome-sapphire'
CHECKLIST = 'https://cdn.shopify.com/s/files/1/0739/2015/1805/files/2025_Topps_Chrome_F1_Sapphire_Edition_Checklist.pdf?v=1770631422'
ODDS = 'https://cdn.shopify.com/s/files/1/0739/2015/1805/files/Topps_Chrome_F1_2025_Odds_8bbac9c4-bcdd-418b-9001-bfe3218c8827.pdf?v=1770631422'
SCOPE = 'Sapphire Pack Rate'
HEADERS = ['Checklist section', 'Card number', 'Name', 'Source page', 'Team',
           'Subset', 'Rookie', 'Published checklist block', 'Team/subset source page', 'Rookie source page']

def row_cells(page, row, origins):
    # Exclude off-page repeated print titles/section headings. Use original
    # glyph draw order so a long team cannot overwrite the next column.
    chars = [c for c in page.chars if c['x0'] >= 0 and row.bbox[1] <= (c['top']+c['bottom'])/2 < row.bbox[3]]
    starts = []
    for col, x in enumerate(origins):
        # Verdana replacements start the first column at 53.04, while the
        # original Aptos cells start at 52.92. Their printed border is shared.
        indices = [i for i,c in enumerate(chars) if abs(c['x0']-x) < (.15 if col==0 else .03)]
        if indices:
            starts.append((max(indices), col))
    assert not chars or starts and starts[0][0] == 0, (row.bbox, ''.join(c['text'] for c in chars))
    values = [''] * len(origins)
    for i,(start,col) in enumerate(starts):
        end = starts[i+1][0] if i+1 < len(starts) else len(chars)
        values[col] = ''.join(c['text'] for c in chars[start:end]).strip()
    return values

def read_cards(path):
    rows, raw = [], []
    block = None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 27
        raw = [{'page':pn,'text':p.extract_text()} for pn,p in enumerate(pdf.pages,1)]
        for pn in range(9):
            pages = [pdf.pages[pn+offset] for offset in [0,9,18]]
            tables = [p.find_tables() for p in pages]
            assert len({len(ts) for ts in tables}) == 1
            # The first print segment contains the true source blocks; its
            # names are outside the ruled body, repeated off-page elsewhere.
            headings = []
            for text in ['BASE CARDS','INSERTS','AUTOGRAPHS']:
                chars = [c for c in pages[0].chars if 'Bold' in c['fontname']]
                ys = sorted(set(round(c['top'],2) for c in chars))
                for y in ys:
                    if ''.join(c['text'] for c in chars if abs(c['top']-y)<.01) == text:
                        headings.append((y,text))
            headings.sort()
            for triplet in zip(*tables):
                assert len({len(t.rows) for t in triplet}) == 1
                for source_rows in zip(*(t.rows for t in triplet)):
                    top,bottom = source_rows[0].bbox[1],source_rows[0].bbox[3]
                    assert all(abs(r.bbox[1]-top)<.01 and abs(r.bbox[3]-bottom)<.01 for r in source_rows)
                    while headings and headings[0][0] < top:
                        block = headings.pop(0)[1]
                    assert block in ['BASE CARDS','INSERTS','AUTOGRAPHS']
                    number,name = row_cells(pages[0],source_rows[0],[52.92,172.34])
                    team,subset = row_cells(pages[1],source_rows[1],[52.92,324.31])
                    rookie, = row_cells(pages[2],source_rows[2],[52.92])
                    assert re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',number) and name and subset
                    assert rookie in ['', 'Rookie']
                    family = 'BASE CARDS' if block == 'BASE CARDS' else subset
                    rows.append([family,number,name,str(pn+1),team,subset,rookie,block,str(pn+10),str(pn+19)])
    assert len(rows) == 346
    assert {int(r[1]) for r in rows if r[0]=='BASE CARDS'} == set(range(1,201))
    assert sum(r[6]=='Rookie' for r in rows) == 35
    return rows,raw

def acquire(url,path):
    subprocess.run(['curl','-sLf','--retry','2','--max-time','30',url,'-o',str(path)],check=True)
    path.with_suffix('.pdf.url').write_text(url)
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    cp = ROOT/'data/set-catalog.json'
    catalog = json.loads(cp.read_text())
    record = next(r for r in catalog['sets'] if r['slug']==SLUG)
    dp = ROOT/record['tableData']
    data = json.loads(dp.read_text())
    path = ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
    fingerprint = acquire(CHECKLIST,path)
    rows,raw = read_cards(path)
    op = path.with_name(SLUG+'-odds.pdf')
    odds_hash = acquire(ODDS,op)
    full,formats,odds_raw,issues = physical_odds_pdf(op)
    assert not issues and len(full)==274 and len(formats)==7 and SCOPE in formats
    for odd in full:
        if odd['name'].startswith('Base '):
            odd['family'] = 'BASE CARDS'
        else:
            families = {r[0] for r in rows if r[0]!='BASE CARDS'}
            matches = [family for family in families if odd['name']==family or odd['name'].startswith(family+' ')]
            if matches:
                family = max(matches,key=len)
                odd.update(family=family,familyBase=odd['name'] in [family,'Chrome Autographs Sapphire'])
    odds = [{**o,'values':{SCOPE:o['values'][SCOPE]}} for o in full if o['values'][SCOPE] is not None]
    assert len(odds)==51
    proof = ROOT/'data/parallel-audit-sources/f1-sapphire-product-20261014.json'
    evidence = json.loads(proof.read_text())
    assert evidence['source']==PRODUCT and evidence['checklistUrl']==CHECKLIST and evidence['oddsUrl']==ODDS
    note = ('All 346 printed subject rows, 200 distinct base numbers, separate Team/Subset fields and 35 literal Rookie flags are reconciled across the three nine-page print segments by identical physical row boxes. '
            'The 200-card base program has 210 subject rows because printed duo numbers 164–173 each repeat for their two subjects. Blank teams and original spelling remain unchanged. '
            'All 274 odds categories and seven original format columns remain in officialOddsTable; this page displays only the 51 rows with published Sapphire Pack Rate values, including repeated autograph rows. '
            'The official launch page states the collection has arrived. The Japanese store lists Product Year 2026 and Available From February 13, 2026, while the checklist/product title identifies 2025. Regional store availability is not a verified universal release date. '
            'Exhaustive parallel-numbering review remains pending; unrelated Chrome format limits are not applied to Sapphire.')
    data.update(headers=HEADERS,rows=rows,rawPages=raw,unclassifiedLines=[],source=CHECKLIST,sha256=fingerprint,
                sectionColumn=0,importKind='topps-grid-pdf',dedicatedParser=PARSER,coverageComplete=True,
                odds=odds,formats=[SCOPE],officialOddsTable=full,officialOddsFormats=formats,oddsScope=SCOPE,
                oddsSource=ODDS,oddsSha256=odds_hash,oddsRawPages=odds_raw,oddsIssues=[],
                oddsParser='scripts/official_odds_layout.py',
                productConfigurationEvidence={'file':str(proof.relative_to(ROOT)),'source':PRODUCT,'sha256':hashlib.sha256(proof.read_bytes()).hexdigest()},
                sourceSheets=[{'name':'Official source reconciliation','notes':[['Checklist and odds scope',note]]}])
    dp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
    record.update(sourcePage=PRODUCT,checklistUrl=CHECKLIST,oddsUrl=ODDS,rowCount=len(rows),
                  sections=len({r[0] for r in rows}),sha256=fingerprint,importKind=data['importKind'],
                  dedicatedParser=PARSER,coverageComplete=True,odds=len(odds),formats=1,
                  oddsParser=data['oddsParser'],oddsImportIssues=0,productYear='2026',availableFrom='2026-02-13',
                  releaseStatus='Released',releaseEvidence=PRODUCT,
                  availabilityEvidence=evidence['regionalStore']['source'],catalogEvidence=note,dataAudit=note)
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip = ROOT/'data/topps-product-official-catalog.json'
    inventory = json.loads(ip.read_text())
    ip.write_text(json.dumps([record if r['slug']==SLUG else r for r in inventory],ensure_ascii=False,indent=2)+'\n')
    print(record['title'],len(rows),'source rows; 35 rookies; 51 Sapphire odds; 274 full-table categories retained')

if __name__=='__main__':
    build()
