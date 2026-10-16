"""Reconcile Chrome Disney using original clipping cells and glyph draw order."""
import collections,hashlib,json,logging,re
from pathlib import Path
import pdfplumber
from pypdf import PdfReader
from import_topps_tribute_2026 import acquire,text
from official_odds_layout import physical_odds_pdf
logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-disney'
PARSER='scripts/import_topps_disney_chrome_2026.py';PROOF=ROOT/'data/parallel-audit-sources/disney-chrome-2026-20261015.json'
HEADERS=['Checklist section','Card number','Player / subjects','Source page','Character','Subject','Property','First Name','Last Name','Character Name','Official unlabelled annotation','Official text column 1','Official text column 2','Artist Name']
FAMILIES={'DISNEY CHROME FACSIMILE TRIPLE AUTOGRAPHS', 'CARS AUTHENTIC AUTOGRAPHS', 'THE ONE AND ONLY WALT', 'THE ONE AND ONLY', 'SKETCH CARDS', 'DARKWING DUCK 35TH ANNIVERSARY', 'DUMBO 85TH ANNIVERSARY', 'WINNIE THE POOH 100TH ANNIVERSARY', 'DISNEY DUAL AUTOGRAPHS', 'DISNEY PRINCESS AUTOGRAPHS', 'TRON TEK', 'DISNEY CHANNEL', 'DISNEY CHROME FACSIMILE DUAL AUTOGRAPHS', 'ALICE IN WONDERLAND 75TH ANNIVERSARY', 'CARS 20TH ANNIVERSARY', 'DISNEY CHANNEL AUTOGRAPH VARIATION', 'ICONIC MOMENTS', 'FUTURE STARS', 'MOANA 10TH ANNIVERSARY', 'AUTHENTIC AUTOGRAPHS', 'DISNEY INK AND PAINT', 'DISNEY QUAD AUTOGRAPHS', 'THE HEART OF TE FITI SHADOWBOX', 'THE ROSE SHADOWBOX', 'HELIX', 'DISNEY CHROME FACSIMILE QUAD AUTOGRAPHS', 'TOY STORY 5 FIRST EDITION', 'MONSTERS, INC. 25TH ANNIVERSARY', 'DISNEY TRIPLE AUTOGRAPHS', 'DISNEY CHROME FACSIMILE AUTOGRAPHS', 'SCORCHED', 'DISNEY REFLECTIONS', 'LILO & STITCH SHADOWBOX', 'SUPER STRENGTH CHROME', 'BASE CARD IMAGE VARIATIONS', 'MICKEY AND FRIENDS UKIYO-E', 'HIGH SCHOOL MUSICAL 20TH ANNIVERSARY', 'ART OF DISNEY', 'BASE CARDS', 'DISNEY & PIXAR STUDIO ARTIST SKETCH CARDS', 'GOLDEN AGE POSTERS', 'MICKEY AND FRIENDS MLB HOME JERSEY SET'}

