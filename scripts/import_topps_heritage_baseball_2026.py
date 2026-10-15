"""Reconcile Heritage's physical cells, literal annotations and exact guide joins."""
import collections
import hashlib
import json
import re
import urllib.request
from pathlib import Path

import pdfplumber
from import_official_catalog import odds_pdf

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-heritage-baseball'
PARSER = 'scripts/import_topps_heritage_baseball_2026.py'
PROOF = ROOT / 'data/parallel-audit-sources/heritage-baseball-2026-guides-20261015.json'
CAPTIONS = {'BASE', 'INSERT', 'AUTOGRAPH', 'AUTOGRAPH RELIC', 'RELIC'}
NOTES = {'2026 TOPPS HERITAGE CHECKLIST', 'SUBJECT TO CHANGE*', '* - Denotes Short Print'}
ORIGINS = [113.06, 252.05, 367.39, 442.87]


def acquire(url, path):
    with urllib.request.urlopen(url, timeout=45) as response:
        blob = response.read()
    assert blob.startswith(b'%PDF-')
    temporary = path.with_suffix('.part')
    temporary.write_bytes(blob)
    temporary.replace(path)
    path.with_suffix('.pdf.url').write_text(url)
    return hashlib.sha256(blob).hexdigest()


def read_cards(path):
    original, raw, notes = [], [], []
    section = None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 25
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text()})
            lines = collections.defaultdict(list)
            for char in page.chars:
                lines[round(char['top'], 1)].append(char)
            for y, chars in sorted(lines.items()):
                text = ''.join(c['text'] for c in chars).strip()
                if text in NOTES:
                    notes.append([str(pn), text])
                    continue
                if all('Bold' in c['fontname'] for c in chars):
                    assert text == text.upper(), (pn, y, text)
                    if text not in CAPTIONS:
                        section = text
                    continue
                starts = []
                for col, x in enumerate(ORIGINS, 1):
                    indices = [i for i, c in enumerate(chars) if abs(c['x0'] - x) < .03]
                    if indices:
                        starts.append((max(indices), col))
                assert starts and starts[0][1] == 1, (pn, y, text)
                cells = [''.join(c['text'] for c in chars[:starts[0][0]]).strip(), '', '', '', '']
                for j, (idx, col) in enumerate(starts):
                    end = starts[j + 1][0] if j + 1 < len(starts) else len(chars)
                    cells[col] = ''.join(c['text'] for c in chars[idx:end]).strip()
                assert re.fullmatch(r'\d+|[A-Za-z0-9]+-[A-Za-z0-9]+', cells[0]), (pn, y, cells)
                assert section and cells[1]
                assert cells[3] in ['', 'Rookie', 'Base unnumbered autos are all red ink'], (pn, y, cells)
                assert cells[4] in ['', '*Back Variation'], (pn, y, cells)
                original.append([section, *cells, str(pn)])
    assert len(original) == 1542 and len({r[0] for r in original}) == 40
    assert sum(r[4] == 'Rookie' for r in original) == 315
    rows = [[*r[:4], 'Rookie' if r[4] == 'Rookie' else '', *r[4:]] for r in original]
    return rows, original, raw, notes


