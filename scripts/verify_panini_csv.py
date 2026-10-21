"""Reconcile normalized imports against preserved manufacturer CSV bytes."""
import csv, hashlib, json
from pathlib import Path
from import_panini_pending import export_state
ROOT=Path(__file__).resolve().parents[1]
records=[r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r.get('importKind')=='panini-csv']
assert records
for record in records:
 raw=(ROOT/record['sourceExport']).read_bytes()
 original=list(csv.reader(raw.decode('utf-8-sig').splitlines()))
 assert export_state(original[0],original[1:])=='populated',record['slug']
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
 if data.get('guideReview'):
  proof=data['guideReview'];assert proof==record['guideReview']
  assert hashlib.sha256((ROOT/proof['file']).read_bytes()).hexdigest()==proof['sha256']
  guide=json.loads((ROOT/proof['file']).read_text())
  for snapshot in guide['snapshots']:
   if snapshot['id'] not in guide['mapping'][record['slug']]:continue
   facts=json.dumps(snapshot['facts'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
   assert hashlib.sha256(facts).hexdigest()==snapshot['factsSha256']
   assert any(spec.get('source')==snapshot['source'] and spec.get('rows')==[[*row,snapshot['source']] for row in snapshot['facts']] for spec in data['publishedSpecifications'])
print(f"Verified {len(records)} official Panini exports and {sum(r['rowCount'] for r in records):,} original rows, hashes and numbering entries.")
pending=[r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r.get('importKind')=='panini-source-only']
for record in pending:
 raw=(ROOT/record['sourceExport']).read_bytes()
 printed=list(csv.reader(raw.decode('utf-8-sig').splitlines()))
 state=export_state(printed[0],printed[1:])
 assert state in ['header-only','placeholder-only']
 assert state==record.get('sourceExportState','header-only')
 assert hashlib.sha256(raw).hexdigest()==record['sha256']
 assert record['coverageComplete'] is False and not record.get('tableData') and not record.get('rowCount')
 assert not record.get('publishedOdds') and not record.get('parallelData') and record['releaseDate'] is None
 proof=record['sourceObservation'];assert hashlib.sha256((ROOT/proof['file']).read_bytes()).hexdigest()==proof['sha256']
 observation=json.loads((ROOT/proof['file']).read_text())
 matched=next(o for o in observation['exports'] if o['sha256']==record['sha256'] and o['sourceSelection']==record['sourceSelection'])
 assert matched['rows']==len(printed)-1 and matched['families']==len(set(r[4] for r in printed[1:]))
 if state=='header-only':assert 'header-only' in record['importIssue']
 else:
  assert matched['verifiedRosterRows']==0 and matched['originalPlaceholderRows']==printed[1:]
  assert printed[1][:4]==[record['sourceSelection'][k] for k in ['sport','year','brand','program']]
  assert 'placeholder row' in record['importIssue']
 assert 'Source-only' in record['catalogEvidence']
 if record.get('dedicatedParser')=='scripts/import_panini_pending.py':
  assert record['description'].startswith('Source-only:')
  page=(ROOT/record['page']).read_text()
  assert record['description'] in page and 'data-table=' not in page
 if record.get('productGuideContext'):
  guide=record['productGuideObservation'];blob=(ROOT/guide['file']).read_bytes()
  assert hashlib.sha256(blob).hexdigest()==guide['sha256']
  retained=json.loads(blob)['snapshots']
  for snapshot in record['productGuideContext']:
   assert snapshot in retained
   facts=json.dumps(snapshot['facts'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
   assert hashlib.sha256(facts).hexdigest()==snapshot['sha256']
  assert 'FOTL' in record['catalogEvidence'] and 'Box averages are not pack odds' in record['catalogEvidence']
print(f"Verified {len(pending)} explicit source-only Panini programs with header-only or placeholder-only exports; "+('card coverage remains incomplete.' if pending else 'full manufacturer release inventory and revision coverage remain under review.'))
