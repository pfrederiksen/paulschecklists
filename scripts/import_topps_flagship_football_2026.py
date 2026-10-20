"""Read original card cells and continuation signers in Topps Football 2026."""
import collections,hashlib,json,re,subprocess
from pathlib import Path
import pdfplumber
ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-flagship-football'
PARSER='scripts/import_topps_flagship_football_2026.py'
def read_cards(path):
 rows=[];subjects=[];source=[];section=None;raw=[]
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==44
  for pn,page in enumerate(pdf.pages,1):
   raw.append({'page':pn,'text':page.extract_text()});lines=collections.defaultdict(list)
   for c in page.chars:lines[round(c['top'],1)].append(c)
   for y,chars in sorted(lines.items()):
    if pn==1 and y<75:continue
    number=''.join(c['text'] for c in chars if c['x0']<172).strip();text=''.join(c['text'] for c in chars).strip()
    is_number=bool(re.fullmatch(r'\d+[A-Z]?|[A-Z0-9]+[-–][A-Z0-9-]+',number))
    continuation=not number and any(abs(c['x0']-173.06)<.03 for c in chars)
    if is_number or continuation:
     starts=[]
     for col,x in [(1,173.06),(2,248.33),(3,331.87)]:
      indices=[i for i,c in enumerate(chars) if abs(c['x0']-x)<.03]
      if indices:starts.append((min(indices) if col==3 else max(indices),col))
     assert starts and starts[0][1]==1,(pn,y,'Missing name origin',text)
     cols=[number,'','','']
     for j,(idx,col) in enumerate(starts):
      end=starts[j+1][0] if j+1<len(starts) else len(chars);piece=chars[idx:end];parts=[];previous=None
      for c in piece:
       if col==3 and previous is not None and (c['x0']<previous['x0']-1 or c['x0']>previous['x1']+1):parts.append(' ')
       parts.append(c['text']);previous=c
      cols[col]=' '.join(''.join(parts).split())
     assert section and cols[1] and cols[3] in ['', 'Rookie', 'Silver Pack Auto', 'Rookie Silver Pack Auto'],(pn,y,cols)
     source.append([section,*cols,str(pn)])
     sub={'Name':cols[1],'Team':cols[2],'Published annotation':cols[3],'Source page':str(pn),'Printed card number':number}
     if number:rows.append([section,number,cols[1],cols[2],cols[3],str(pn)]);subjects.append([sub])
     else:
      assert rows and rows[-1][0]==section,(pn,y,'Unattached continuation',cols)
      subjects[-1].append(sub);rows[-1][2]+=' / '+cols[1];rows[-1][3]+=' / '+cols[2]
    elif text:
     assert text==text.upper() and re.search('[A-Z]',text),(pn,y,'Unclassified line',text)
     if text not in ['BASE','INSERTS','AUTOGRAPHS','RELICS','AUTOGRAPH RELICS']:section=text
 assert len(rows)==4082 and len(source)==4171 and sum(len(s)-1 for s in subjects)==89
 assert len({r[0] for r in rows})==87
 for row,ss in zip(rows,subjects):
  note=' / '.join(s['Published annotation'] for s in ss if s['Published annotation'])
  # The filter flag is copied only for an individually identified subject.
  # Multi-subject annotations remain in the full original subject records.
  rookie='Rookie' if len(ss)==1 and re.search(r'\bRookie\b',ss[0]['Published annotation']) else ''
  row[:]=[row[0],row[1],row[2],row[3],rookie,note,json.dumps(ss,ensure_ascii=False),row[-1]]
 return rows,subjects,source,raw

def build():
 catalog_path=ROOT/'data/set-catalog.json';catalog=json.loads(catalog_path.read_text());record=next(r for r in catalog['sets'] if r['slug']==SLUG)
 path=ROOT/'data/catalog-sources/downloads'/f'{SLUG}.pdf'
 subprocess.run(['curl','-sLf','--retry','2','--max-time','30',record['checklistUrl'],'-o',str(path)],check=True)
 rows,subjects,source,raw=read_cards(path);data_path=ROOT/record['tableData'];data=json.loads(data_path.read_text())
 data.update(headers=['Checklist section','Card number','Name','Team','Rookie','Published annotation','Published subjects','Source page'],rows=rows,rowTeams=[list(dict.fromkeys(s['Team'] for s in ss if s['Team'])) for ss in subjects],originalSubjectHeaders=['Checklist section','Card number','Name','Team','Published annotation','Source page'],originalSubjectRows=source,rawPages=raw,unclassifiedLines=[],sha256=hashlib.sha256(path.read_bytes()).hexdigest(),importKind='topps-grid-pdf',dedicatedParser=PARSER,sectionColumn=0)
 base_families=['BASE CARDS I','FUTURE STARS','TEAM CARDS','LEAGUE LEADERS','COMBO CARDS','ROOKIES']
 for odd in data['odds']:
  if odd['name']=='Base Cards Base' or odd['name'].startswith('Base Cards ') and not any(term in odd['name'] for term in ['Autograph','Golden Mirror','Variation']):
   odd.update(family='BASE CARDS I',familyAliases=base_families[1:],familyBase=odd['name']=='Base Cards Base')
 data_path.write_text(json.dumps(data,ensure_ascii=False)+'\n')
 record.update(rowCount=4082,sections=87,importKind=data['importKind'],dedicatedParser=PARSER,sha256=data['sha256'],dataAudit='All 4,171 printed subject rows imported as 4,082 numbered rows across 87 sections; 89 blank-number signer continuations stay attached to their cards. Original names, teams, rookie annotations and Silver Pack Auto notes retained. Repeated printed numbers are preserved; individual parallel eligibility is not inferred.')
 for name in ['set-catalog.json','topps-product-official-catalog.json']:
  p=ROOT/'data'/name;c=json.loads(p.read_text());items=c['sets'] if isinstance(c,dict) else c;found=False
  for i,r in enumerate(items):
   if r['slug']==SLUG:items[i]=record;found=True
  if not found:items.append(record)
  p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 print('Imported 4082 numbered rows, all 4171 published subjects and 89 attached signer continuations.')
 from import_topps_flagship_london_specs_2026 import apply_specs
 apply_specs()
if __name__=='__main__':build()