def read_odds(path):
    odds, printed_formats, raw, issues = odds_pdf(path)
    assert len(odds) == 230 and len(printed_formats) == 12 and not issues
    # The disclaimer occupies the category heading, outside the first SKU cell.
    formats = [re.sub(r'^\*subject to change\*', '', f) for f in printed_formats]
    assert all(re.fullmatch(r'65\d\d - MLB- HERITAGE 2026 .+', f) for f in formats)
    for odd in odds:
        odd['values'] = {f: v for f, v in zip(formats, odd['values'].values())}
    families = ['LEAGUE LEADERS', 'RECORD BREAKERS', 'WORLD SERIES HIGHLIGHTS', 'TURN BACK THE CLOCK', 'QUAD ROOKIES']
    variation_names = {
        'BASE ALL-STAR LOGO VARIATIONS': 'ALL STAR LOGO VARIATION',
        'BASE IMAGE VARIATIONS': 'IMAGE VARIATIONS',
        'BASE ALTERNATE BANNER VARIATIONS': 'ALTERNATE BANNER VARIATIONS',
        'BASE NICKNAME VARIATIONS': 'NICKNAME VARIATIONS',
        'BASE THROWBACK JERSEY VARIATIONS': 'THROWBACK JERSEYS VARIATION',
        'BASE BLACK AND WHITE IMAGE VARIATIONS': 'BLACK AND WHITE IMAGE VARIATION',
    }
    for odd in odds:
        name = odd['name']
        if name in variation_names:
            odd.update(family=variation_names[name], familyBase=True)
            continue
        for family in sorted(families, key=len, reverse=True):
            if name == family or name.startswith(family + ' '):
                chrome = ' CHROME VARIATIONS' in name
                odd.update(family=family + (' CHROME VARIATION' if chrome else ''),
                           familyBase=name == family + (' CHROME VARIATIONS' if chrome else ''))
                break
        else:
            if name.startswith('BASE CHROME VARIATIONS') or name.startswith('BASE SHORT PRINTS CHROME VARIATIONS'):
                odd.update(family='BASE CARDS CHROME VARIATION', familyBase=name == 'BASE CHROME VARIATIONS')
            elif name.startswith('BASE ') and not name.startswith('BASE CHROME AUTOGRAPH') and 'VARIATION' not in name:
                odd.update(family='BASE CARDS', familyBase=False)
    return odds, formats, raw


