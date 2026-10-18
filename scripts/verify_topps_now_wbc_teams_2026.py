"""Verify all literal WBC team-set names, memberships and isolated bundle facts."""
import hashlib
import json
from pathlib import Path
import import_official_catalog as generic
from import_topps_now_wbc_teams_2026 import TEAMS,identity,PARALLEL,AUTO,FOILS,LOGO

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
'united-states':[
'Aaron Judge;Cal Raleigh;Kyle Schwarber;Bobby Witt Jr.;Gunnar Henderson;Clayton Kershaw;Paul Skenes;Pete Crow-Armstrong;Byron Buxton;Tarik Skubal;Bryce Harper;Roman Anthony',
'Aaron Judge;Cal Raleigh;Kyle Schwarber;Bobby Witt Jr.;Gunnar Henderson;Clayton Kershaw;Paul Skenes;Pete Crow-Armstrong;Byron Buxton;Tarik Skubal;Bryce Harper;Roman Anthony',
'Aaron Judge;Gunnar Henderson;Clayton Kershaw;Paul Skenes'],
'venezuela':[
'Ronald Acuña Jr.;Luis Arraez;William Contreras;Jackson Chourio;Salvador Perez;Eugenio Suárez;Willson Contreras;Wilyer Abreu;Gleyber Torres;Maikel Garcia;Miguel Cabrera;Johan Santana',
'Ronald Acuña Jr.;Jackson Chourio;Miguel Cabrera',
'Ronald Acuña Jr.;Jackson Chourio;Miguel Cabrera'],
'dominican-republic':[
'Juan Soto;Junior Caminero;Ketel Marte;Oneil Cruz;Vladimir Guerrero Jr.;Julio Rodríguez;Jeremy Peña;Fernando Tatis Jr.;Sandy Alcantara;Geraldo Perdomo;Manny Machado;Albert Pujols',
'Juan Soto;Vladimir Guerrero Jr.;Fernando Tatis Jr.;Albert Pujols',
'Juan Soto;Vladimir Guerrero Jr.;Albert Pujols'],
'japan':[
'Shohei Ohtani;Seiya Suzuki;Yoshinobu Yamamoto;Munetaka Murakami;Kazuma Okamoto;Kensuke Kondo;Yusei Kikuchi;Tomoyuki Sugano;Hiromi Itoh;Masataka Yoshida;Shugo Maki;Kaito Kozono',
'Shohei Ohtani;Seiya Suzuki;Yoshinobu Yamamoto;Munetaka Murakami;Kazuma Okamoto;Kensuke Kondo;Yusei Kikuchi;Tomoyuki Sugano;Hiromi Itoh;Masataka Yoshida;Shugo Maki;Kaito Kozono',
'Shohei Ohtani;Yoshinobu Yamamoto;Munetaka Murakami;Kazuma Okamoto'],
'korea':[
'Jung Hoo Lee;Hyeseong Kim;Woo-Suk Go;Hyun Jin Ryu;Shay Whitcomb;Jahmai Jones;Dane Dunning;Do Yeong Kim;Hyun Min Ahn;Ju Won Kim',
'Jung Hoo Lee;Hyeseong Kim',
'Jung Hoo Lee']}
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text())['sets']
catalog=json.loads((ROOT/'data/set-catalog.json').read_text())['sets'];observations=json.loads((ROOT/'data/topps-now-observations.json').read_text());total=0
for key,rosters in EXPECTED.items():
 country,run,counts=TEAMS[key];slug,page,evidence=identity(key);p=ROOT/evidence;proof=json.loads(p.read_text());ph=hashlib.sha256(p.read_bytes()).hexdigest();data=json.loads((ROOT/'data/imports'/(slug+'.json')).read_text())
 families=['Team '+country+' Subject List:',PARALLEL,AUTO];expected=[[family,'',name,name,page] for family,names in zip(families,rosters) for name in names.split(';')]
 assert data['rows']==expected and len(expected)==sum(counts);total+=len(expected)
 assert data['headers']==['Checklist section','Card number','Player / subjects','Published subject','Official source']
 lines=[s.strip() for s in proof['description'].splitlines() if s.strip()];paragraphs=[s.strip() for s in proof['descriptionParagraphs'] if s.strip()]
 assert lines==paragraphs and lines[1:-1]==[cell for family,names in zip(families,rosters) for cell in [family,*names.split(';')]]
 assert data['source']==page and data['sha256']==ph and data['sourceProducts'][0]['sha256']==ph and proof['documentLinks']==[]
 assert proof['title']=='2026 Topps NOW® Baseball – Team '+country+' – World Baseball Classic Team Sets - PR: '+run
 assert not data.get('odds') and not data.get('formats') and not data.get('serialColumn') and registry[slug]==[]
 assert not any('team' in h.lower() or 'rookie' in h.lower() for h in data['headers'])
 terms=next(s for s in data['publishedSpecifications'] if s['name']=='Unjoined product foil and WBC Logo terms')
 assert [r[:2] for r in terms['rows']]==[['WBC Logo Parallel','Unnumbered'],*[[name,n] for name,n in FOILS]]
 for family,count in zip(families,counts):
  table=next(s for s in data['publishedSpecifications'] if s['name']==family);assert table['rows'][0][0]==str(count)+' separately published '+('subject' if count==1 else 'subjects');assert not any('/99' in cell or '/1' in cell for r in table['rows'] for cell in r)
 fields={r[0]:r[1] for r in next(s for s in data['publishedSpecifications'] if s['name'].startswith('Set-wide'))['rows']}
 assert fields['Published bundle print run']==run and fields['Available From']=='Mar 5, 2026' and fields['Available Until']=='Mar 16, 2026'
 assert fields['Printed card numbers']==fields['Team assignments / rookie flags']=='Not published'
 assert fields['Published bundle contents']==f'({counts[0]}) Base Cards PLUS (1) Guaranteed parallel or autograph parallel per set.'
 record=next(r for r in catalog if r['slug']==slug);assert record['releaseStatus']=='Unverified' and record['releaseDate'] is None and not record['coverageComplete'];assert generic.run(record.copy())==record
 assert not any(p['source']==page for p in observations)
assert total==106
champ=json.loads((ROOT/'data/imports/topps-bowman-2026-venezuela-wbc-championship-topps-now.json').read_text());fields={r[0]:r[1] for r in next(s for s in champ['publishedSpecifications'] if s['name'].startswith('Set-wide'))['rows']}
assert len(champ['rows'])==27 and fields['Published bundle print run']=='1084' and fields['Available From']=='Mar 18, 2026' and fields['Available Until']=='Mar 25, 2026'
assert not json.loads((ROOT/'data/topps-now-archive-index.json').read_text())['coverageComplete']
print('Verified all 106 literal WBC team entries and 15 exact rosters, seven qualified parallel terms per set, explicit unnumbered Logo, blank IDs, five separate bundle runs and March 5–16 sale windows. Venezuela championship facts remain distinct; no autograph ladder or complete-history claim.')
