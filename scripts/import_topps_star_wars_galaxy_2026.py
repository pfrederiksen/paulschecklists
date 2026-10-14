"""Preserve original Galaxy subject cells, repeated signers and artist roster."""
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path
import pdfplumber
from official_odds_layout import physical_odds_pdf

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-star-wars-chrome-galaxy'
PARSER = 'scripts/import_topps_star_wars_galaxy_2026.py'
PRODUCT = 'https://www.topps.com/products/2026-star-wars-chrome%C2%AE-galaxy-hobby-box'
CHECKLIST = 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/26SWCGCHECKLISTUPDATE.pdf?v=1787977075'
ODDS = 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Stars_Wars_Chrome_Galaxy.pdf?v=1787977079'

def physical_rows(page):
    groups = []
    for char in page.chars:
        # Production disclaimers occupy the page header. The later-added
        # Bryce Dallas Howard card also uses Arial and must remain a card.
        if 'Arial' in char['fontname'] and char['top'] < 52:
            continue
        group = next((g for y, g in groups if abs(y - char['top']) < 2), None)
        if group is None:
            group = []
            groups.append((char['top'], group))
        group.append(char)
    return sorted(groups)

def read_cards(path):
    rows, raw = [], []
    section = None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 17
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text()})
            for y, chars in physical_rows(page):
                text = ''.join(c['text'] for c in chars).strip()
                if all('Bold' in c['fontname'] for c in chars):
                    if text != 'INSERT':
                        section = text
                    continue
                if section == 'SKETCH CARD ARTISTS':
                    assert all(c['x0'] >= 126.3 for c in chars), (pn, y, text)
                    rows.append([section, '', text, str(pn), '', text])
                    continue
                starts = []
                origins = [123.67, 360.67] if all('Arial' in c['fontname'] for c in chars) else [126.38, 362.21]
                for col, x in enumerate(origins):
                    # Aptos and Verdana start the first printed text cell at
                    # 126.38 and 126.50 respectively in this document.
                    indices = [i for i, c in enumerate(chars) if abs(c['x0'] - x) < (.15 if col == 0 else .03)]
                    if indices:
                        starts.append((max(indices), col))
                assert starts and starts[0][1] == 0, (pn, y, text)
                number = ''.join(c['text'] for c in chars[:starts[0][0]]).strip()
                assert re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9-]+', number), (pn, y, number)
                cells = ['', '']
                for i, (start, col) in enumerate(starts):
                    end = starts[i + 1][0] if i + 1 < len(starts) else len(chars)
                    cells[col] = ''.join(c['text'] for c in chars[start:end]).strip()
                assert section and cells[0], (pn, y, text)
                rows.append([section, number, cells[0], str(pn), cells[1], ''])
    assert [int(r[1]) for r in rows if r[0] == 'BASE CARDS'] == list(range(1, 101))
    return rows, raw

