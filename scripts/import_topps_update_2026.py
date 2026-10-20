"""Reconcile both official Update layouts without inferring missing Rookie fields."""
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path
import pdfplumber
from import_official_catalog import odds_pdf

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-update-series-baseball'
PARSER = 'scripts/import_topps_update_2026.py'
PREVIOUS_URL = 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Update_Series_Baseball_Checklist_10-12.pdf?v=1791908509'
PREVIOUS_HASH = '9fb7df274e22d2c1f4180c7eeb65cd02d274ec3f6bc74717058b5456f7892e41'
URL = 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Update_Series_Baseball_Checklist_10-19.pdf?v=1792504951'
CURRENT_HASH = '016821d40f16ad880dcaa1fdddba77b34590b5c0119624dcd18ba7494bd9e81d'
REVISION = 'data/parallel-audit-sources/update-baseball-2026-revision-20261020.json'
EDUCATION_URL = 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/Update_Series_Baseball_Education_Sheet-r2.pdf?v=1791989094'
EDUCATION_HASH = '1f2b2161a7b90e957ccef480b4d231add41291d3d204978b272e4337bca079bc'
EDUCATION_PROOF = 'data/parallel-audit-sources/update-baseball-2026-education-20261020.json'
BASE = ['VETERAN I', 'VETERANS II', 'ROOKIES', 'ROOKIE DEBUT', 'VETERAN COMBOS', 'SEASON HIGHLIGHTS']


def acquire(url, path):
    temporary = path.with_suffix('.refresh.pdf')
    subprocess.run(['curl', '-sLf', '--retry', '2', '--max-time', '45', url, '-o', str(temporary)], check=True)
    assert temporary.read_bytes().startswith(b'%PDF')
    temporary.replace(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_tiled_cards(path):
    rows, raw, positions, captions = [], [], {}, []
    section = None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 100
        for pn, page in enumerate(pdf.pages[:73], 1):
            raw.append({'page': pn, 'text': page.extract_text() or ''})
            bands = []
            for c in sorted(page.chars, key=lambda c: c['top']):
                if not bands or c['top'] - bands[-1][0] > 2:
                    bands.append((c['top'], []))
                bands[-1][1].append(c)
            for y, band in bands:
                if pn == 1 and y < 150:
                    continue
                ids = {id(c) for c in band}
                chars = [c for c in page.chars if id(c) in ids]
                text = ''.join(c['text'] for c in chars).strip()
                if all('Bold' in c['fontname'] for c in chars):
                    captions.append({'page': pn, 'top': round(y, 3), 'text': text})
                    section = text
                    continue
                starts = []
                for col, x in [(1, 132.62), (2, 352.87)]:
                    matches = [i for i, c in enumerate(chars) if abs(c['x0'] - x) < .03]
                    if matches:
                        starts.append((max(matches), col))
                assert starts and starts[0][1] == 1, (pn, y, text)
                cells = [''.join(c['text'] for c in chars[:starts[0][0]]).strip(), '', '']
                for j, (idx, col) in enumerate(starts):
                    end = starts[j + 1][0] if j + 1 < len(starts) else len(chars)
                    cells[col] = ''.join(c['text'] for c in chars[idx:end]).strip()
                assert section and cells[1] and re.fullmatch(r'[A-Za-z0-9-]*', cells[0]), (pn, cells)
                rows.append([section, *cells, '', str(pn)])
                positions.setdefault(pn, []).append((y, len(rows) - 1))
        # The PDF tiles the rightmost Rookie column after all 73 name pages.
        # Only 27 continuation pages are printed; never propagate other flags.
        for number, page in enumerate(pdf.pages[73:], 74):
            raw.append({'page': number, 'text': page.extract_text() or ''})
            for word in page.extract_words():
                if word['text'] != 'Rookie':
                    assert number == 74 and word['top'] < 120, (number, word)
                    continue
                candidates = [idx for y, idx in positions[number - 73] if abs(y - word['top']) < .03]
                assert len(candidates) == 1, (number, word, candidates)
                row = rows[candidates[0]]
                assert not row[4]
                row[4] = 'Rookie'
    assert len(rows) == 3795 and sum(not r[1] for r in rows) == 121
    assert rows[-1][1:4] == ['', 'Ketel Marte', 'Arizona Diamondbacks®']
    return rows, raw, captions


def read_cards(path):
    """Use original text-object starts, including the overlapping buyback cells."""
    rows, raw, captions = [], [], []
    section = None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 67
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text() or ''})
            bands = []
            for c in sorted(page.chars, key=lambda c: c['top']):
                if not bands or c['top'] - bands[-1][0] > 2:
                    bands.append((c['top'], []))
                bands[-1][1].append(c)
            for y, band in bands:
                if pn == 1 and y < 150:
                    continue
                ids = {id(c) for c in band}
                chars = [c for c in page.chars if id(c) in ids]
                text = ''.join(c['text'] for c in chars).strip()
                if all('Bold' in c['fontname'] for c in chars):
                    section = text
                    captions.append({'page': pn, 'top': round(y, 3), 'text': text})
                    continue
                starts = []
                for col, x in [(1, 123.62), (2, 319.63), (3, 454.78)]:
                    matches = [i for i, c in enumerate(chars) if abs(c['x0'] - x) < .03]
                    if matches:
                        starts.append((max(matches), col))
                assert starts and starts[0][1] == 1, (pn, y, text)
                cells = [''.join(c['text'] for c in chars[:starts[0][0]]).strip(), '', '', '']
                for j, (idx, col) in enumerate(starts):
                    end = starts[j + 1][0] if j + 1 < len(starts) else len(chars)
                    cells[col] = ''.join(c['text'] for c in chars[idx:end]).strip()
                assert section and cells[1] and re.fullmatch(r'[A-Za-z0-9-]*', cells[0]), (pn, cells)
                assert cells[3] in {'', 'Rookie'}, (pn, cells)
                rows.append([section, *cells, str(pn)])
    assert len(rows) == 3870 and len({r[0] for r in rows}) == 99
    assert sum(r[4] == 'Rookie' for r in rows) == 1570
    assert sum(not r[1] for r in rows) == 121
    assert rows[-1][1:4] == ['', 'Ketel Marte', 'Arizona Diamondbacks®']
    return rows, raw, captions


