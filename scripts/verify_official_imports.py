"""Compare every imported PDF odds literal against the retained official PDF."""
import json,re,hashlib,collections,concurrent.futures
from pathlib import Path
import pdfplumber
ROOT=Path(__file__).resolve().parents[1]
def verify(set):
 data=json.loads((ROOT/set['tableData']).read_text())
 path=ROOT/'data/catalog-sources/downloads'/(set['slug']+'-odds.pdf')
 assert hashlib.sha256(path.read_bytes()).hexdigest()==data['oddsSha256'],set['title']
 tolerance=.1 if any(term in path.name for term in ['flagship-football','series-1-baseball','series-2-baseball']) else 3
 original=collections.Counter()
 with pdfplumber.open(path) as pdf:
  for page in pdf.pages:
   original.update(word['text'] for word in page.extract_words(x_tolerance=tolerance) if re.fullmatch(r'[\d,.]+(?::[\d,.]+)+',word['text']))
 source_rows=data.get('officialOddsTable',data['odds'])
 imported=collections.Counter(value for row in source_rows for value in row['values'].values() if value)
 if data.get('oddsScope'):
  scope=data['oddsScope']
  assert data['formats']==[scope]
  assert data['odds']==[{**row,'values':{scope:row['values'][scope]}} for row in source_rows if row['values'][scope] is not None],set['title']
 assert original==imported,(set['title'],original-imported,imported-original)
 return len(source_rows),sum(imported.values())
if __name__=='__main__':
 catalog=json.loads((ROOT/'data/set-catalog.json').read_text());sets=[set for set in catalog['sets'] if set.get('oddsUrl')]
 with concurrent.futures.ProcessPoolExecutor(max_workers=6) as pool:results=list(pool.map(verify,sets))
 print(f'Every odds literal matched its official PDF: {len(sets)} documents, {sum(r[0] for r in results)} rows, {sum(r[1] for r in results)} published values. Source SHA-256 hashes matched.')
