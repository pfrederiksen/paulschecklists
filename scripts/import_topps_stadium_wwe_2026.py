"""Reconcile glyph draw order to avoid overlapping WWE names/designations."""
import json,re,hashlib,urllib.request
import pdfplumber
import import_official_catalog as g
ROOT=g.ROOT;slug='topps-bowman-2026-topps-stadium-club-wwe';page='https://www.topps.com/pages/topps-stadium-club-wwe'
url='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Stadium_Club_WWE_-_Checklist.pdf?v=1791221305';odds='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Stadium_Club_WWE_Odds.pdf?v=1791212522'
blob=urllib.request.urlopen(url,timeout=30).read();path=g.CACHE/(slug+'.pdf');path.write_bytes(blob);rows=[];raw=[];family='Checklist'
with pdfplumber.open(path) as pdf:
 for pn,p in enumerate(pdf.pages,1):
  raw.append({'page':pn,'text':p.extract_text() or ''});groups=[]
  for c in p.chars:
   group=next((group for group in groups if abs(group[0]['top']-c['top'])<2),None)
   if group is None:groups.append([c])
   else:group.append(c)
  for cs in sorted(groups,key=lambda cs:cs[0]['top']):
   # Preserve PDF drawing sequence within each physical line, not x-order.
   text=lambda a:''.join(c['text'] for c in a).strip()
   ni=next((i for i,c in enumerate(cs) if abs(c['x0']-132.62)<.03),None)
   number=text(cs[:ni]) if ni is not None else ''
   if ni is not None and re.fullmatch(r'\d+|[A-Z]+(?:-[A-Z0-9-]+|\d+)',number):
    bi=[i for i,c in enumerate(cs) if i>ni and abs(c['x0']-269.45)<.03]
    assert bi,(pn,number,text(cs));bi=bi[-1]
    ri=next((i for i,c in enumerate(cs) if i>bi and abs(c['x0']-421.27)<.03),len(cs))
    name=text(cs[ni:bi]);designation=text(cs[bi:ri]);rookie=text(cs[ri:])
    assert name and rookie in ['', 'Rookie'],(pn,number,name,designation,rookie)
    rows.append([family,number,name,designation,rookie,str(pn)])
   else:
    line=text(sorted(cs,key=lambda c:c['x0']))
    if line and line==line.upper() and re.search('[A-Z]',line):family=line
assert len([r for r in rows if r[0]=='BASE CARDS'])==200
assert any(r[0]=='BASE CARDS' and r[1]=='8' and r[2]=='"The American Nightmare" Cody Rhodes' and r[3]=='Smackdown' for r in rows)
ob=urllib.request.urlopen(odds,timeout=30).read();op=g.CACHE/(slug+'-odds.pdf');op.write_bytes(ob);entries,formats,oraw,issues=g.odds_pdf(op);assert not issues,issues
payload={'title':'2026 Topps Stadium Club WWE','headers':['Checklist section','Card number','Name','Published designation','Rookie','Source page'],'rows':rows,'source':url,'sha256':hashlib.sha256(blob).hexdigest(),'rawPages':raw,'importKind':'pdf','sectionColumn':0,'odds':entries,'formats':formats,'oddsSource':odds,'oddsSha256':hashlib.sha256(ob).hexdigest(),'oddsRawPages':oraw,'oddsIssues':issues}
path='data/imports/'+slug+'.json';(ROOT/path).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
r={'title':payload['title'],'manufacturer':'Topps / Bowman','sport':'wrestling','year':'2026','slug':slug,'page':'sets/'+slug+'.html','sourcePage':page,'checklistUrl':url,'oddsUrl':odds,'tableData':path,'status':'Source table','importKind':'pdf','dedicatedParser':'scripts/import_topps_stadium_wwe_2026.py','rowCount':len(rows),'sections':len(set(r[0] for r in rows)),'odds':len(entries),'formats':len(formats),'parallelData':True,'publishedOdds':True,'releaseStatus':'Upcoming','releaseDate':'2026-10-23','sha256':payload['sha256'],'verified':'2026-10-12','catalogEvidence':'Official product page lists October 23 availability. Physical name/designation columns overlap for long names in PDF text extraction; original glyph draw order preserves every printed character. Raw, Smackdown, NXT, Legend and other designations are preserved as published fields, not inferred teams. Source ratios such as 5:1 mean five cards per pack, not one-in-five pack odds.','dataAudit':'Physical glyph origins reconcile card number, name, designation and printed rookie values; 200 base cards and the overlapping Cody Rhodes row verified. All literal odds columns validated without alignment issues.'}
p=ROOT/'data/set-catalog.json';c=json.loads(p.read_text());c['sets']=[x for x in c['sets'] if x['slug']!=slug]+[r];p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'data/topps-product-official-catalog.json';inv=json.loads(p.read_text());inv=[x for x in inv if x['slug']!=slug]+[r];p.write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
print(r['title'],len(rows),'rows;',len(entries),'odds;',sum(r[4]=='Rookie' for r in rows),'rookie markers',formats)