def retain_revision(path, rows):
    previous = path.with_name(SLUG + '-10-12.pdf')
    assert acquire(PREVIOUS_URL, previous) == PREVIOUS_HASH
    old, _, _ = read_tiled_cards(previous)
    identities = lambda values: collections.Counter(tuple(r[:4]) for r in values)
    before, after = identities(old), identities(rows)
    assert not before - after
    added = list((after - before).elements())
    assert collections.Counter(r[0] for r in added) == {
        'WORLD BASEBALL CLASSIC HIGHLIGHTS': 50, 'STRIKE ZONE HEROES': 25}
    flags = lambda values: identities([r for r in values if r[4] == 'Rookie'])
    prior_flags, current_flags = flags(old), flags(rows)
    assert not prior_flags - current_flags
    added_flags = list((current_flags - prior_flags).elements())
    assert len(added_flags) == 909
    proof = {
        'observed': '2026-10-20', 'sourceKind': 'official-pdf-physical-revision-comparison',
        'sourceIndex': 'https://www.topps.com/pages/checklists',
        'previousDocument': {'url': PREVIOUS_URL, 'sha256': PREVIOUS_HASH, 'pages': 100,
                             'subjectRows': 3795, 'families': 97, 'printedRookieFields': 661},
        'currentDocument': {'url': URL, 'sha256': CURRENT_HASH, 'pages': 67,
                            'subjectRows': 3870, 'families': 99, 'printedRookieFields': 1570},
        'identityColumns': ['Checklist section', 'Card number', 'Name', 'Team / country'],
        'removedSubjectIdentities': [], 'addedSubjectIdentities': added,
        'removedPrintedRookieFields': [], 'addedPrintedRookieFields': added_flags,
        'reconciliation': 'All 3,795 earlier number/name/team identities and all 661 earlier Rookie fields remain. '
                          'The new PDF adds 75 subjects and prints 909 additional Rookie fields. '
                          'Its Rookie column is inline on all 67 pages; earlier missing continuation tiles remain historical, not inferred omissions.',
        'qualifications': [
            'Both added families are explicitly captioned JAPAN EXCLUSIVE. WBC country cells remain literal source values; no club team is inferred.',
            'The two buyback Rookie fields are separate original text objects, even where the long Ohtani title overlaps other cells. The word Rookie inside each buyback title is not itself a flag.',
            'The unchanged odds source retains all 281 categories / nine columns and the malformed 1:-401,280 Fanatics cell. No odds unit, extra numbering or parallel eligibility is inferred.'
        ]
    }
    evidence = ROOT / REVISION
    evidence.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
    return hashlib.sha256(evidence.read_bytes()).hexdigest()


