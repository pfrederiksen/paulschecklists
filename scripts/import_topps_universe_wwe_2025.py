"""Reconcile Universe WWE's overlapping original Name/Designation/Rookie cells."""
import collections, hashlib, json, re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire, text

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2025-topps-universe-wwe'
PARSER='scripts/import_topps_universe_wwe_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/universe-wwe-2025-physical-20261017.json'
HEADERS=['Checklist section','Card number','Name','Source page','Published designation (source column 3)','Rookie']
FAMILIES={'BASE CARDS I':100,'BASE CARDS II':100,'BASE CARDS EVENT VARIATION':100,'RING LEADERS':30,
 'STAR PORTAL':25,'INTERNATIONAL IMPACT':20,'DAZZLING DEBUTS':20,'FOREVER FACTIONS':5,'RAGE':30,'NAMESAKES':40,
 'FOREIGN OBJECTS':20,'REMARKABLE RETURNS':10,'WWE THEN':5,'WWE NOW':20,'WWE FOREVER':5,'WWE TOGETHER':20,
 'MASKED':10,'UNIVERSE AUTOGRAPHS':43,'LEGENDS AUTOGRAPHS':30,'NEXT LEVEL AUTOGRAPHS':19,
 'CELEBRATING CENA AUTOGRAPHS':4,'THE ROCK RETROSPECTIVE AUTOGRAPHS':1,'TRIPLE H TRIBUTE AUTOGRAPHS':3,
 'SUPERSTAR RIVALRY SIGNATURES':2,'SUPERSTAR RELIC SIGNATURES':31,'WORLDWIDE RELIC AUTOGRAPHS':17,
 'TAG TEAM RELIC AUTOGRAPHS':32,'TITLE MARKS RELIC AUTOGRAPHS':15,'UNIVERSE RELICS':33,
 'TRIPLE SUPERSTAR RELICS':15,'WWE AUTHENTICS':21,'RINGSIDE RELICS':20}

def read_cards(path):
 rows=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==18
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    line=text(cs)
    if all('Bold' in c['fontname'] for c in cs):
     if line in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPH RELIC','RELIC'}:notes.append([str(pn),line])
     else:
      assert line in FAMILIES,(pn,line);family=line
     continue
    # Preserve drawing order: long Name objects overlap Designation glyphs.
    # Spatially sorting all characters would interleave Cody Rhodes and others.
    a=next(i for i,c in enumerate(cs) if abs(c['x0']-132.62)<.02)
    b=next(i for i,c in enumerate(cs) if abs(c['x0']-269.45)<.02)
    k=next((i for i,c in enumerate(cs) if abs(c['x0']-421.27)<.02),len(cs))
    number,name,designation,rookie=[text(part) for part in [cs[:a],cs[a:b],cs[b:k],cs[k:]]]
    assert family and re.fullmatch(r'\d+|[A-Z]+-[A-Za-z0-9]+',number) and name,(pn,line)
    assert designation in {'Raw','Smackdown','NXT','Legend','Legends','WWE'} and rookie in {'','Rookie'},(pn,line)
    rows.append([family,number,name,str(pn),designation,rookie])
 assert len(rows)==846 and len({tuple(r[:2]) for r in rows})==820
 assert collections.Counter(r[0] for r in rows)==FAMILIES and sum(r[5]=='Rookie' for r in rows)==2
 return rows,raw,notes

def build():
 proof=json.loads(PROOF.read_text());sources=proof['sources']
 evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
 dp=ROOT/record['tableData'];data=json.loads(dp.read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
 sha=acquire(proof['checklistUrl'],path);assert sha==proof['checklistSha256']
 rows,raw,notes=read_cards(path)
 def table(name,headers,values,source):return dict(name=name,headers=headers,rows=values,source=source,worksheet='Official U.S. product / collector guide; preserve source units and scope',**evidence)
 published=[table('Official Hobby box configuration',['Published item','Published value','Unit / scope'],proof['hobbyConfiguration'],sources['formatGuide']),
  table('Official Hobby case configuration',['Published item','Published value','Unit / scope'],proof['spotlightConfiguration'],sources['spotlight']),
  table('Official Value box configuration',['Published item','Published value','Unit / scope'],proof['valueConfiguration'],sources['formatGuide']),
  table('Official Hobby case contents',['Published item','Published value','Qualification'],proof['caseConfiguration'],sources['formatGuide']),
  table('Official product metadata',['Published field','Published value','Qualification'],proof['productMetadata'],sources['product']),
  table('Official parallel and format context',['Parallel / variation','Published statement','Qualification'],proof['parallelContext'],sources['formatGuide'])]
 note=('All 846 physical subject rows / 820 family-card identities across 32 sections retain separate original Name/Designation/Rookie cells. '
  'The three base programs retain 100 numbers each (1–100, 101–200 and 201–300); 16 Tag Team relic cards retain both signers, including TTA-ANF across pages 15–16. '
  'Only Zaria 109 and Jordynne Grace 118 have printed Rookie marks; no flags are inferred for other cards. '
  'Original Raw, Smackdown, NXT, Legend, Legends and WWE designations are not teams. '
  'Long names are preserved from their original text objects without interleaving designation glyphs. '
  'Official Hobby/Value box and case distributions retain their units and do not establish pack odds or numeric serial limits. '
  'The 2025 product page and two official guides supply no verified 2025 pack-odds link; the current Universe landing page describes 2026, whose odds cannot fill this gap. '
  'The verified February 27, 2026 release remains distinct from product year 2025. Exhaustive parallel numbering remains unverified.')
 data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,
  unclassifiedLines=[],source=proof['checklistUrl'],sha256=sha,dedicatedParser=PARSER,importKind='pdf',coverageComplete=True,sectionColumn=0,
  odds=[],formats=[],formatNamesPublished=False,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=published,
  sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
 record.update(sourcePage=sources['product'],rowCount=846,sections=32,sha256=sha,dedicatedParser=PARSER,coverageComplete=True,
  verified=proof['observed'],dataAudit=note,catalogEvidence=note,
  sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=sources['product']))
 cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text())
 inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record]
 ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text())
 registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Remaining 2025 odds and parallel numbering',gap=' '.join(proof['remainingGaps']),source=sources['formatGuide'],**evidence)]
 rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('2025 Universe WWE: 846 subjects / 820 identities, 32 sections, two Rookie marks, 16 complete Tag Team duals; published box/case units remain separate from unverified pack odds and serial limits.')

if __name__=='__main__':build()
