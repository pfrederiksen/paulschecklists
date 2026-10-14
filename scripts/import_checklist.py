"""Rebuild factual checklist data from the retained official Topps PDFs.
Requires pdfplumber. No guessed odds, print runs, or parallel eligibility.
"""
import json,re,hashlib
from pathlib import Path
import pdfplumber
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/sources'
sections=[]; current=None; category='Base'; skipped=[]
categories={'BASE':'Base','INSERT':'Insert','RELIC':'Relic','AUTOGRAPH':'Autograph','AUTOGRAPH RELIC':'Autograph relic'}
with pdfplumber.open(SOURCE/'checklist.pdf') as pdf:
 for page_no,page in enumerate(pdf.pages,1):
  for line in (page.extract_text() or '').splitlines():
   if line.startswith(('Checklists provided','that product','odds may vary.')): continue
   if line in categories: category=categories[line]; continue
   match=re.match(r'^(\d+|[A-Z0-9]+-[A-Z0-9-]+)\s+(.+)$',line)
   if match:
    assert current is not None,line
    number,description=match.groups()
    rookie=description.endswith(' Rookie')
    clean=description.removesuffix(' Rookie')
    # Trademark glyphs delimit the printed team; keep the original text too.
    team_match=re.search(r' ((?:New York|Los Angeles|San Diego|San Francisco|St\. Louis|Boston|Chicago|Miami|Houston|Toronto|Kansas City|Pittsburgh|Washington|Tampa Bay|Seattle|Cincinnati|Atlanta|Cleveland|Philadelphia|Detroit|Baltimore|Colorado|Texas|Minnesota|Milwaukee|Arizona|Oakland|Montréal|Brooklyn|Florida|Penn State|Athletics|Angels)[^®™]*[®™])$',clean)
    team=team_match.group(1).rstrip('®™') if team_match else ''
    name=clean[:team_match.start()] if team_match else clean
    current['cards'].append({'number':number,'name':name,'team':team,'rookie':rookie,'sourceText':description,'page':page_no})
   elif line.isupper():
    current={'id':len(sections),'name':line,'category':category,'cards':[]};sections.append(current)
   else: skipped.append({'page':page_no,'text':line})
assert not skipped,skipped
odds=[]
with pdfplumber.open(SOURCE/'odds.pdf') as pdf:
 for page_no,page in enumerate(pdf.pages,1):
  for table in page.extract_tables():
   for row in table:
    if row[0]=='Card': continue
    label=' '.join(row[0].split())
    values={k:None if v=='-' else int(v.replace('1:','').replace(',','')) for k,v in zip(['fat','hobby','value'],row[1:])}
    odds.append({'name':label,'odds':values,'page':page_no})
# Only explicit family associations. Separate mini exclusives have no published odds.
aliases={
 'BASE CARDS':'BASE CARDS', 'BASE CARDS I MINI VARIATION':'BASE CARD MINI SIZED',
 'DAGUERREOTYPE BASE CARD VARIATIONS':'BASE CARD DAGUERREOTYPE VARIATION REDEMPTION CARD',
 'TIN TYPE BASE CARD VARIATION':'TIN TYPE BASE CARD VARIATION',
 'BASE CARDS CHROME VARIATION':'BASE CARD CHROME VARIATION',
 'BASE CARDS MINI CHROME VARIATION':'BASE MINI CARD CHROME VARIATION',
 'BASE CARDS I MINI METAL VARIATION':'BASE CARD MINI SIZED METALS',
 'BASE CARDS I MINI STAINED GLASS VARIATION':'BASE CARD MINI STAINED GLASS VARIATION',
 'RIP CARDS I':'ALLEN & GINTER RIP CARDS',
 'MINI 50 WAYS TO SAY HELLO':'50 WAYS TO SAY HELLO','MINI MUSICAL METHODS':'MUSICAL METHODS',
 'DOUBLE RIP CARDS':'ALLEN & GINTER DOUBLE RIP CARDS',
 'ALLEN AND GINTER FRAMED RELICS MINI SIZE I':'ALLEN & GINTER FRAMED RELICS MINI',
 'ALLEN AND GINTER FRAMED RELICS MINI SIZE II':'ALLEN & GINTER FRAMED RELICS MINI',
 'MINI BASEBALL AUTOGRAPHS I':'MINI BASEBALL AUTOGRAPH CARDS FRAMED MINI SIZE',
 'MINI NON BASEBALL AUTOGRAPHS':'MINI NON BASEBALL AUTOGRAPH CARDS FRAMED MINI SIZE',
 'FULL SIZE AUTOGRAPH CARDS':'ALLEN & GINTER AUTOGRAPHS FULL SIZE CARDS',
 'MINI EMPLOYEE AUTOGRAPHS':'ALLEN & GINTER EMPLOYEE AUTOGRAPH FRAMED MINI SIZE',
 'DUAL AUTOGRAPHS':'ALLEN & GINTER DUAL AUTOGRAPH FULL SIZE CARDS',
 'QUINTUPLE AUTOGRAPHS':'ALLEN & GINTER QUINTUPLE AUTOGRAPH FULL SIZE CARDS',
 'AUTOGRAPH RELIC CARDS':'ALLEN & GINTER AUTOGRAPHED RELIC CARDS',
 'DUAL AUTOGRAPH RELIC CARDS':'ALLEN & GINTER DUAL AUTOGRAPHED RELIC CARDS',
 'DYNASTY AUTOGRAPHED PATCH CARDS':'DYNASTY AUTOGRAPHED PATCH CARDS',
}
for section in sections:
 prefix=aliases.get(section['name'],section['name'].replace(' AND ',' & '))
 section['oddsIds']=[i for i,o in enumerate(odds) if o['name']==prefix or o['name'].startswith(prefix+' ')]
 # Multiple subjects printed under one card code belong to the same card.
 grouped={}
 for card in section['cards']:
  if card['number'] not in grouped: grouped[card['number']]={'number':card['number'],'subjects':[]}
  grouped[card['number']]['subjects'].append(card)
 section['cards']=list(grouped.values())
assert len(sections[0]['cards'])==300
assert [int(c['number']) for c in sections[0]['cards']]==list(range(1,301))
assert len(odds)==97,len(odds)
result={'title':'2026 Topps Allen & Ginter Baseball','verified':'2026-10-11','sections':sections,'odds':odds,'source':{'product':'https://www.topps.com/pages/topps-allen-ginter-baseball','checklist':'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Allen_and_Ginter.pdf?v=1788875550','odds':'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026-09-29_MLB-ALLEN-_-GINTER-2026_Odds.pdf?v=1790697457'},'sha256':{n:hashlib.sha256((SOURCE/n).read_bytes()).hexdigest() for n in ['checklist.pdf','odds.pdf']}}
# Visually transcribed from the official education sheet, page 2. The sheet
# is image-only: retain the original bytes and exact family scopes.
education=json.loads((SOURCE/'education-specifications.json').read_text())
assert hashlib.sha256((SOURCE/'education.pdf').read_bytes()).hexdigest()==education['sha256']
result['publishedSpecifications']=education['specifications']
result['source']['education']=education['url']
result['sha256']['education.pdf']=education['sha256']
for spec in education['specifications']:
 for name,numbering in spec['rows']:
  for odd in odds:
   if odd['name']==name:
    odd['numbering']=numbering
    odd['numberingSource']={'url':education['url'],'page':2}
(ROOT/'data/allen-ginter-2026.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(len(sections),'sections;',sum(len(s['cards']) for s in sections),'cards;',len(odds),'odds entries')
for s in sections: print(s['name'],len(s['cards']),len(s['oddsIds']))
