"""Independently reconcile Chrome Baseball glyphs, rookie pages and odds cells."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-chrome-baseball'
data=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']
assert data['dedicatedParser']=='scripts/import_topps_chrome_baseball_2026.py'
rows=data['rows']
assert len(rows)==1643 and len({r[0] for r in rows})==55
assert sum(r[4]=='Rookie' for r in rows)==412
compact=lambda value:re.sub(r'\s+','',value)
with pdfplumber.open(path) as pdf:
    index=0
    for pn,page in enumerate(pdf.pages[:32],1):
        groups=collections.defaultdict(list)
        for char in page.chars:
            if 'Bold' in char['fontname'] or pn==1 and char['top']<120:
                continue
            groups[round(char['top'],1)].append(char)
        flags=[w for w in pdf.pages[pn+31].extract_words(extra_attrs=['fontname']) if 'Italic' not in w['fontname']] if pn<=31 else []
        assert all(w['text']=='Rookie' for w in flags)
        matched=0
        for y,chars in sorted(groups.items()):
            row=rows[index]
            assert compact(''.join(c['text'] for c in chars))==compact(row[1]+row[2]+row[3]),(pn,row)
            assert row[5]==str(pn) and row[6]==(str(pn+32) if pn<=31 else '')
            rookie=any(abs(w['top']-y)<.1 for w in flags)
            assert row[4]==('Rookie' if rookie else '')
            matched+=rookie
            index+=1
        assert matched==len(flags)
    assert index==len(rows)
assert [int(r[1]) for r in rows if r[0]=='BASE CARDS']==list(range(1,301))
assert [int(r[1]) for r in rows if r[0]=='BASE CARDS LIGHTBOARD LOGO VARIATION']==list(range(1,301))
assert next(r for r in rows if r[0]=='BASE CARDS' and r[1]=='7')[2:5]==['Samuel Basallo','Baltimore Orioles®','Rookie']
assert next(r for r in rows if r[0]=='BASE CARDS' and r[1]=='131')[2:5]==['Jac Caglianone','Kansas City Royals®','Rookie']
redemptions=[r for r in rows if r[0]=='FANATICS AUTHENTICS REDEMPTION CARDS']
assert len(redemptions)==30 and all(not r[1] for r in redemptions)
assert redemptions[1][2:4]==['Oniel Cruz','Pittsburgh Pirates®']
assert redemptions[21][2:4]==['Jackson Holliday','Baltimore Oroles®']
assert next(r for r in rows if r[1]=='CT-1')[2:4]==['','Los Angeles Dodgers®']
assert sum(not r[2] for r in rows)==1 and sum(not r[3] for r in rows)==2
assert len([r for r in rows if r[0]=='HOBBY MASTERS'])==19,'Do not invent an unpublished HM-20'
assert len([r for r in rows if r[0]=='1991 TOPPS BASEBALL'])==30
assert len([r for r in rows if r[0]=='2025 CHROME MVP BUYBACKS'])==2
assert not any(r[1] in {'1991','2025'} for r in rows),'Numeric section headings are not card numbers'
assert all(not r[4] and not r[6] for r in rows if r[5]=='32')
op=path.with_name(SLUG+'-odds.pdf')
assert hashlib.sha256(op.read_bytes()).hexdigest()==data['oddsSha256']
assert len(data['odds'])==349 and len(data['formats'])==6
with pdfplumber.open(op) as pdf:
    original=collections.Counter(w['text'] for page in pdf.pages for w in page.extract_words() if re.fullmatch(r'[\d,.]+(?::[\d,.]+)+',w['text']))
    exception=data['oddsLiteralExceptions'][0]
    assert exception['page']==6 and exception['value']=='0.39374999999999999'
    assert exception['format']=='6623 - MLB-CHROME 2026 BREAKER DELIGHT'
    page=pdf.pages[5]
    box=exception['valueBox']
    literal=''.join(c['text'] for c in page.chars if box[0]-.01<=c['x0'] and c['x1']<=box[2]+.01 and box[1]-.01<=c['top'] and c['bottom']<=box[3]+.01)
    assert literal==exception['value']
    original.update([literal])
assert original==collections.Counter(v for o in data['odds'] for v in o['values'].values() if v)
unusual=next(o for o in data['odds'] if o['name']==exception['name'])
assert unusual['values'][data['formats'][0]]=='1:1,2175'
assert unusual['values'][exception['format']]==exception['value']
assert 'not inferred' in unusual['qualification']
assert sum(all(v is None for v in o['values'].values()) for o in data['odds'])==6
assert all(o.get('family') for o in data['odds'])
print('Verified 1,643 original rows, all 600 base/Lightboard entries, 30 unnumbered redemptions, 412 rookie flags, exact blank cells and all 349 odds categories including the non-ratio decimal.')