def education(path, odds):
    sheet = path.with_name(SLUG + '-education.pdf')
    assert acquire(EDUCATION_URL, sheet) == EDUCATION_HASH
    expected = {
        'BASE PARALLELS': [['Gold', '/2026'], ['Independence Day', '/76'], ['Black', '/75'],
                          ['Canvas', '/50'], ['Memorial Day Camo', '/25'], ['Wood', '/25']],
        'INSERT PARALLELS': [['Blue', '/150'], ['Green', '/99'], ['Gold', '/50'], ['Orange', '/25'],
                            ['Black', '/10'], ['Red', '/5'], ['Foilfractor', '/1']],
        'AUTOGRAPH PARALLELS': [['Blue', '/150'], ['Green', '/99'], ['Gold', '/50'], ['Orange', '/25'],
                               ['Black', '/10'], ['Red', '/5'], ['Foilfractor', '/1']]}
    with pdfplumber.open(sheet) as pdf:
        assert len(pdf.pages) == 2
        raw = [{'page': n, 'text': p.extract_text() or ''} for n, p in enumerate(pdf.pages, 1)]
        for heading, box in [('BASE PARALLELS', (198, 645, 330, 738)),
                             ('INSERT PARALLELS', (337, 645, 464, 738)),
                             ('AUTOGRAPH PARALLELS', (470, 645, 598, 738))]:
            lines = pdf.pages[1].crop(box).extract_text().splitlines()
            cells = [list(re.fullmatch(r'(.+?)\s+(/\d+)', line).groups()) for line in lines]
            assert cells == expected[heading], (heading, cells)
        configurations = [
            ['HOBBY BOX', '12 CARDS PER PACK', '20 PACKS PER BOX', '1 AUTO OR RELIC PER BOX'],
            ['JUMBO BOX', '40 CARDS PER PACK', '10 PACKS PER BOX', '1 AUTO AND RELIC PER BOX'],
            ['VALUE BOX', '12 CARDS PER PACK', '6 PACKS PER BOX', 'Not stated in this sheet']]
        # Original text objects preserve each format's quantities and units.
        configuration_boxes = [
            [(75, 212, 130, 232), (140, 212, 192, 232), (95, 237, 180, 252)],
            [(255, 212, 310, 232), (322, 212, 374, 232), (275, 237, 365, 252)],
            [(435, 212, 490, 232), (502, 212, 546, 232), None]]
        for column, boxes in zip(configurations, configuration_boxes):
            for value, box in zip(column[1:], boxes):
                if box is not None:
                    text = re.sub(r'\s+', '', pdf.pages[1].crop(box).extract_text() or '')
                    assert re.sub(r'\s+', '', value) == text, (value, text)
    facts = {'parallelColumns': expected, 'baseFamilies': BASE, 'boxConfigurations': configurations,
             'sheetSummary': [['CARD BASE SET', '350'], ['INSERT SETS', '7'],
                              ['AUTOGRAPH SUBSETS', '22'], ['SSP SETS', '7']]}
    proof = {'observed': '2026-10-20', 'sourceKind': 'official-pdf-physical-column-review',
             'source': EDUCATION_URL, 'sha256': EDUCATION_HASH, 'pages': 2, 'facts': facts,
             'factsSha256': hashlib.sha256(json.dumps(facts, ensure_ascii=False, sort_keys=True,
                                                     separators=(',', ':')).encode()).hexdigest(),
             'rawPages': raw,
             'qualifications': ['The base column applies only to the six printed BASE SET sections / 350 numeric identities. No base variation, insert, autograph, redemption or Japan-exclusive program inherits those limits.',
                                'The insert and autograph columns do not identify exact family eligibility. Preserve all fourteen terms unjoined, including the literal /1, without selecting a family limit.',
                                'Configuration quantities retain per-pack and per-box units. Preserve the Jumbo literal 1 AUTO AND RELIC PER BOX; do not invent a separate relic count or convert box statements into pack odds.',
                                'The sheet counts do not replace the complete checklist family counts. The 75th-anniversary design motif is not an additional serial-number claim.']}
    evidence = ROOT / EDUCATION_PROOF
    evidence.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    mappings = []
    for name, value in expected['BASE PARALLELS']:
        odds_name = 'BASE CARDS ' + name.upper()
        assert any(o['name'] == odds_name and o['family'] == BASE[0] and o['familyAliases'] == BASE[1:] for o in odds)
        mappings.append({'family': BASE[0], 'name': name, 'numbering': value, 'oddsName': odds_name,
                         'source': EDUCATION_URL, 'evidenceFile': EDUCATION_PROOF, 'evidenceSha256': digest,
                         'qualification': 'Education-sheet BASE PARALLELS column, scoped to the 350-card BASE SET and its six explicit checklist headings. The original Base odds aliases retain all six headings; no variation, insert, autograph or Japan-exclusive program receives this limit.'})
    registry_path = ROOT / 'data/parallel-specifications.json'
    registry = json.loads(registry_path.read_text())
    retained = [entry for entry in registry['sets'].get(SLUG, [])
                if entry.get('evidenceFile') != EDUCATION_PROOF]
    registry['sets'][SLUG] = retained + mappings
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
    tables = [{'name': heading + ' (exact family eligibility unverified)',
               'worksheet': 'Original education-sheet column; retain unjoined scope',
               'headers': ['Published parallel', 'Published numbering', 'Scope qualification'],
               'rows': [[name, value, 'No exact checklist-family eligibility is stated; do not apply this limit to an individual family.'] for name, value in expected[heading]],
               'source': EDUCATION_URL, 'evidenceFile': EDUCATION_PROOF, 'evidenceSha256': digest}
              for heading in ['INSERT PARALLELS', 'AUTOGRAPH PARALLELS']]
    tables.append({'name': 'Manufacturer box configurations (education sheet)',
                   'worksheet': 'Original units and text; box contents are not pack odds',
                   'headers': ['Published format', 'Cards per pack', 'Packs per box', 'Literal published box statement'],
                   'rows': configurations, 'source': EDUCATION_URL,
                   'evidenceFile': EDUCATION_PROOF, 'evidenceSha256': digest})
    return tables, {'source': EDUCATION_URL, 'sha256': EDUCATION_HASH,
                    'evidenceFile': EDUCATION_PROOF, 'evidenceSha256': digest}


