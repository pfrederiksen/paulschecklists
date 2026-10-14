"""Verify the new imports against their original physical/workbook fields."""
import json,hashlib,sys,collections
from pathlib import Path
import pdfplumber,xlrd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from import_topps_october_inventory import parse_brooklyn,parse_kaws,parse_xls,CONFIG
for title,sport,page,cl,od,kind in CONFIG:
 import re
 slug='topps-bowman-'+re.sub('[^a-z0-9]+','-',title.lower()).strip('-');d=json.loads((ROOT/'data/imports'/f'{slug}.json').read_text());file=ROOT/'data/catalog-sources/downloads'/(slug+('.xls' if kind=='xls' else '.pdf'))
 assert hashlib.sha256(file.read_bytes()).hexdigest()==d['sha256']
 if kind=='xls':
  s=xlrd.open_workbook(str(file)).sheet_by_index(0);original=[s.row_values(i) for i in range(s.nrows) if s.cell_value(i,1)]
  assert len(original)==len(d['rows'])
  for expected,row in zip(original,d['rows']):assert [str(int(x)) if isinstance(x,float) and x.is_integer() else str(x) for x in expected]==row[1:5]
 if kind=='kaws':
  assert len(d['rows'])==146
  assert next(r[2] for r in d['rows'] if r[1]=='9-A')=='Gunnar Henderson'
  assert next(r[2] for r in d['rows'] if r[1]=='14-A')=='Yoshinobu Yamamoto'
  assert next(r[2] for r in d['rows'] if r[1]=='15-A')=='Roki Saski','Preserve the printed source spelling'
  assert len([r for r in d['rows'] if r[1].startswith('SP-K') and not r[2]])==10
  assert len(set(o['name'] for o in d['odds']))==22,'Production-code dashes must not become pack formats or erase labels'
  assert d['formats']==['Pack']
 if kind=='brooklyn':
  assert len([r for r in d['rows'] if r[0]=='SKETCH CARD ARTISTS'])==55
  assert any(r[2]=='BLANCAS' and r[0]=='SKETCH CARD ARTISTS' for r in d['rows'])
  assert next(o['values']['Hobby'] for o in d['odds'] if o['name']=='Base Set Blue and Silver')=='1:7'
 if kind=='collector':assert d['headers']==['Checklist section','Card number','Name','Team','Rookie','Source page'];assert sum(r[4]=='Rookie' for r in d['rows'])==5
print('Verified physical name columns, wrapped KAWS names, blank subjects, artist roster, original XLS cells and source-specific odds labels.')
