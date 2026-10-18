"""Reconcile normalized imports against preserved manufacturer CSV bytes."""
import csv, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
records=[r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r.get('importKind')=='panini-csv']
assert records
for record in records:
 raw=(ROOT/record['sourceExport']).read_bytes()
 original=list(csv.reader(raw.decode('utf-8-sig').splitlines()))
 data=json.loads((ROOT/record['tableData']).read_text())
 assert hashlib.sha256(raw).hexdigest()==record['sha256']==data['sha256'],record['slug']
 assert data['headers'][4:]==original[0]
 assert len(original)-1==record['rowCount']==len(data['rows'])
 for normalized,printed in zip(data['rows'],original[1:]):
  assert normalized[4:]==printed
  assert normalized[:4]==[printed[4],printed[8],printed[5],printed[9]]
 expected=[(r[4],r[8],r[5],r[9]) for r in original[1:] if r[9]]
 observed=[(spec['name'],*r) for spec in data['publishedSpecifications'] if spec['headers']==['Card number','Athlete','Published SEQUENCE'] for r in spec['rows']]
 assert sorted(expected)==sorted(observed)
 assert not data.get('odds') and not record.get('publishedOdds')
 if data.get('sourceObservation'):
  proof=data['sourceObservation'];assert hashlib.sha256((ROOT/proof['file']).read_bytes()).hexdigest()==proof['sha256']
  observation=json.loads((ROOT/proof['file']).read_text())
  assert record['releaseDate'] is None and data['checklistFirstObserved']==record['checklistFirstObserved']==observation['observed']
  assert any(o['sha256']==data['sha256'] and o['sourceSelection']==data['sourceSelection'] for o in observation['exports'])
  if proof['file'].endswith('basketball-2025-26-observations-20261014.json'):
   assert data['checklistFirstObserved']=='2026-10-14'
   assert record['sourceYear']=='2025' and record['year']=='2025-26'
   assert '2025-26 Panini' in record['title']
 for spec in data['publishedSpecifications']:
  if spec.get('evidenceFile'):assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
print(f"Verified {len(records)} official Panini exports and {sum(r['rowCount'] for r in records):,} original rows, hashes and numbering entries.")