def read_cards(path):
  result=[];raw=[];notes=[];family="BASE CARDS";reader=PdfReader(path)
  with pdfplumber.open(path) as pdf:
   assert len(pdf.pages)==20
   for pn,page in enumerate(pdf.pages,1):
    raw.append(dict(page=pn,text=page.extract_text()))
    state={'clip':None,'pending':None};stack=[];objects=[]
    def b(op,args,cm,tm):
     if op==b'q':stack.append(state.copy())
     elif op==b'Q':state.clear();state.update(stack.pop())
     elif op==b're':
      assert abs(cm[1])+abs(cm[2])<.001 and cm[0]>0 and cm[3]>0,'Changed PDF transform needs reconciliation'
      x,y,w,h=map(float,args);state['pending']=(x*cm[0]+cm[4],y*cm[3]+cm[5],(x+w)*cm[0]+cm[4],(y+h)*cm[3]+cm[5])
     elif op in {b'W',b'W*'}:state['clip']=state['pending']
    def v(t,cm,tm,f,sz):
     if t.strip():objects.append((tm[4]*cm[0]+cm[4],tm[5]*cm[3]+cm[5],state['clip'],t))
    reader.pages[pn-1].extract_text(visitor_text=v,visitor_operand_before=b)
    groups=collections.defaultdict(list)
    for c in page.chars:groups[round(c['matrix'][5],1)].append(c)
    cells=collections.defaultdict(list)
    # Original object origins identify cell starts even when long text crosses
    # the next column. Keep glyph draw order; x-sorting merges adjacent names.
    for y,cs in sorted(groups.items(),reverse=True):
     if not text(cs):continue
     obs=[o for o in objects if abs(o[1]-y)<.06];anchors={}
     for x,by,clip,t in obs:
      matches=[i for i,c in enumerate(cs) if abs(c['matrix'][4]-x)<.03]
      assert matches,(pn,y,x,t)
      anchors[max(matches)]=clip
     assert anchors,(pn,y,text(cs),[o for o in objects if abs(o[1]-y)<2]);assert min(anchors)==0,(pn,y,text(cs))
     starts=sorted(anchors)
     for start,end in zip(starts,starts[1:]+[len(cs)]):
      clip=anchors[start]
      cells[clip].extend(cs[start:end])
    rows=collections.defaultdict(dict)
    numberboxes=[box for box in cells if box and box[0]==72]
    # Wrapped captions and properties share the number cell's clipping box.
    # This also merges tiny nested trademark clips without duplicating glyphs.
    for box,cs in cells.items():
     if box is None:continue
     if box[0]==72:target=box
     else:
      matches=[b for b in numberboxes if b[1]-.01<=min(c['matrix'][5] for c in cs) and max(c['matrix'][5] for c in cs)<=b[3]+.01]
      assert len(matches)==1,(pn,box,text(cs),matches)
      target=matches[0]
     col=box[0]
     rows[target].setdefault(col,[]).extend(cs)
    if None in cells:notes.append([str(pn),text(cells[None])])
    for box,cols in sorted(rows.items(),key=lambda pair:pair[0][3],reverse=True):
      values={}
      for x,cs in sorted(cols.items()):
        lines=collections.defaultdict(list)
        for c in cs:lines[round(c['matrix'][5],1)].append(c)
        values[x]=' '.join(text(line) for y,line in sorted(lines.items(),reverse=True))
      number=values[72.]
      if number in {'Card Number','Artist Name'}:continue
      if number in FAMILIES:
        assert len(values)==1,(pn,values)
        family=number;continue
      row=[family,'','',str(pn)]+['']*10
      if 14<=pn<=16:
        assert len(values)==1
        row[2]=row[13]=number
      else:
        assert re.fullmatch(r'\d+|[A-Z0-9&]+-[A-Z0-9]+',number),(pn,values)
        row[1]=number
        if pn<=5:
          row[2]=row[4]=values[140.];row[6]=values.get(310.,'');row[10]=values.get(540.,'')
        elif pn<=12:
          row[2]=row[5]=values.get(144.,values.get(149.,''));row[6]=values.get(369.,'')
        elif pn==13:
          row[2]=row[5]=values[190.];row[11]=values[342.];row[12]=values[512.]
        else:
          row[7]=values.get(139.,'');row[8]=values.get(247.,'');row[9]=values.get(339.,'');row[6]=values.get(447.,values.get(454.,''));row[2]=' '.join([row[7],row[8]]).strip()
        assert row[2],(pn,values)
      result.append(row)
  assert {r[0] for r in result}==FAMILIES
  return result,raw,notes

