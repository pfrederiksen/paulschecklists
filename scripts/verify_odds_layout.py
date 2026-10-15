"""Check literal publisher headings, independent source values and edge cases."""
import collections, hashlib, json, re
from pathlib import Path
import pdfplumber

root = Path(__file__).resolve().parents[1]
catalog = json.loads((root / 'data/set-catalog.json').read_text())['sets']
repaired = [s for s in catalog if s.get('oddsParser') == 'scripts/official_odds_layout.py']
assert len(repaired) >= 21
compact = lambda s: re.sub(r'\s+', '', s)
for record in repaired:
    data = json.loads((root / record['tableData']).read_text())
    path = root / 'data/catalog-sources/downloads' / (record['slug'] + '-odds.pdf')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == data['oddsSha256']
    assert record['odds'] == len(data['odds']) and record['formats'] == len(data['formats'])
    with pdfplumber.open(path) as pdf:
        header_rows = pdf.pages[0].find_tables()[0].extract()
        header = header_rows[0]
        if [' '.join((v or '').split()) for v in header] == ['SUBJECT TO CHANGE', '']:
            assert header_rows[1] == ['', ''] and header_rows[2][0] == 'Cards'
            header = header_rows[2]
        text = ' '.join(v or '' for v in header)
        if data.get('formatNamesPublished') is False:
            assert data['formats'] == ['Published odds (format not named)']
            assert data['oddsUnitsPublished'] is False
            if data.get('formatHeaderIsProductTitle'):
                assert compact(text)=='Card2025MarvelTheCollector'
                assert data['officialOddsHeader']==['Card','2025 Marvel The Collector']
                assert data['officialOddsFormats']==['2025 Marvel The Collector']
                assert data['odds']==[{**row,'family':data['odds'][i]['family'],'values':{data['formats'][0]:row['values'][data['officialOddsFormats'][0]]}} for i,row in enumerate(data['officialOddsTable'])]
            else:
                assert not text.startswith(('Card ', 'Cards ')), 'Do not mislabel a printed header as absent'
        else:
            caption = re.match(r'^(All Components|Description|COMPONENT|Cards|Card)', text)
            assert caption, (record['title'], text)
            if record['slug'] == 'topps-bowman-2026-topps-chrome-wwe':
                # The flattened header reads across each line, while each
                # original column wraps independently. Preserve every token
                # and verify the left-to-right printed SKU order separately.
                assert collections.Counter(text[caption.end():].split()) == collections.Counter(' '.join(data['formats']).split())
                assert re.findall(r'\b(\d{4})\s+-', text) == [re.match(r'\d{4}', f)[0] for f in data['formats']]
            elif record['slug'] == 'topps-bowman-2025-topps-chrome-football-sapphire':
                # Retained full source headings wrap across all 14 columns;
                # the public view intentionally exposes only Sapphire.
                source_formats=data['officialOddsFormats']
                assert len(source_formats)==14
                assert collections.Counter(compact(text[caption.end():])) == collections.Counter(compact(' '.join(source_formats)))
                assert re.findall(r'\b(\d{4})\s+-',text)==[re.match(r'\d{4}',f)[0] for f in source_formats]
            elif record['slug'] == 'topps-bowman-2026-topps-flagship-football':
                # This dense wrapped header has no vertical separators. Text
                # extraction reads by line and merges adjacent headings;
                # the physical parser retains each original column's glyphs.
                assert collections.Counter(compact(text[caption.end():])) == collections.Counter(compact(' '.join(data['formats'])))
                assert len(data['formats']) == 20
                assert data['formats'][:4] == ['Hobby Silver PK Pack Rate','Hobby Pack Rate','Jumbo Silver PK Pack Rate','Jumbo Pack Rate']
            else:
                source_formats=data.get('officialOddsFormats',data['formats'])
                assert compact(text[caption.end():]) == compact(' '.join(source_formats)), (record['title'], text, source_formats)
    assert all(o['name'] and set(o['values']) == set(data['formats']) for o in data['odds'])

def load(slug):
    return json.loads((root / 'data/imports' / (slug + '.json')).read_text())
def odd(data, name):
    return next(o for o in data['odds'] if o['name'] == name)
finest = load('topps-bowman-2026-topps-finest-baseball')
assert odd(finest, 'Base Cards Common Refractor')['values'] == {'Hobby': '1:3', 'First Day Issue': '1:3', 'Breaker': '1:2', 'Mega Box': '1:9'}
marvel = load('topps-bowman-2026-topps-chrome-marvel-comics')
assert odd(marvel, 'Base - Characters Refractor')['values'] == {'Hobby': '1:2', 'Value CEE': '1:4', 'Value EA': '1:4', 'Value SE': '1:4', 'Mega SE': '1:4', 'Mega EA': '1:4', 'Mega CEE': '1:4'}
assert odd(marvel, 'Fanfare Superfractor')['values']['Value CEE'] == '1:171.596', 'Keep the printed period separator'
black = load('topps-bowman-2026-topps-chrome-black-basketball')
assert odd(black, 'Base Base')['values'] == {'Hobby Pack Rate': '3:1', 'Hobby Box Topper: Autographs Pack Rate': None}
inception = load('topps-bowman-2025-topps-inception-baseball')
assert odd(inception, 'Base Blue')['values']['Hobby'] == '01:44:00', 'Do not turn a published three-part cell into inferred 1:44 odds'
platinum = load('topps-bowman-2025-topps-chrome-platinum-baseball')
assert sum(o['name'] == 'Base' for o in platinum['odds']) > 1, 'The official repeated rows must not be silently deduplicated'
disney = load('topps-bowman-2026-topps-chrome-disney')
assert len(disney['odds']) == 210 and any(all(v is None for v in o['values'].values()) for o in disney['odds']), 'Retain categories with entirely blank odds'
registry = json.loads((root / 'data/parallel-specifications.json').read_text())
wwe = load('topps-bowman-2026-topps-chrome-wwe')
assert len(wwe['odds']) == 410 and len(wwe['formats']) == 11
assert not any(o['name'] == 'AUSTIN' for o in wwe['odds']), 'Retain ratio-shaped category titles'
assert odd(wwe, 'AUSTIN 3:16')['values'][wwe['formats'][1]] == '1:42'
assert odd(wwe, 'AUSTIN 3:16 GOLD REFRACTOR')['values'][wwe['formats'][-1]] == '1:991'
assert odd(wwe, 'SAY HIS NAME SUPERFRACTOR')['values'][wwe['formats'][-1]] == '1:2,476,800', 'The final-page split header must not become a category'
assert odd(wwe, 'FAMILY TREE GOLD REFRACTOR')['values'][wwe['formats'][1]] == '1:689'
assert any(c['slug'] == 'topps-bowman-2025-topps-exalted-wwe' and c['family'] == 'BASE CARDS' for c in registry['conflicts'])
print(f'Verified {len(repaired)} physical odds imports, literal format headings, column assignments, repeated rows, blank categories and unusual published notation.')