def acquire(url, path):
    subprocess.run(['curl', '-sLf', '--retry', '2', '--max-time', '30', url, '-o', str(path)], check=True)
    path.with_suffix('.pdf.url').write_text(url)
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    cp = ROOT / 'data/set-catalog.json'
    catalog = json.loads(cp.read_text())
    record = next(r for r in catalog['sets'] if r['slug'] == SLUG)
    dp = ROOT / record['tableData']
    data = json.loads(dp.read_text())
    path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
    fingerprint = acquire(CHECKLIST, path)
    rows, raw = read_cards(path)
    op = path.with_name(SLUG + '-odds.pdf')
    odds_hash = acquire(ODDS, op)
    odds, formats, odds_raw, issues = physical_odds_pdf(op)
    assert not issues and len(odds) == 110 and formats == ['Hobby']
    if odds_hash == data.get('oddsSha256'):
        prior = {o['name']: o for o in data['odds']}
        for odd in odds:
            for field in ['family', 'familyAliases', 'numbering', 'numberingSource', 'qualification']:
                if field in prior.get(odd['name'], {}):
                    odd[field] = prior[odd['name']][field]
    for odd in odds:
        # The product description identifies the KOTOR and concept-art
        # programs. Keep each document's literal title while reconciling
        # these two uniquely named checklist/odds family spelling variants.
        for prefix, family in [('Art of Knights of the Old Republic', 'ART OF KNIGHTS OF THE REPUBLIC'),
                               ('Chrome Layers Original Art', 'TOPPS CHROME LAYERS ORIGINAL ART')]:
            if odd['name'] == prefix or odd['name'].startswith(prefix + ' '):
                odd.update(family=family, familyBase=odd['name'] == prefix)
    data.update(headers=['Checklist section', 'Card number', 'Player / subjects', 'Source page', 'Additional published text', 'Artist roster name'],
                rows=rows, rawPages=raw, unclassifiedLines=[], sha256=fingerprint,
                source=CHECKLIST, sectionColumn=0, importKind='topps-grid-pdf', dedicatedParser=PARSER,
                coverageComplete=True, odds=odds, formats=formats, oddsRawPages=odds_raw,
                oddsSource=ODDS, oddsSha256=odds_hash, oddsIssues=[], oddsParser='scripts/official_odds_layout.py')
    evidence = ROOT / 'data/parallel-audit-sources/star-wars-galaxy-product-20261014.json'
    product = json.loads(evidence.read_text())
    assert product['source'] == PRODUCT
    data['productConfigurationEvidence'] = {'file': str(evidence.relative_to(ROOT)), 'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest(), 'source': PRODUCT}
    data['sourceSheets'] = [{'name': 'Official Hobby product configuration', 'notes': [
        ['Manufacturer configuration', f"{product['cardsPerPack']} cards per pack; {product['packsPerBox']} packs per box; {product['ChromeParallelsPerBox']} Chrome parallels per box; {product['autographStatement']}. These are manufacturer configuration statements, not calculated pack odds or individual-card guarantees."],
        ['Store availability', product['Available From'] + '; this Available From field is not a verified release date.'],
        ['Unlabelled source columns', 'The numbered checklist prints subjects/names and art credits or character names in separate text columns without column headings. Additional published text retains the original second cell.'],
        ['Source family titles', 'Checklist ART OF KNIGHTS OF THE REPUBLIC corresponds to odds Art of Knights of the Old Republic; TOPPS CHROME LAYERS ORIGINAL ART corresponds to odds Chrome Layers Original Art. Original names remain literal. Family odds do not establish individual-subject eligibility.'],
        ['Parallel audit', 'The official hobby guide could not be retrieved for exact parallel-numbering reconciliation; exhaustive coverage is not claimed.']]}]
    dp.write_text(json.dumps(data, ensure_ascii=False) + '\n')
    numbered = sum(bool(r[1]) for r in rows)
    artists = len(rows) - numbered
    note = (f'All {numbered} numbered subject rows and {artists} unnumbered sketch-artist entries are reconciled to original physical PDF cells, including the Japanese/Latin final artist name. The additional text column contains printed art credits or autograph character names; its original values and spelling are retained without assigning an unpublished universal column label. Repeated card numbers for dual, triple and quad signers remain separate source rows. Counts represent source entries, not unique cards. All 110 Hobby odds categories are retained. The official product lists Available From August 12, 2026; this store availability field is not treated as a verified release date. Exhaustive parallel numbering review remains pending; the official hobby guide currently could not be retrieved for reconciliation.')
    record.update(sourcePage=PRODUCT, checklistUrl=CHECKLIST, oddsUrl=ODDS, rowCount=len(rows),
                  sections=len({r[0] for r in rows}), sha256=fingerprint, importKind=data['importKind'],
                  dedicatedParser=PARSER, coverageComplete=True, availableFrom='2026-08-12',
                  odds=len(odds), formats=len(formats), oddsParser=data['oddsParser'], oddsImportIssues=0,
                  catalogEvidence=note, dataAudit=note)
    cp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    ip = ROOT / 'data/topps-product-official-catalog.json'
    inventory = json.loads(ip.read_text())
    inventory = [record if r['slug'] == SLUG else r for r in inventory]
    ip.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    print(record['title'], numbered, 'numbered subject rows;', artists, 'artists;', len(rows), 'entries;', len(odds), 'odds categories')

if __name__ == '__main__':
    build()
