"""Verify original CSV cells, qualified guide units and the Golf ordering alternate."""
import collections,csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads((ROOT/path).read_text())
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
proof_path='data/parallel-audit-sources/panini-older-sports-guides-20261021-1900.json'
proof=read(proof_path);assert len(proof['snapshots'])==3
assert sum(len(s['facts']) for s in proof['snapshots'])==23
catalog=read('data/set-catalog.json')['sets']
for slug,ids in proof['mapping'].items():
 record=next(s for s in catalog if s['slug']==slug);data=read(record['tableData'])
 assert record['guideReview']==data['guideReview']
 assert record['guideReview']['file']==proof_path and record['guideReview']['sha256']==sha(proof_path)
 assert record['releaseDate'] is None and not record['publishedOdds']
 assert not data.get('odds') and not data.get('formats') and not data.get('categoryNumbering')
 original=list(csv.reader((ROOT/record['sourceExport']).read_text().splitlines()))
 assert [r[4:] for r in data['rows']]==original[1:]
 assert record['sha256']==data['sha256']==sha(record['sourceExport'])
 assert data['sourceSelection']['year']=='2025'
 observation=read(record['sourceObservation']['file']);previous=observation['originalCsvObservation']
 assert previous['sha256']==sha(previous['file'])
 for snapshot in [s for s in proof['snapshots'] if s['id'] in ids]:
  facts=json.dumps(snapshot['facts'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
  assert hashlib.sha256(facts).hexdigest()==snapshot['factsSha256']
  spec=next(s for s in data['publishedSpecifications'] if s.get('source')==snapshot['source'])
  assert spec['headers']==['Field','Value','Scope / qualifier','Official source']
  assert spec['rows']==[[*r,snapshot['source']] for r in snapshot['facts']]
  assert spec['evidenceSha256']==sha(proof_path)
facts={s['id']:{r[0]:r[1:] for r in s['facts']} for s in proof['snapshots']}
golf=facts['impeccable-golf-hobby'];assert [golf[k][0] for k in ['Cards per pack','Packs per box','Boxes per case']]==['8','1','3']
assert [golf[k][0] for k in ['Autographs per box','Base/Base Parallels per box','Insert per box']]==['3','4','1']
assert all('on average' in golf[k][1] for k in ['Autographs per box','Base/Base Parallels per box','Insert per box'])
boys=facts['boys-of-summer-guide'];assert boys['Autographs per box'][0]=='3' and boys['Memorabilia card per box'][0]=='1'
assert 'format not named' in boys['Autographs per box'][1]
combat=facts['combat-anthology-hobby'];assert [combat[k][0] for k in ['Packs per box','Cards per pack','Inserts or parallels per box','Autographs per box']]==['4','10','20','2']
assert 'combined' in combat['Inserts or parallels per box'][1]
for key in ['boys-of-summer-guide','combat-anthology-hobby']:assert 'not a verified general release date' in facts[key]['Article publication'][1]
review=proof['csvAlternateReview'];assert sha(review['primaryFile'])==review['primarySha256'] and sha(review['alternateFile'])==review['alternateSha256']
primary=list(csv.reader((ROOT/review['primaryFile']).read_text().splitlines()));alternate=list(csv.reader((ROOT/review['alternateFile']).read_text().splitlines()));assert primary[0]==alternate[0] and len(primary)==len(alternate)==2059
changed=[]
for line,(a,b) in enumerate(zip(primary[1:],alternate[1:]),2):
 assert len(a)==len(b)==10 and a[:5]==b[:5] and a[8:]==b[8:]
 def aligned(row):
  parts=[row[i].split('/') for i in [5,6,7]];assert len({len(p) for p in parts})==1
  return collections.Counter(zip(*parts))
 assert aligned(a)==aligned(b)
 if a!=b:assert len(a[5].split('/'))==4;changed.append({'csvLine':line,'primary':a,'alternate':b})
assert changed==review['differingRows'] and len(changed)==34
print('Verified23 qualified guide facts across3 programs; original CSV rows/numbering preserved,34 Golf alternates reorder the same four aligned signers. Box averages, publication dates and product context never become pack odds, new serial limits or release dates.')
