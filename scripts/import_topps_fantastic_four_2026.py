"""Reconcile physical Fantastic Four subject cells and complete ruled odds."""
import collections
import hashlib
import json
import re
import urllib.request
from pathlib import Path

import pdfplumber
from official_odds_layout import physical_odds_pdf

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-finest-fantastic-four'
PARSER = 'scripts/import_topps_fantastic_four_2026.py'
PROOF = ROOT / 'data/parallel-audit-sources/fantastic-four-2026-guide-20261015.json'
FAMILIES = {
    'BASE CARDS COMMON', 'BASE CARDS UNCOMMON', 'BASE CARDS RARE',
    '1960s BLACKLIGHT BASE VARIATION', 'NEGATIVE ZONE BASE VARIATION', 'TRIBUTE TO FINEST ‘96',
    'FIRST FAMILY', 'CLOBBERIN’ TIME', 'SCREEN MOMENTS', 'WORLD’S GREATEST COMIC MAGAZINES',
    'THE FANTASTIC FOUR: FIRST STEPS CONCEPT ART', 'ADVERSARIES', 'FLAME THROWERS VARIANTS',
    'ROCK STARS VARIANTS', 'FINEST TIMELINES', 'DECADES POSTERS', 'FANTASTIC SCIENCE', 'POWER HOUR',
    'FUTURE FOUNDATION ID CARDS', 'ALL FOR FOUR', 'ASTONISHING', 'TOPPS ORIGINALS',
    'FANTASTIC CREATORS', 'COMIC EXCERPTS: SILVER SURFER', 'FINEST AUTOGRAPHS',
    'DUAL AUTOGRAPHS', 'TRIPLE AUTOGRAPHS', 'QUAD AUTOGRAPHS BOOK CARD',
    'FANTASTIC SCIENCE AUTOGRAPHS', 'AUTHENTIC MARVEL COMIC BOOK ARTIST AUTOGRAPHS', 'SKETCH CARDS',
}

def acquire(url, path):
    with urllib.request.urlopen(url, timeout=45) as response:
        blob = response.read()
    assert blob.startswith(b'%PDF-')
    temp = path.with_suffix('.part'); temp.write_bytes(blob); temp.replace(path)
    path.with_suffix('.pdf.url').write_text(url)
    return hashlib.sha256(blob).hexdigest()

def text(chars):
    return ' '.join(''.join(c['text'] for c in chars).split())

def read_cards(path):
    rows, artists, raw, notes = [], [], [], []
    family = None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 17
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text()})
            groups = []
            for c in page.chars:
                baseline = c['matrix'][5]
                group = next((cs for y, cs in groups if abs(y-baseline) < .6), None)
                if group is None:
                    group = []; groups.append((baseline, group))
                group.append(c)
            for y, cs in sorted(groups, reverse=True):
                line = text(cs)
                if not line: continue
                if pn == 1 and y > 740:
                    notes.append([str(pn), line]); continue
                if line in FAMILIES:
                    family = line; continue
                if line in {'BASE', 'INSERT', 'RELIC', 'AUTOGRAPH', 'SKETCH'}: continue
                assert family, (pn, line)
                if family == 'SKETCH CARDS':
                    artists.append([line, str(pn)]); continue
                number = text([c for c in cs if c['x0'] < 180])
                right = 350 if family in {'TOPPS ORIGINALS','COMIC EXCERPTS: SILVER SURFER','FINEST AUTOGRAPHS','DUAL AUTOGRAPHS','TRIPLE AUTOGRAPHS','QUAD AUTOGRAPHS BOOK CARD','FANTASTIC SCIENCE AUTOGRAPHS'} else page.width
                name = text([c for c in cs if 180 <= c['x0'] < right])
                additional = text([c for c in cs if c['x0'] >= right])
                assert re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+', number) and name, (pn, line, number, name)
                rows.append([family, number, name, additional, str(pn)])
    assert len(rows) == 704 and len({r[0] for r in rows}) == 30
    assert len(artists) == 116 and artists[-1][0] == 'ジェイソン (Jason)'
    return rows, artists, raw, notes

