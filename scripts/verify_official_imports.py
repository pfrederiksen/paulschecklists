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
   original.update(word['text'] for word in page.extract_words(x_tolerance=tolerance,use_text_flow=data.get('oddsParser') in {'scripts/import_topps_star_wars_backfills.py','scripts/import_topps_jennie_2026.py','scripts/import_topps_cactus_jack_2025.py'}) if re.fullmatch(r'[\d,.]+(?::[\d,.]+)+',word['text']))
  for exception in data.get('oddsLiteralExceptions',[]):
   # A malformed literal must be verified inside its original physical value
   # cell, not promoted to a ratio or added from an arbitrary PDF number.
   page=pdf.pages[exception['page']-1]
   if exception.get('valueBox'):
    # A borderless multi-column row needs the recorded physical value box;
    # the flattened table cell includes its caption and all six values.
    name=' '.join((page.crop(tuple(exception['nameBox'])).extract_text() or '').split())
    value=''.join(c['text'] for c in page.chars if exception['valueBox'][0]-.01<=c['x0'] and c['x1']<=exception['valueBox'][2]+.01 and exception['valueBox'][1]-.01<=c['top'] and c['bottom']<=exception['valueBox'][3]+.01)
    assert name==exception['name'] and value==exception['value'],(set['title'],exception)
    assert any(o['name']==name and o['values'][exception['format']]==value for o in data['odds'])
   else:
    matches=[row for table in page.find_tables() for row in table.extract()[1:] if ' '.join((row[0] or '').split())==exception['name']]
    assert len(matches)==1 and ' '.join(matches[0][1].split())==exception['value'],(set['title'],exception)
   assert not re.fullmatch(r'[\d,.]+(?::[\d,.]+)+',exception['value'])
   original.update([exception['value']])
 source_rows=data.get('officialOddsTable',data['odds'])
 imported=collections.Counter(value for row in source_rows for value in row['values'].values() if value)
 if data.get('oddsParser')=='scripts/official_odds_layout.py':
  category_literals=collections.Counter(token for row in source_rows for token in row['name'].split() if re.fullmatch(r'[\d,.]+(?::[\d,.]+)+',token))
  assert not category_literals-original, (set['title'],'Category literal is not printed in source')
  original.subtract(category_literals);original=+original
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
