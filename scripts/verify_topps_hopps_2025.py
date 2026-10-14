"""Independently check all Hopps glyph rows and literal rookie continuations."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2025-26-topps-hopps-basketball'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
p=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_hopps_2025.py'
assert len(d['rows'])==1091 and len({r[0] for r in d['rows']})==29
assert sum(r[4]=='Rookie' for r in d['rows'])==384
assert sum(not r[3] for r in d['rows'])==1
compact=lambda text: re.sub(r'\s+','',text)
with pdfplumber.open(p) as pdf:
    index=0
    for pn,page in enumerate(pdf.pages[:23],1):
        groups=collections.defaultdict(list)
        for char in page.chars:
            if 'Bold' in char['fontname'] or pn==1 and char['top']<150:
                continue
            groups[round(char['top'],1)].append(char)
        flag_words=pdf.pages[pn+22].extract_words() if pn<=22 else []
        assert all(w['text']=='Rookie' for w in flag_words)
        for y,chars in sorted(groups.items()):
            row=d['rows'][index]
            assert compact(''.join(c['text'] for c in chars))==compact(row[1]+row[2]+row[3]),(pn,row)
            assert row[5]==str(pn) and row[6]==(str(pn+23) if pn<=22 else '')
            assert row[4]==('Rookie' if any(abs(w['top']-y)<.1 for w in flag_words) else '')
            index+=1
    assert index==1091
base=[r for r in d['rows'] if r[1].isdigit()]
assert [int(r[1]) for r in base]==list(range(1,301))
assert next(r for r in base if r[1]=='35')[2:5]==['Cooper Flagg','Dallas Mavericks','Rookie']
assert next(r for r in d['rows'] if r[1]=='HW-19')[2:4]==["De'Aaron Fox",'San Antonio Spurs']
assert next(r for r in d['rows'] if r[1]=='HS-KW')[2:4]==["Kel'el ware",'Miami Heat']
assert next(r for r in d['rows'] if r[1]=='HS-Td')[2:4]==['Tristan da Silva','Orlando Magic']
assert next(r for r in d['rows'] if r[1]=='HHS-JTA')[2:4]==["Jae'Sean Tate",'Houston Rockets']
assert d['rows'][-1][1:5]==['HHS-ZW','Ziaire Williams','Brooklyn Nets','']
assert all(not r[4] and not r[6] for r in d['rows'] if r[5]=='23')
assert len(d['odds'])==193 and len(d['formats'])==5
assert all(o.get('family') for o in d['odds'])
base_odd=next(o for o in d['odds'] if o['name']=='Base Rainbow')
assert base_odd['family']=='BASE CARDS I'
assert base_odd['familyAliases']==['BASE CARDS II','BASE CARDS III','HIGHLIGHTS','ALL STARS']
assert next(o for o in d['odds'] if o['name']=='Hoops Rookies First Signs')['family']=='HOOPS ROOKIE FIRST SIGNS'
assert next(o for o in d['odds'] if o['name']=='Hoops Rookies Duals')['family']=='HOOPS ROOKIE DUALS'
assert not d.get('parallelSpecifications'),'No unverified numbering inferred from colors'
op=p.with_name(SLUG+'-odds.pdf')
assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
with pdfplumber.open(op) as pdf:
    literals=collections.Counter(w['text'] for page in pdf.pages for w in page.extract_words() if re.fullmatch(r'[\d,.]+(?::[\d,.]+)+',w['text']))
assert literals==collections.Counter(v for o in d['odds'] for v in o['values'].values() if v)
print('Verified 1,091 original subjects, 300 base numbers, separate teams, 384 exact rookie flags, the absent final continuation, mixed-case codes and all 193 odds categories.')
