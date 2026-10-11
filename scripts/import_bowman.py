import json,re,hashlib
from pathlib import Path
import pdfplumber
root=Path(__file__).resolve().parents[1];src=root/'data/sources/bowman-football-2026'
def lines(page):
 rows=[]
 for w in sorted(page.extract_words(),key=lambda w:w['top']):
  if rows and abs(w['top']-rows[-1][0])<3:rows[-1][1].append(w)
  else:rows.append((w['top'],[w]))
 return [sorted(ws,key=lambda w:w['x0']) for _,ws in rows]

sections=[];current=None;category='Base';raw_count=0
with pdfplumber.open(src/'checklist.pdf') as pdf:
 for page_no,p in enumerate(pdf.pages,1):
  for ws in lines(p):
   line=' '.join(w['text'] for w in ws)
   if line.startswith(('Checklists provided','product at the time')):continue
   if line in ['BASE','INSERT','AUTOGRAPH']:category=line.title();continue
   number=' '.join(w['text'] for w in ws if w['x0']<134)
   if re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9-]+',number) and len(ws)>1 and ws[0]['x0']<134:
    name=' '.join(w['text'] for w in ws if 134<=w['x0']<296)
    team=' '.join(w['text'] for w in ws if 296<=w['x0']<461).replace('®','').replace('™','')
    rookie=any(w['text']=='Rookie' and w['x0']>=461 for w in ws)
    assert current and name,(page_no,line)
    current['cards'].append({'number':number,'subjects':[{'number':number,'name':name,'team':team,'rookie':rookie,'sourceText':line,'page':page_no}]});raw_count+=1
   elif ws[0]['x0']>=200 and current and current['cards']:
    subject=current['cards'][-1]['subjects'][-1];subject['team']+=' '+line.replace('®','').replace('™','');subject['sourceText']+=' '+line
   elif line.isupper():current={'id':len(sections),'name':line,'category':category,'cards':[]};sections.append(current)
   else:raise ValueError((page_no,line))
odds=[];keys=['hobby','fdi','breaker','jumbo','mega','value'];bounds=[(590,700),(700,800),(800,910),(910,1025),(1025,1140),(1140,1300)]
with pdfplumber.open(src/'odds.pdf') as pdf:
 for page_no,p in enumerate(pdf.pages,1):
  for ws in lines(p):
   vals=[' '.join(w['text'] for w in ws if a<=w['x0']<b) for a,b in bounds]
   if not any(v.startswith('1:') for v in vals):continue
   name=' '.join(w['text'] for w in ws if w['x0']<590)
   assert all(not v or v=='-' or re.fullmatch(r'1:[\d,]+',v) for v in vals),(name,vals)
   odds.append({'name':name.upper(),'odds':{k:None if v in ['', '-'] else int(v[2:].replace(',','')) for k,v in zip(keys,vals)},'page':page_no})
aliases={'BASE NFL':'BASE NFL','CHROME NFL BASE':'CHROME NFL BASE','CHROME ROOKIE BASE':'CHROME ROOKIE BASE','BASE CHROME AUTOGRAPHS':'BASE CHROME AUTOGRAPH','CHROME PROSPECT AUTOGRAPHS':'CHROME PROSPECTS AUTOGRAPH','PAPER PROSPECT AUTOGRAPHS':'PAPER PROSPECTS AUTOGRAPHS'}
# Longest-prefix ownership prevents an autograph or variation leaking into base parallels.
prefixes={s['id']:aliases.get(s['name'],s['name']) for s in sections}
for s in sections:s['oddsIds']=[]
for i,o in enumerate(odds):
 matches=[s for s in sections if o['name']==prefixes[s['id']] or o['name'].startswith(prefixes[s['id']]+' ')]
 if matches:
  owner=max(matches,key=lambda s:len(prefixes[s['id']]));owner['oddsIds'].append(i);o['label']=o['name'][len(prefixes[owner['id']]):].strip() or 'Standard / original'
# Multi-subject autograph codes are grouped; base numbering errors remain separate rows.
for s in sections:
 if s['category']=='Autograph':
  grouped={}
  for c in s['cards']:
   if c['number'] not in grouped:grouped[c['number']]=c
   else:grouped[c['number']]['subjects'].extend(c['subjects'])
  s['cards']=list(grouped.values())
assert len(sections[0]['cards'])==100 and len(sections[1]['cards'])==100
assert len(sections[2]['cards'])==201
notes=['The official NFL base checklist prints #68 twice (Tua Tagovailoa and Jaylen Waddle) and omits #66. Both source entries are preserved; numbering is not corrected or treated as a multi-player card.','Blank odds cells and dashes both mean no published odds for that format.']
x={'title':'2026 Bowman Football','verified':'2026-10-11','formats':[{'id':k,'name':n} for k,n in zip(keys,['Hobby','FDI','Breaker','Jumbo','Mega','Value'])],'sections':sections,'odds':odds,'notes':notes,'source':{'product':'https://www.topps.com/pages/bowman-football','checklist':'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Bowman_Football_Checklist.pdf?v=1790867994','odds':'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Bowman_Football_Odds.pdf?v=1790713108'},'sha256':{n:hashlib.sha256((src/n).read_bytes()).hexdigest() for n in ['checklist.pdf','odds.pdf']}}
(root/'data/bowman-football-2026.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
print('Parsed',raw_count,'subjects;',sum(len(s['cards']) for s in sections),'cards;',len(sections),'sections;',len(odds),'odds entries')
for s in sections:print(s['name'],len(s['cards']),len(s['oddsIds']))
print('UNMAPPED', [o['name'] for i,o in enumerate(odds) if not any(i in s['oddsIds'] for s in sections)])