def build():
    cp = ROOT / 'data/set-catalog.json'; catalog = json.loads(cp.read_text())
    record = next(s for s in catalog['sets'] if s['slug'] == SLUG)
    dp = ROOT / record['tableData']; data = json.loads(dp.read_text())
    path = ROOT / 'data/catalog-sources/downloads' / (SLUG+'.pdf')
    fingerprint = acquire(record['checklistUrl'], path)
    rows, artists, raw, notes = read_cards(path)
    op = path.with_name(SLUG+'-odds.pdf'); odds_hash = acquire(record['oddsUrl'], op)
    odds, formats, odds_raw, issues = physical_odds_pdf(op)
    assert len(odds) == 158 and formats == ['Hobby'] and not issues
    aliases = {
        'Base Cards - Common': 'BASE CARDS COMMON', 'Base Cards - Uncommon': 'BASE CARDS UNCOMMON',
        'Base Cards - Rare': 'BASE CARDS RARE', 'Base Cards - Negative Zone Variation': 'NEGATIVE ZONE BASE VARIATION',
        "Base Cards - 1960's Blacklight Neon": '1960s BLACKLIGHT BASE VARIATION',
        "Tribute to Finest '96": 'TRIBUTE TO FINEST ‘96', 'Concept Art': 'THE FANTASTIC FOUR: FIRST STEPS CONCEPT ART',
        "Clobberin' Time": 'CLOBBERIN’ TIME', "World's Greatest Comic Magazines": 'WORLD’S GREATEST COMIC MAGAZINES',
        'Flame Throwers': 'FLAME THROWERS VARIANTS', 'Rock Stars': 'ROCK STARS VARIANTS',
        'Comic Book Artist Autographs': 'AUTHENTIC MARVEL COMIC BOOK ARTIST AUTOGRAPHS',
        'Finest Dual Autographs': 'DUAL AUTOGRAPHS', 'Finest Triple Autographs': 'TRIPLE AUTOGRAPHS',
        'Finest Quad Autographs Booklets': 'QUAD AUTOGRAPHS BOOK CARD',
    }
    aliases.update({f.title(): f for f in FAMILIES if f not in aliases.values()})
    for odd in odds:
        matches = [k for k in aliases if odd['name'].casefold() == k.casefold() or odd['name'].casefold().startswith(k.casefold()+' ')]
        assert matches, odd['name']
        odd['family'] = aliases[max(matches, key=len)]
    note = ('All 704 numbered subject rows across 30 sections and 116 unnumbered sketch artists reconciled against physical cells. '
            'The three base tiers contain 100 subject rows but 98 distinct numeric identities: printed 34/034 and 41/041 repeat, '
            'while numeric 36 and 42 are absent. Preserve leading zeros and the published 19/46 forms. '
            'Blacklight, Negative Zone and Tribute each retain all 100 printed codes. Actor/character, artist and comic-issue cells '
            'remain separate unlabelled source fields. Repeated dual/triple/quad signer numbers and the missing FS-10 are retained. '
            'All 158 odds categories retain their complete wrapped names and literal Hobby ratios from ruled cells. '
            'The odds sheet names Hobby but does not state a ratio unit; no per-pack rate or probability is inferred. '
            'Only Tribute to Finest 96 /96 and Fantastic Creators 1/1 have guide-confirmed numbering; other parallel limits '
            'and a calendar release date remain unverified.')
    data.update(headers=['Checklist section','Card number','Name','Published additional text','Source page'], rows=rows,
                originalSubjectHeaders=['Checklist section','Card number','Name','Unlabelled additional column','Source page'],
                originalSubjectRows=rows, originalArtistRosters={'SKETCH CARDS': artists}, rawPages=raw,
                sourceDocumentNotes=notes, unclassifiedLines=[], sha256=fingerprint, importKind='topps-grid-pdf',
                dedicatedParser=PARSER, sectionColumn=0, odds=odds, formats=formats, oddsRawPages=odds_raw,
                oddsSha256=odds_hash, oddsIssues=[], oddsParser='scripts/official_odds_layout.py',
                formatNamesPublished=True, oddsUnitsPublished=False,
                publishedSpecifications=[dict(name='SKETCH CARDS', worksheet='Official PDF unnumbered artist roster; no card numbers inferred',
                                              headers=['Published artist name','Source page'], rows=artists)],
                sourceSheets=[dict(name='Official source reconciliation', notes=[[note]])])
    dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
    record.update(rowCount=len(rows), sections=30, importKind=data['importKind'], dedicatedParser=PARSER,
                  sha256=fingerprint, odds=158, formats=1, oddsParser=data['oddsParser'], oddsImportIssues=0,
                  verified='2026-10-15', catalogEvidence=note, dataAudit=note)
    cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    ip = ROOT/'data/topps-product-official-catalog.json'; inventory=json.loads(ip.read_text())
    inventory=[record if s['slug']==SLUG else s for s in inventory]
    if not any(s['slug']==SLUG for s in inventory): inventory.append(record)
    ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    rp=ROOT/'data/parallel-specifications.json'; registry=json.loads(rp.read_text())
    evidence=dict(source=json.loads(PROOF.read_text())['source'], evidenceFile=str(PROOF.relative_to(ROOT)),
                  evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
    registry['sets'][SLUG]=[
        dict(family='TRIBUTE TO FINEST ‘96',name="Tribute to Finest '96",oddsName="Tribute to Finest '96",numbering='/96',
             qualification='Tribute base variation only; no limits for its other named Refractors are inferred.',**evidence),
        dict(family='FANTASTIC CREATORS',name='Cut-signature relics',numbering='1/1',
             qualification='The guide names Jack Kirby and Stan Lee cut-signature relics; no other family is assigned this limit.',**evidence),
    ]
    rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    print('Finest Fantastic Four: 704 subject rows, 30 sections, 116 sketch artists, 158 complete odds categories and two scoped numbering facts.')

if __name__=='__main__': build()
