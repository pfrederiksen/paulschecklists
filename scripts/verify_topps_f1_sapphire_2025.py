"""Check all F1 field continuations, literal rookies and scoped odds values."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2025-topps-chrome-formula-1-sapphire-edition'
d = json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
p = ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_f1_sapphire_2025.py'
assert len(d['rows'])==346 and len({r[0] for r in d['rows']})==9
assert sum(r[6]=='Rookie' for r in d['rows'])==35
assert sum(not r[4] for r in d['rows'])==26
compact = lambda text: re.sub(r'\s+','',text)
index = 0
with pdfplumber.open(p) as pdf:
    assert len(pdf.pages)==27
    for pn in range(9):
        pages = [pdf.pages[pn+x] for x in [0,9,18]]
        tables = [page.find_tables() for page in pages]
        for triplet in zip(*tables):
            for source_rows,number_name in zip(zip(*(t.rows for t in triplet)),triplet[0].extract()):
                row = d['rows'][index]
                assert row[1:3]==number_name,(pn,row,number_name)
                assert row[3]==str(pn+1) and row[8:10]==[str(pn+10),str(pn+19)]
                # Compare the complete original draw sequence within each
                # physical row; no text may be dropped at column borders.
                for page,box,fields in zip(pages,[r.bbox for r in source_rows],[row[1]+row[2],row[4]+row[5],row[6]]):
                    text=''.join(c['text'] for c in page.chars if c['x0']>=0 and box[1] <= (c['top']+c['bottom'])/2 < box[3])
                    assert compact(text)==compact(fields),(pn,text,row)
                index+=1
assert index==346
base=[r for r in d['rows'] if r[0]=='BASE CARDS']
assert len(base)==210 and {int(r[1]) for r in base}==set(range(1,201))
assert all(sum(r[1]==str(n) for r in base)==2 for n in range(164,174))
assert [r[2] for r in base if r[1]=='164']==['Max Verstappen','Yuki Tsunoda']
assert next(r for r in base if r[1]=='8')[6]=='Rookie'
assert next(r for r in base if r[1]=='149')[4]==''
assert next(r for r in d['rows'] if r[1]=='CAC-COL')[2:7]==['Franco Colapinto','7','BWT Alpine Formula One™ Team','Chrome Autographs','']
assert next(r for r in d['rows'] if r[1]=='24')[2]=='Josep MaríaMartí','Keep printed spelling'
assert next(r for r in d['rows'] if r[1]=='HC-8')[2]=='OliverBearman','Keep printed spelling'
assert d['oddsScope']=='Sapphire Pack Rate' and d['formats']==['Sapphire Pack Rate']
full=d['officialOddsTable']
assert len(full)==274 and len(d['officialOddsFormats'])==7
assert len(d['odds'])==51
assert d['odds']==[{**o,'values':{'Sapphire Pack Rate':o['values']['Sapphire Pack Rate']}} for o in full if o['values']['Sapphire Pack Rate'] is not None]
assert not any(o['name']=='Base Refractor Parallel' for o in d['odds'])
assert next(o for o in d['odds'] if o['name']=='Base Orange Sapphire Parallel')['values']=={'Sapphire Pack Rate':'1:17'}
assert sum(o['name']=='Chrome Autographs Sapphire' for o in d['odds'])==2
assert not d.get('parallelSpecifications'),'No regular Chrome ladder may be copied to Sapphire'
op=p.with_name(SLUG+'-odds.pdf')
assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
with pdfplumber.open(op) as pdf:
    values=collections.Counter(w['text'] for page in pdf.pages for w in page.extract_words() if re.fullmatch(r'[\d,.]+(?::[\d,.]+)+',w['text']))
assert values==collections.Counter(v for o in full for v in o['values'].values() if v)
proof=d['productConfigurationEvidence']
assert hashlib.sha256((ROOT/proof['file']).read_bytes()).hexdigest()==proof['sha256']
record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert record['year']=='2025' and record['productYear']=='2026' and record['releaseDate'] is None
assert record['availableFrom']=='2026-02-13'
assert record['releaseStatus']=='Released' and record['releaseEvidence']=='https://www.topps.com/pages/formula-1-chrome-sapphire'
print('Verified all 346 physical rows, 200 distinct base numbers, 35 rookie flags, 26 blank teams, 51 Sapphire odds, seven retained full-source columns and scoped regional availability.')