def build():
    cp = ROOT / 'data/set-catalog.json'
    catalog = json.loads(cp.read_text())
    record = next(s for s in catalog['sets'] if s['slug'] == SLUG)
    dp = ROOT / record['tableData']
    data = json.loads(dp.read_text())
    path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
    fingerprint = acquire(record['checklistUrl'], path)
    rows, original, raw, notes = read_cards(path)
    op = path.with_name(SLUG + '-odds.pdf')
    odds_hash = acquire(record['oddsUrl'], op)
    odds, formats, odds_raw = read_odds(op)
    proof = json.loads(PROOF.read_text())
    proof_hash = hashlib.sha256(PROOF.read_bytes()).hexdigest()
    evidence = {'file': str(PROOF.relative_to(ROOT)), 'sha256': proof_hash, 'source': proof['productSource']}
    note = ('All 1,542 physical subject rows across 40 sections reconciled, with separate name/team cells, '
            '315 literal Rookie marks, 148 subject/team asterisks and both Back Variation annotations. '
            'Each paper and Chrome base program retains 400 distinct numbers across 456 subject rows. '
            'Repeated multi-player numbers, ten blank team cells, original marks on established players and '
            '77RO autograph codes are retained. Repeated disclaimers are source notes, not card sections. '
            'All 230 odds categories and 12 original SKU columns remain literal; the category-heading disclaimer '
            'is separated from the first format. Color of the Year /77 applies only to the paper base program; '
            'hand-numbered Special Edition Red Ink /77 is separate from the PDF note about unnumbered red-ink '
            'base autographs. LCS/AL-NL family joins and exhaustive parallel numbering remain unresolved. '
            'March 18, 2026 is verified U.S. store availability; a universal release date is not asserted. '
            'Store availability and box contents are not pack odds.')
    data.update(headers=['Checklist section', 'Card number', 'Name', 'Team', 'Rookie', 'Published annotation',
                         'Published additional annotation', 'Source page'],
                rows=rows, originalSubjectHeaders=['Checklist section', 'Card number', 'Name', 'Team',
                                                  'Published annotation', 'Published additional annotation', 'Source page'],
                originalSubjectRows=original, rawPages=raw, sourceDocumentNotes=notes, unclassifiedLines=[],
                sha256=fingerprint, sectionColumn=0, importKind='topps-grid-pdf', dedicatedParser=PARSER,
                odds=odds, formats=formats, oddsRawPages=odds_raw, oddsSha256=odds_hash, oddsIssues=[],
                oddsHeaderNotes=['Card *subject to change*'], productConfigurationEvidence=evidence,
                publishedSpecifications=[{'name': 'Box contents and store availability (not pack odds)',
                                          'worksheet': 'Official product pages; preserve configuration and date scope',
                                          'headers': ['Published format', 'Published configuration', 'Official store availability', 'Official source'],
                                          'rows': proof['configuration'], 'source': proof['productSource'],
                                          'evidenceFile': evidence['file'], 'evidenceSha256': proof_hash},
                                         {'name': 'Manufacturer format-specific parallels',
                                          'worksheet': 'Official Value and Mega product descriptions; numbering is not stated here',
                                          'headers': ['Published format', 'Published program', 'Published parallel', 'Official source'],
                                          'rows': [[*r, proof['valueSource'] if r[0] == 'Value' else proof['megaSource']]
                                                   for r in proof['formatParallels']],
                                          'source': proof['productSource'], 'evidenceFile': evidence['file'], 'evidenceSha256': proof_hash}],
                sourceSheets=[{'name': 'Official source reconciliation', 'notes': [[note], *[[g] for g in proof['remainingGaps']]]}])
    dp.write_text(json.dumps(data, ensure_ascii=False) + '\n')
    record.pop('releaseSource', None)
    record.pop('releaseEvidence', None)
    record.update(rowCount=len(rows), sections=40, importKind=data['importKind'], dedicatedParser=PARSER,
                  sha256=fingerprint, odds=230, formats=12, oddsImportIssues=0,
                  releaseStatus='Released', releaseDate=None, storeAvailabilityDate=proof['availability'],
                  storeAvailabilitySource=proof['hobbySource'], storeAvailabilityEvidence=evidence,
                  verified=proof['observed'], catalogEvidence=note, dataAudit=note)
    cp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    ip = ROOT / 'data/topps-product-official-catalog.json'
    inventory = json.loads(ip.read_text())
    if any(s['slug'] == SLUG for s in inventory):
        inventory = [record if s['slug'] == SLUG else s for s in inventory]
    else:
        inventory.append(record)
    ip.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    registry_path = ROOT / 'data/parallel-specifications.json'
    registry = json.loads(registry_path.read_text())
    additions = []
    for odd in odds:
        if odd['name'].endswith(' COLOR OF THE YEAR'):
            family = odd.get('family', 'LEAGUE CHAMPIONSHIP SERIES')
            additions.append(dict(family=family, name='Heritage Orange / Color of the Year', numbering='/77',
                                  oddsName=odd['name'], source=proof['productSource'], sourceHeading='About the release',
                                  qualification='Paper base program only; retain the exact odds category and short-print scope. Individual-card eligibility is not inferred.',
                                  evidenceFile=evidence['file'], evidenceSha256=proof_hash))
    assert len(additions) == 8
    additions.append(dict(family='REAL ONE AUTOGRAPHS', name='Special Edition Red Ink', numbering='/77',
                          oddsName='REAL ONE AUTOGRAPHS SPECIAL EDITION', source=proof['megaSource'],
                          sourceHeading='Description / Autograph content',
                          qualification='Hand-numbered Special Edition only. The PDF separately states that base unnumbered autos are all red ink; ink color alone does not establish /77.',
                          evidenceFile=evidence['file'], evidenceSha256=proof_hash))
    registry['sets'][SLUG] = additions
    registry['conflicts'] = [c for c in registry.get('conflicts', []) if c['slug'] != SLUG] + [
        {'slug': SLUG, 'family': family, 'gap': proof['remainingGaps'][i], 'source': proof['productSource'],
         'evidenceFile': evidence['file'], 'evidenceSha256': proof_hash}
        for i, family in [(0, 'REAL ONE AUTOGRAPHS'), (1, 'LEAGUE CHAMPIONSHIP SERIES')]]
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
    print('Heritage Baseball: 1542 original rows, 40 sections, 315 Rookie marks, two 400-number programs, 230 odds categories and nine exact /77 joins.')


if __name__ == '__main__':
    build()
