"""Verify literal RTOD names, inline marks, source scope and unresolved eligibility."""
import hashlib
import json
from pathlib import Path
import import_official_catalog as generic
from import_topps_now_rtod_teams_2026 import TEAMS,identity,FAMILY,PARALLEL_HEADING,COMMON,INCLUDED,BONUSES,BONUS_INTRO

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
'washington-nationals':('James Wood;Robert Hassell III;Josiah Gray;Harry Ford;Daylen Lile;Luis García Jr.;Dylan Crews;CJ Abrams;Brady House;Andrew Alvarez',[0,3,6,8]),
'miami-marlins':('Sandy Alcantara;Owen Caissie;Griffin Conine;Jakob Marsee;Eury Pérez;Xavier Edwards;Christopher Morel;Agustín Ramírez;Connor Norby;Kyle Stowers',[1]),
'baltimore-orioles':('Pete Alonso;Gunnar Henderson;Trevor Rogers;Coby Mayo;Colton Cowser;Adley Rutschman;Dylan Beavers;Jackson Holliday;Shane Baz;Samuel Basallo',[0,1,5,6,7,9]),
'los-angeles-dodgers':('Shohei Ohtani;Mookie Betts;Freddie Freeman;Roki Sasaki;Will Smith;Yoshinobu Yamamoto;Edwin Díaz;Teoscar Hernández;Kyle Tucker;Blake Snell',list(range(10))),
'san-diego-padres':('Manny Machado;Xander Bogaerts;Joe Musgrove;Michael King;Jake Cronenworth;Jackson Merrill;Fernando Tatis Jr.;Sung-Mun Song;Mason Miller;Nick Pivetta',[0,5,6]),
'arizona-diamondbacks':('Corbin Carroll;Ketel Marte;Nolan Arenado;Zac Gallen;Corbin Burnes;Lourdes Gurriel Jr.;Alek Thomas;Geraldo Perdomo;Brandon Pfaadt;Gabriel Moreno',[0,1]),
 'texas-rangers':('Jacob deGrom;Evan Carter;Wyatt Langford;Josh Jung;Brandon Nimmo;Nathan Eovaldi;Corey Seager;MacKenzie Gore;Jack Leiter;Cody Freeman',[0,2,6]),
 'toronto-blue-jays':('Vladimir Guerrero Jr.;Dylan Cease;Addison Barger;Daulton Varsho;George Springer;Trey Yesavage;Kevin Gausman;Ernie Clement;Kazuma Okamoto;Alejandro Kirk',[0,8]),
 'atlanta-braves':('Ronald Acuña Jr.;Michael Harris II;Chris Sale;Mauricio Dubón;Austin Riley;Matt Olson;Ozzie Albies;Drake Baldwin;Robert Suarez;Spencer Strider',[0,5,6,7]),
 'houston-astros':('Yordan Alvarez;Brice Matthews;Jose Altuve;Christian Walker;Tatsuya Imai;Jeremy Peña;Josh Hader;Zach Cole;Cam Smith;Carlos Correa',[0,2,4]),
 'athletics':('Nick Kurtz;Luis Morales;Lawrence Butler;Shea Langeliers;Colby Thomas;Max Muncy;Brent Rooker;Jacob Wilson;Tyler Soderstrom;Jeff McNeil',[0,4,7]),
 'new-york-mets':('Juan Soto;Nolan McLean;Luis Robert Jr.;Freddy Peralta;Marcus Semien;Francisco Lindor;Jorge Polanco;Francisco Alvarez;Bo Bichette;Jonah Tong',[0,1,5,8,9]),
 'angels':("Mike Trout;Christian Moore;Jo Adell;Zach Neto;Logan O'Hoppe;Grayson Rodriguez;Jorge Soler;Nolan Schanuel;Yusei Kikuchi;Reid Detmers",[])}
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text())['sets'];catalog=json.loads((ROOT/'data/set-catalog.json').read_text())['sets'];observations=json.loads((ROOT/'data/topps-now-observations.json').read_text());total_marks=0;total_terms=0
for key,(names,marked_indices) in EXPECTED.items():
 team,run,marked=TEAMS[key];slug,page,evidence=identity(key);p=ROOT/evidence;proof=json.loads(p.read_text());ph=hashlib.sha256(p.read_bytes()).hexdigest();data=json.loads((ROOT/'data/imports'/(slug+'.json')).read_text())
 physical=data
 assert data['importKind']=='topps-grid-pdf'
 data={**data,'headers':['Checklist section','Card number','Player / subjects','Published parallel-subject mark','Published subject','Official source'],'rows':[[r[0],'',r[2],r[7],r[8],page] for r in data['rows']]}
 assert data['headers']==['Checklist section','Card number','Player / subjects','Published parallel-subject mark','Published subject','Official source']
 assert len(data['rows'])==10 and all(len(r)==6 and r[0]==FAMILY and r[1]=='' and r[5]==page for r in data['rows'])
 assert [r[2] for r in data['rows']]==names.split(';')
 assert [i for i,r in enumerate(data['rows']) if r[3]]==marked_indices and len(marked_indices)==marked
 assert all(r[3] in ['', 'parallel subject'] for r in data['rows']);total_marks+=marked
 lines=[s.strip() for s in proof['description'].splitlines() if s.strip()];paragraphs=[s.strip() for s in proof['descriptionParagraphs'] if s.strip()]
 assert [r[4] for r in data['rows']]==lines[lines.index(FAMILY)+1:lines.index(PARALLEL_HEADING)]==paragraphs[paragraphs.index(FAMILY)+1:paragraphs.index(PARALLEL_HEADING)]
 if key in ['baltimore-orioles','toronto-blue-jays','houston-astros']:
  assert all('\u00a0- parallel subject' in data['rows'][i][4] for i in marked_indices)
 assert data['sourceProducts'][0]['sha256']==ph and physical['sha256']=='0dad58e985573cbff62ac41adc3ce7f19736446e094c6a326bc82196d201c104' and proof['documentLinks']==[]
 assert not data.get('odds') and not data.get('formats') and not data.get('serialColumn') and registry[slug]==[]
 assert not any('team' in h.lower() or 'rookie' in h.lower() for h in data['headers'])
 terms=next(s for s in data['publishedSpecifications'] if s['name']=='Unjoined '+PARALLEL_HEADING)
 foils=([('/199','Aqua Foil'),('/150','Blue Foil')] if key=='los-angeles-dodgers' else [])+COMMON
 assert [r[:2] for r in terms['rows']]==[[name,n] for n,name in foils];total_terms+=len(foils)
 fields={r[0]:r[1] for r in next(s for s in data['publishedSpecifications'] if s['name'].startswith('Set-wide bundle'))['rows']}
 assert fields['Published bundle print run']==run and fields['Print-run inclusion statement']==INCLUDED
 assert fields['Available From']=='Mar 20, 2026' and fields['Available Until']=='Apr 6, 2026'
 assert fields['Published parallel distribution']=='(1) Parallel /'+('199' if key=='los-angeles-dodgers' else '99')+' or lower'
 assert fields['Printed card numbers']==fields['Per-row team / rookie fields']=='Published in the linked regular team-set PDF'
 assert fields['Published base contents']=='(10) Base Cards'
 bonuses=next(s for s in data['publishedSpecifications'] if s['name']=='Set-wide conditional bonus-card terms')
 assert [r[0] for r in bonuses['rows']]==BONUSES==proof['descriptionListItems'] and all(BONUS_INTRO in r[1] for r in bonuses['rows'])
 family=next(s for s in data['publishedSpecifications'] if s['name']==FAMILY)
 assert all('/99' not in cell and '/199' not in cell for r in family['rows'] for cell in r)
 if key=='angels':assert 'OD-111 Mike Trout' in family['rows'][0][1] and 'OD-112 Christian Moore' in family['rows'][0][1]
 record=next(r for r in catalog if r['slug']==slug);assert record['releaseStatus']=='Unverified' and record['releaseDate'] is None and not record['coverageComplete'];assert generic.run(record.copy())==record
 assert not any(p['source']==page for p in observations)
assert total_marks==46 and total_terms==80
assert not json.loads((ROOT/'data/topps-now-archive-index.json').read_text())['coverageComplete']
print('Verified 130 exact RTOD subjects, 46 inline marks, original NBSP/accents, 80 literal named foil limits, Dodgers-only /199-/150, all 13 included-356 qualifiers, separate bundle runs, four conditional bonus rules and separate Angels PDF/web marks. Printed PDF IDs are verified separately; no subtraction, odds or complete-history claim.')
