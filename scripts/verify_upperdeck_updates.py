"""Verify newly discovered Upper Deck tables against preserved official HTML."""
import hashlib,html,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
catalog=json.loads((ROOT/'data/set-catalog.json').read_text())
for item in catalog['sets']:
 if item.get('discoverySource')!='https://upperdeck.com/checklists/':continue
 assert item['checklistPublished'].startswith('2026-');assert item['releaseDate'] is None
 data=json.loads((ROOT/item['tableData']).read_text());raw=(ROOT/data['sourceExport']).read_bytes();assert hashlib.sha256(raw).hexdigest()==data['sha256']
 table=re.search(r'<table\b.*?</table>',raw.decode(),re.S|re.I)[0];rows=[]
 for row in re.findall(r'<tr\b.*?</tr>',table,re.S|re.I):
  values=[' '.join(html.unescape(re.sub('<[^>]*>',' ',cell)).split()) for cell in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',row,re.S|re.I)]
  if any(values):rows.append(values)
 assert rows[0]==data['headers'];assert rows[1:]==data['rows'];assert len(rows)-1==item['rowCount']
 if item['slug']=='upper-deck-2025-26-stature':
  assert len(data['rows'])==2335;assert data['serialColumn']==8 and data['oddsColumn']==10
  assert data['rows'][0][2]=='Connor McDavid';assert data['rows'][-1][2]=='Samuel Honzek';assert data['rows'][-1][8]=='1'
 print('Verified',item['title'],len(data['rows']),'rows; original teams, rookie marks, numbering, odds, dates and source hash.')