def build():
    cp = ROOT / 'data/set-catalog.json'
    catalog = json.loads(cp.read_text())
    record = next(r for r in catalog['sets'] if r['slug'] == SLUG)
    dp = ROOT / record['tableData']
    data = json.loads(dp.read_text())
    path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
    fingerprint = acquire(URL, path)
    assert fingerprint == CURRENT_HASH
    rows, raw, captions = read_cards(path)
    revision_hash = retain_revision(path, rows)
    op = path.with_name(SLUG + '-odds.pdf')
    odds_hash = acquire(record['oddsUrl'], op)
    odds, formats, odds_raw, issues = odds_pdf(op)
    assert len(odds) == 281 and len(formats) == 9 and not issues
    malformed = next(o for o in odds if o['name'] == 'TOPPS 75TH ANNIVERSARY GIFTS REDEMPTION CARDS')
    malformed['values'][formats[6]] = '1:-401,280'
    malformed['qualification'] = 'The Fanatics cell prints the malformed literal 1:-401,280. It is retained without correction or an inferred numeric rate.'
    exception = {'name': malformed['name'], 'format': formats[6], 'page': 7,
                 'value': '1:-401,280', 'nameBox': [14, 700.9, 220, 722.8],
                 'valueBox': [900, 700.9, 950, 722.8]}
    with pdfplumber.open(op) as pdf:
        chars = pdf.pages[6].crop(tuple(exception['valueBox'])).chars
        assert ''.join(c['text'] for c in chars) == exception['value']
    families = {r[0] for r in rows}
    key = lambda v: re.sub(r'[^A-Z0-9]', '', v.upper())
    for odd in odds:
        if odd['name'].startswith('BASE CARDS '):
            odd.update(family=BASE[0], familyAliases=BASE[1:], familyBase=False)
            continue
        matches = [f for f in families if key(odd['name']).startswith(key(f))]
        if matches:
            family = max(matches, key=lambda f: len(key(f)))
            odd.update(family=family, familyBase=key(odd['name']) == key(family))
    guide_tables, guide_source = education(path, odds)
    note = ('The revised October 19 checklist is reconciled to all 3,870 physical subject rows across '
            f'{len(families)} families, including 121 unnumbered redemption subjects. Original Name/Team '
            'and country cells, source spellings and repeated signer codes remain intact. All 67 pages '
            f'print their Rookie column inline, retaining {sum(r[4] == "Rookie" for r in rows):,} literal flags. '
            'All earlier subject identities and Rookie fields remain; 50 World Baseball Classic Highlights '
            'and 25 Strike Zone Heroes subjects are added under explicit Japan Exclusive captions. '
            'All 281 odds categories and nine '
            'literal format columns are retained; no ratio unit is stated. The product-linked education '
            'sheet supplies six exact base parallel limits plus fourteen unjoined insert/autograph terms. '
            'Box configuration units remain separate from odds. Exhaustive numbering and '
            'unmatched odds-family mappings remain incomplete. The Fanatics 75th Anniversary Gifts '
            'cell prints malformed 1:-401,280, retained literally without correction or rate inference.')
    data.update(headers=['Checklist section', 'Card number', 'Name', 'Team', 'Rookie', 'Source page'],
                rows=rows, rawPages=raw, sourceCaptions=captions, unclassifiedLines=[],
                source=URL, sha256=fingerprint, importKind='topps-grid-pdf', dedicatedParser=PARSER,
                sectionColumn=0, odds=odds, formats=formats, oddsRawPages=odds_raw, oddsIssues=[],
                oddsSource=record['oddsUrl'], oddsSha256=odds_hash, oddsUnitsPublished=False,
                oddsParser='scripts/official_odds_layout.py', oddsLiteralExceptions=[exception], coverageComplete=False)
    data['checklistRevision'] = {'file': REVISION, 'sha256': revision_hash}
    data['publishedSpecifications'] = [
        {'name': family, 'worksheet': 'Original checklist market caption; no odds or numbering claim',
         'headers': ['Published field', 'Published value', 'Scope'],
         'rows': [['Source caption', 'JAPAN EXCLUSIVE', family]], 'source': URL,
         'evidenceFile': REVISION, 'evidenceSha256': revision_hash}
        for family in ['WORLD BASEBALL CLASSIC HIGHLIGHTS', 'STRIKE ZONE HEROES']]
    data['publishedSpecifications'].extend(guide_tables)
    data['educationSource'] = guide_source
    dp.write_text(json.dumps(data, ensure_ascii=False) + '\n')
    record.update(checklistUrl=URL, sha256=fingerprint, rowCount=len(rows), sections=len(families),
                  importKind=data['importKind'], dedicatedParser=PARSER, odds=len(odds), formats=len(formats),
                  oddsParser=data['oddsParser'], oddsImportIssues=0, publishedOdds=True,
                  dataAudit=note, catalogEvidence=note, coverageComplete=False, verified='2026-10-20',
                  checklistRevision=data['checklistRevision'])
    cp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    ip = ROOT / 'data/topps-product-official-catalog.json'
    inventory = json.loads(ip.read_text())
    inventory = [r for r in inventory if r['slug'] != SLUG] + [record]
    ip.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    index_path = ROOT / 'data/topps-official-catalog.json'
    index = json.loads(index_path.read_text())
    entries = [r for r in index if r['url'] in {PREVIOUS_URL, URL}]
    assert len(entries) == 1 and entries[0]['title'] == record['title']
    entries[0]['url'] = URL
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
    print(note)


if __name__ == '__main__':
    build()
