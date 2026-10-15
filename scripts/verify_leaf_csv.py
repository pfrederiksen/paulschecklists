"""Compare imported Leaf fields against every untouched official CSV sheet."""
import csv,hashlib,io,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
catalog=json.loads((ROOT/'data/set-catalog.json').read_text())
sets=[s for s in catalog['sets'] if s.get('dedicatedParser')=='scripts/import_leaf_csv.py']
count=0
for item in sets:
 data=json.loads((ROOT/item['tableData']).read_text());assert data['source']==item['checklistUrl'];assert data['headers'][:5]==['Checklist section','Card number','Player / subjects','Source worksheet','Source row']
 observed=json.loads('[]');publication=(ROOT/'data/official-leaf'/f"{item['slug']}-publication.html").read_bytes()
 assert hashlib.sha256(publication).hexdigest()==data['publicationSha256']
 gids=re.findall(r'items\.push\(\{name:\s*"(?:[^"\\]|\\.)*",.*?gid:\s*"(-?\d+)"',publication.decode(),re.S)
 assert gids==[s['gid'] for s in data['sourceSheets']],item['slug']
 original_count=0
 for sheet in data['sourceSheets']:
  blob=(ROOT/sheet['sourceExport']).read_bytes();assert hashlib.sha256(blob).hexdigest()==sheet['sha256']
  reader=list(csv.reader(io.StringIO(blob.decode('utf-8-sig'),newline='')));assert reader.pop(0)==sheet['rawHeaders']
  populated=[(rn,row) for rn,row in enumerate(reader,2) if any(row)];assert len(populated)==sheet['rowCount'];original_count+=len(populated)
  actual=[r for r in data['rows'] if r[3]==sheet['name']];assert len(actual)==len(populated)
  for (rn,source),row in zip(populated,actual):
   assert row[4]==str(rn)
   assert [row[data['headers'].index(h)] for h in sheet['headers']]==source,(item['slug'],rn)
   headers=sheet['rawHeaders']
   if 'Checklist' in headers:assert row[1]==source[headers.index('Checklist')]
   name=next((h for h in ['Name','Name_Oscar'] if h in headers),None)
   if name and source[headers.index(name)]:assert row[2]==source[headers.index(name)]
 assert original_count==len(data['rows'])==item['rowCount'];assert item['publishedOdds'] is False
 fingerprint=hashlib.sha256(json.dumps([{'gid':s['gid'],'sha256':s['sha256']} for s in data['sourceSheets']],sort_keys=True).encode()).hexdigest();assert data['checklistFingerprint']==fingerprint
 assert sum(len(s['rows']) for s in data['publishedSpecifications'])==len(data['rows'])
 count+=len(data['rows'])
football=next(s for s in sets if s['slug']=='leaf-2026-leaf-football');d=json.loads((ROOT/football['tableData']).read_text());assert len(d['sourceSheets'])==2;assert 'asset killed' in d['headers']
trinity=json.loads((ROOT/'data/imports/leaf-2026-leaf-trinity-football.json').read_text());assert 'Bronze [column 6]' in trinity['headers'] and 'Bronze [column 16]' in trinity['headers']
print(f'Verified {len(sets)} official Leaf CSV checklists, every published worksheet, all {count:,} populated rows, duplicate columns, numbering cells, notes and hashes.')