def build():
  proof=json.loads(PROOF.read_text());ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();evidence=dict(source=proof['productSource'],evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
  cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
  path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
  op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);odds,formats,odds_raw,issues=physical_odds_pdf(op)
  assert digest==proof['checklistSha256'] and oh==proof['oddsSha256'] and not issues
  assert len(rows)==741 and sum(bool(r[1]) for r in rows)==640 and len(odds)==210 and len(formats)==7
  aliases={f.title():f for f in FAMILIES}
  aliases.update({'Base':'BASE CARDS','Base Card':'BASE CARDS','Mickey & Friends MLB Home Jersey Set':'MICKEY AND FRIENDS MLB HOME JERSEY SET','Lilo and Stitch':'LILO & STITCH SHADOWBOX','The Rose':'THE ROSE SHADOWBOX','The Heart of Te Fiti':'THE HEART OF TE FITI SHADOWBOX','Facsimile Autographs':'DISNEY CHROME FACSIMILE AUTOGRAPHS','Dual Facsimile Autographs':'DISNEY CHROME FACSIMILE DUAL AUTOGRAPHS','Triple Facsimile Autographs':'DISNEY CHROME FACSIMILE TRIPLE AUTOGRAPHS','Quad Facsimile Autographs':'DISNEY CHROME FACSIMILE QUAD AUTOGRAPHS','Disney Princesses Autographs':'DISNEY PRINCESS AUTOGRAPHS','Disney Interal Artists Sketch':'DISNEY & PIXAR STUDIO ARTIST SKETCH CARDS','Pixar Interal Artists Sketch':'DISNEY & PIXAR STUDIO ARTIST SKETCH CARDS'})
  for odd in odds:
    prefix=next((a for a in sorted(aliases,key=len,reverse=True) if odd['name'].casefold()==a.casefold() or odd['name'].casefold().startswith(a.casefold()+' ')),None)
    assert prefix,odd['name'];odd.update(family=aliases[prefix],familyBase=odd['name'].casefold()==prefix.casefold())
  note=('All 640 numbered subject rows / 582 family-card identities and 101 unnumbered artists across 42 sections are reconciled from original clipping cells and glyph drawing order. '
        'All 200 base cards, the ten Disney Ink and Paint cards, complete wrapped IM-9 caption, DCA-VH, AA-JV and final TR-BLS signer are retained. '
        'Character/Subject/Property and autograph First Name/Last Name/Character Name cells stay separate; 20 literal DEBUT annotations are not rookie flags. '
        'All 210 odds categories and seven exact columns remain intact. Ratio units are unstated; guide numbering is card-specific and no universal color ladder is inferred. '
        'The combined studio artist roster cannot allocate Disney/Pixar odds to individual artists. The verified June 17 release date is preserved; exhaustive parallel numbering remains incomplete.')
  data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,dedicatedParser=PARSER,coverageComplete=True,importKind='pdf',sectionColumn=0,odds=odds,formats=formats,oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser='scripts/official_odds_layout.py',formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=[dict(name='Manufacturer product fields',worksheet='Official landing page; published artwork uniqueness is not artist-roster numbering',headers=['Published field','Published value','Scope'],rows=proof['productFields'],**evidence),dict(name='Manufacturer guide qualifications',worksheet='Card-specific examples do not establish family-wide numbering',headers=['Published field','Published value','Scope'],rows=proof['guideFields'],**{**evidence,'source':proof['guideSource']}),dict(name='Regional manufacturer product fields',worksheet='Japanese store; configuration is not pack odds',headers=['Published field','Published value','Scope'],rows=proof['regionalFields'],**{**evidence,'source':proof['regionalProductSource']})],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
  dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=proof['productSource'],rowCount=len(rows),sections=42,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=210,formats=7,verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser=data['oddsParser'],oddsImportIssues=0,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=proof['productSource']));cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
  ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());ip.write_text(json.dumps([r for r in inventory if r['slug']!=SLUG]+[record],ensure_ascii=False,indent=2)+'\n')
  rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=[];registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG];registry['conflicts'].append(dict(slug=SLUG,family='Card-specific guide numbering, combined artist roster and odds units',gap=' '.join(proof['remainingGaps']),**evidence));rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
  print('Chrome Disney: 640 numbered subject rows / 582 identities, 101 artists, 42 sections and all 210 literal odds / seven formats. Verified June 17 release retained; card-specific guide numbering stays qualified.')

if __name__=='__main__':build()
