"""Retain every Marvel Chrome subject, unlabelled cell and unnumbered artist."""
import collections
import hashlib
import json
import re
import urllib.request
from pathlib import Path

import pdfplumber
from official_odds_layout import physical_odds_pdf

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-chrome-marvel-comics'
PARSER = 'scripts/import_topps_marvel_chrome_2026.py'
PROOF = ROOT / 'data/parallel-audit-sources/marvel-chrome-2026-guides-20261015.json'
FAMILIES = {
    'CHARACTERS I', 'CHARACTERS II', 'CHARACTERS I CLAWED CHROME VARIATION',
    'CHARACTERS II CLAWED CHROME VARIATION', 'FANFARE', 'MARVEL ICONS', 'MEANWHILE',
    'ONE WORLD UNDER DOOM', 'FUTURE STARS', '60 YEARS OF BLACK PANTHER', '65 FANTASTIC YEARS',
    'VARIED VISAGE AOA', 'THE BEYOND', 'TOPPS ORIGINALS', 'CLASSIC COMIC BOOK COVERS',
    'CORDIALLY INVITED', 'MARVEL REFLECTIONS', 'GOLDEN ANNIVERSARIES', 'ASTONISHING',
    'MARVEL FACSIMILE AUTOGRAPHS', 'MARVEL FACSIMILE DUAL AUTOGRAPHS',
    'MARVEL FACSIMILE TRIPLE AUTOGRAPHS', 'MARVEL FACSIMILE QUAD AUTOGRAPHS',
    'TOPPS PATRIMONY', 'THE ONE AND ONLY', 'X-FORCE 35TH ANNIVERSARY',
    'THE ONE AND ONLY STAN LEE AND STEVE DITKO', 'COMIC EXCERPTS SPIDER MAN',
    'AUTHENTIC MARVEL COMIC BOOK ARTIST AUTOGRAPHS', 'CORDIALLY INVITED AUTOGRAPHS',
    'VARIED VISAGE AUTOGRAPHS', 'ARTIST ORIGINALS', 'SKETCH CARD ARTISTS',
}
EXTRA = {'TOPPS ORIGINALS', 'TOPPS PATRIMONY', 'COMIC EXCERPTS SPIDER MAN', 'VARIED VISAGE AUTOGRAPHS'}


def acquire(url, path):
    with urllib.request.urlopen(url, timeout=45) as response:
        blob = response.read()
    assert blob.startswith(b'%PDF-')
    temporary = path.with_suffix('.part')
    temporary.write_bytes(blob)
    temporary.replace(path)
    path.with_suffix('.pdf.url').write_text(url)
    return hashlib.sha256(blob).hexdigest()


def text(chars):
    return ' '.join(''.join(c['text'] for c in chars).split())


def read_cards(path):
    rows, raw, notes = [], [], []
    artists = collections.defaultdict(list)
    section = None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 22
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text()})
            groups = []
            for char in page.chars:
                baseline = char['matrix'][5]
                chars = next((cs for y, cs in groups if abs(baseline - y) < .6), None)
                if chars is None:
                    chars = []
                    groups.append((baseline, chars))
                chars.append(char)
            for baseline, chars in sorted(groups, reverse=True):
                line = text(chars)
                if not line:
                    continue
                if pn == 1 and baseline > 710:
                    notes.append([str(pn), line])
                    continue
                if line in FAMILIES:
                    section = line
                    continue
                if line in ['BASE', 'INSERT', 'RELIC', 'AUTOGRAPH', 'SKETCH']:
                    continue
                if pn == 16 and line in ['MARVEL', 'FACSIMILE', 'QUAD', 'AUTOGRAPHS']:
                    section = 'MARVEL FACSIMILE QUAD AUTOGRAPHS'
                    continue
                if section in ['ARTIST ORIGINALS', 'SKETCH CARD ARTISTS']:
                    artists[section].append([line, str(pn)])
                    continue
                pieces = [chars]
                # The source draws the second printed card inline after Mary
                # Jane. Preserve both original glyph ranges, not a guessed ID.
                if pn == 4 and any(c['text'] == '1' and abs(c['x0'] - 124.96) < .02 for c in chars):
                    assert line == '136 Mary Jane 137 Misery'
                    pieces = [[c for c in chars if c['x0'] < 124.9], [c for c in chars if c['x0'] >= 124.9]]
                for cells in pieces:
                    line = text(cells)
                    if section.startswith('CHARACTERS'):
                        match = re.fullmatch(r'(\d+)\s*(.+)', line)
                        assert match, (pn, baseline, line)
                        number, name = match.groups()
                        additional = ''
                    else:
                        # The early inserts and first facsimile card use
                        # narrower printed ID cells than the remaining table.
                        left = 75 if section in ['FANFARE', 'MARVEL ICONS'] else 100 if line.startswith('MF-BB') else 130
                        right = 350 if section in EXTRA else 612
                        number = text([c for c in cells if c['x0'] < left])
                        name = text([c for c in cells if left <= c['x0'] < right])
                        additional = text([c for c in cells if c['x0'] >= right])
                        assert re.fullmatch(r'[A-Za-z0-9]+-[A-Za-z0-9]+', number), (pn, baseline, line, number)
                    assert section and name, (pn, baseline, line)
                    rows.append([section, number, name, additional, str(pn)])
    assert len(rows) == 764 and len({r[0] for r in rows}) == 31
    assert len(artists['ARTIST ORIGINALS']) == 2 and len(artists['SKETCH CARD ARTISTS']) == 124
    assert artists['SKETCH CARD ARTISTS'][-1][0] == 'ジェイソン (Jason)'
    for family in ['CHARACTERS I', 'CHARACTERS II', 'CHARACTERS I CLAWED CHROME VARIATION', 'CHARACTERS II CLAWED CHROME VARIATION']:
        numbers = {int(r[1]) for r in rows if r[0] == family}
        assert numbers == set(range(1, 101) if family.startswith('CHARACTERS I ') or family == 'CHARACTERS I' else range(101, 201))
    return rows, dict(artists), raw, notes


