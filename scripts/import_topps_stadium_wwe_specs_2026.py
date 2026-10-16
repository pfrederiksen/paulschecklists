"""Reapply verified WWE guide statements after the physical checklist refresh."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-stadium-club-wwe';PARSER='scripts/import_topps_stadium_wwe_2026.py'
PROOF=ROOT/'data/parallel-audit-sources/stadium-club-wwe-2026-20261016.json'
UNJOINED='Base Chrome Autographs II / repeated captions (roster join unverified)'
def supplement(data):
 proof=json.loads(PROOF.read_text());sources=proof['sources'];evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
 assert data['sha256']==proof['checklistSha256'] and data['oddsSha256']==proof['oddsSha256'],'Source revision requires physical and guide reconciliation'
 assert len(data['rows'])==938 and len(data['odds'])==122
 families=set(r[0] for r in data['rows']);aliases={f:f for f in families};aliases.update({'Base':'BASE CARDS','Chrome Base':'CHROME BASE CARDS','Base Card Autographs':'BASE CARDS AUTOGRAPH VARIATION','Base Card Autographs II':'BASE CARDS AUTOGRAPH VARIATION II','Base Chrome Autographs':'BASE CARDS CHROME AUTOGRAPH VARIATION'})
 original=data['odds'];odds=[];counts={}
 for item in original:
  name=item['name'];counts[name]=counts.get(name,0)+1
  # These captions are printed twice; the latter instances follow an
  # unmatched II program. Do not silently attach them to the first roster.
  if name.startswith('Base Chrome Autographs II') or name in {'Base Chrome Autographs Orange','Base Chrome Autographs Superfractor'} and counts[name]>1:
   odds.append(dict(item,family=UNJOINED));continue
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if name.casefold()==a.casefold() or name.casefold().startswith(a.casefold()+' ')),None);assert prefix,name
  odds.append(dict(item,family=aliases[prefix],familyBase=name.casefold()==prefix.casefold()))
 assert sum(o['family']==UNJOINED for o in odds)==5
 note=('All 938 original subjects, 25 sections and 35 literal Rookie marks are retained. Published WWE designations remain separate from teams. '
       'All 122 odds rows and three SKU columns remain literal, including five unjoined Chrome Autographs II/repeated-caption rows with no verified roster join. '
       'The sheet names SKU formats but no ratio unit; 5:1 remains as printed without a per-pack estimate. '
       'Exact approved guide joins include Base Card Autographs Gold /50, the named Inked/Main Stage/Aftermath Purple /25 and Green /5 parallels, three named Gold Rainbow Foilboard 1/1 programs and the first Base Chrome Superfractor 1/1. '
       'Guide-only Base Chrome Pearl White /30 and Gold Minted have no published matching odds row; serial limits for other colors are not inferred. '
       'Jey Uso and Charlotte Flair/Alexa Bliss examples remain card-specific. Ambiguous Concentration/Gold wording and the rest of the numbering audit remain explicit. '
       'The October 16 guide confirms the scheduled October 23 release; the set remains Upcoming.')
 specs=[dict(name=t['name'],worksheet='Official WWE guides',headers=t['headers'],rows=t['rows'],source=sources[t['sourceKey']],**evidence) for t in proof['tables']]
 data.update(odds=odds,officialOddsTable=original,officialOddsFormats=data['formats'],officialOddsHeader=['Subset',*data['formats']],formatNamesPublished=True,oddsUnitsPublished=False,originalSubjectHeaders=data['headers'],originalSubjectRows=data['rows'],dedicatedParser=PARSER,coverageComplete=True,parallelSpecifications=[],publishedSpecifications=specs,sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=[dict(**{k:v for k,v in entry.items() if k!='sourceKey'},source=sources[entry['sourceKey']],**evidence) for entry in proof['approvedSpecifications']];registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Unjoined Chrome II roster, guide-only categories and qualified numbering',gap=' '.join(proof['remainingGaps']),source=sources['guide'],**evidence)];rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 return data,dict(proof,**evidence)