def build():
    cp = ROOT / 'data/set-catalog.json'
    catalog = json.loads(cp.read_text())
    record = next(s for s in catalog['sets'] if s['slug'] == SLUG)
    dp = ROOT / record['tableData']
    data = json.loads(dp.read_text())
    path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
    fingerprint = acquire(record['checklistUrl'], path)
    rows, artists, raw, notes = read_cards(path)
    op = path.with_name(SLUG + '-odds.pdf')
    odds_hash = acquire(record['oddsUrl'], op)
    odds, formats, odds_raw, issues = physical_odds_pdf(op)
    assert len(odds) == 179 and len(formats) == 7 and not issues
    exact = {
        'The One and Only: Stan Lee & Steve Ditko Superfractor': 'THE ONE AND ONLY STAN LEE AND STEVE DITKO',
        'The One and Only Superfractor': 'THE ONE AND ONLY',
        'Artist Originals': 'ARTIST ORIGINALS',
    }
    for odd in odds:
        if odd['name'] in exact:
            odd['family'] = exact[odd['name']]
    proof = json.loads(PROOF.read_text())
    proof_hash = hashlib.sha256(PROOF.read_bytes()).hexdigest()
    note = ('All 764 numbered subject rows in 31 sections reconciled, including both 200-card base and Clawed programs, '
            '30 retail insert rows, the wrapped quad-facsimile heading and both printed inline cards 136 Mary Jane / 137 Misery. '
            'All 38 unlabelled additional cells retain their printed artist names or years without assigning new column roles. '
            'Artist Originals lists two unnumbered artists; the separate sketch roster retains 124 names, including IQ and the '
            'final Japanese/Latin name. No team or rookie fields are inferred. All 179 odds categories and seven literal columns '
            'remain unchanged, including three-part and period-separated ratios; those values are not converted to numeric hit rates. '
            'The guide describes the Stan Lee/Steve Ditko cut program and Artist Originals as one-of-one; these do not number '
            'the separate five-character The One and Only insert. Exhaustive parallel numbering and a release date remain unverified.')
    specs = [dict(name=family, worksheet='Official PDF unnumbered artist roster; no card numbers inferred',
                  headers=['Published artist name', 'Source page'], rows=values)
             for family, values in artists.items()]
    data.update(headers=['Checklist section', 'Card number', 'Name', 'Published additional text', 'Source page'],
                rows=rows, originalSubjectHeaders=['Checklist section', 'Card number', 'Name', 'Unlabelled additional column', 'Source page'],
                originalSubjectRows=rows, rawPages=raw, sourceDocumentNotes=notes, originalArtistRosters=artists,
                unclassifiedLines=[], sha256=fingerprint, sectionColumn=0, importKind='topps-grid-pdf', dedicatedParser=PARSER,
                odds=odds, formats=formats, oddsRawPages=odds_raw, oddsSha256=odds_hash, oddsIssues=[],
                oddsParser='scripts/official_odds_layout.py', publishedSpecifications=specs,
                sourceSheets=[{'name': 'Official source reconciliation', 'notes': [[note], *[[g] for g in proof['remainingGaps']]]}])
    dp.write_text(json.dumps(data, ensure_ascii=False) + '\n')
    record.update(rowCount=764, sections=31, importKind=data['importKind'], dedicatedParser=PARSER, sha256=fingerprint,
                  odds=179, formats=7, oddsParser=data['oddsParser'], oddsImportIssues=0,
                  verified=proof['observed'], catalogEvidence=note, dataAudit=note)
    cp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    ip = ROOT / 'data/topps-product-official-catalog.json'
    inventory = json.loads(ip.read_text())
    inventory = [record if s['slug'] == SLUG else s for s in inventory]
    if not any(s['slug'] == SLUG for s in inventory):
        inventory.append(record)
    ip.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    rp = ROOT / 'data/parallel-specifications.json'
    registry = json.loads(rp.read_text())
    evidence = dict(source=proof['source'], evidenceFile=str(PROOF.relative_to(ROOT)), evidenceSha256=proof_hash)
    registry['sets'][SLUG] = [
        dict(family='THE ONE AND ONLY STAN LEE AND STEVE DITKO', name='Cut signatures', numbering='1/1',
             qualification='Named Stan Lee/Steve Ditko cut-signature program only; the separate five-character The One and Only insert is not assigned this limit.',
             sourceHeading='Introduction / The One and Only cut signatures', **evidence),
        dict(family='ARTIST ORIGINALS', name='Original hand-drawn artwork', numbering='One-of-one original artwork', oddsName='Artist Originals',
             qualification='The guide describes artwork uniqueness; this is not a claim of printed serial numbering for the artist roster or other sketch programs.',
             sourceHeading='Artist Originals / Collector FAQs', **evidence),
    ]
    rp.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
    print('Chrome Marvel Comics: 764 subject rows, 31 sections, 126 unnumbered artist entries, 179 odds categories and exact one-of-one guide scope.')


if __name__ == '__main__':
    build()
