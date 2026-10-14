"""Reconcile Disneyland's original PDF cells, including its numeric base lists."""
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path
import pdfplumber
from official_odds_layout import physical_odds_pdf

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2025-topps-disneyland-70th-anniversary'
PARSER = 'scripts/import_topps_disneyland_2025.py'
HEADERS = ['Checklist section', 'Card number', 'Player / subjects', 'Source page',
           'Subject', 'THEN / NOW', 'Land', 'Unlabelled additional subject column',
           'First Name', 'Last Name', 'Character', 'Attraction', 'Name']

def cells(chars, origins):
    starts = []
    for col, x in enumerate(origins):
        indices = [i for i, c in enumerate(chars) if abs(c['x0'] - x) < .03]
        if indices:
            starts.append((max(indices), col))
    assert starts, ''.join(c['text'] for c in chars)
    values = [''] * len(origins)
    for i, (start, col) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(chars)
        values[col] = ''.join(c['text'] for c in chars[start:end]).strip()
    return values, starts[0][0]

def read_cards(path):
    rows, raw = [], []
    section = None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 14
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text()})
            lines = collections.defaultdict(list)
            for c in page.chars:
                # Japanese and Latin glyphs share one artist cell, but have
                # slightly different font baselines in the final source row.
                y = round(c['top']) if pn >= 13 else round(c['top'], 1)
                if pn == 14 and 433 <= c['top'] <= 435:
                    y = 434
                lines[y].append(c)
            for y, chars in sorted(lines.items()):
                text = ''.join(c['text'] for c in chars).strip()
                if text in ['Card NumberSubjectLand', 'Card NumberSubject',
                            'Card NumberFirst NameLast NameCharacterAttraction',
                            'Card NumberCharacter', 'Name']:
                    continue
                row = [''] * len(HEADERS)
                row[3] = str(pn)
                if pn >= 13:
                    if text == 'SKETCH ARTISTS':
                        section = text
                        continue
                    row[2] = row[12] = text
                else:
                    origins = ([97.96, 270.32, 301.94] if pn <= 6 else
                               [82.82, 197.62] if pn <= 8 else
                               [110.97, 175.77, 253.53, 377.46] if pn == 9 else [125.0])
                    has_cell = any(abs(c['x0'] - origins[0]) < .03 for c in chars)
                    if all('Bold' in c['fontname'] for c in chars):
                        assert text == text.upper() and re.search('[A-Z]', text), (pn, y, text)
                        section = text
                        continue
                    assert has_cell, (pn, y, text)
                    values, start = cells(chars, origins)
                    number = ''.join(c['text'] for c in chars[:start]).strip()
                    assert re.fullmatch(r'\d+|[A-Z0-9&]+-[A-Z0-9-]+', number) or (not number and section == 'MAGICAL GRAND PRIZE REDEMPTION'), (pn, y, number)
                    row[1] = number
                    if pn <= 6:
                        row[2] = row[4] = values[0]
                        row[5:7] = values[1:]
                        assert row[5] in ['', 'THEN', 'NOW'], (pn, y, row, text)
                    elif pn <= 8:
                        row[2] = row[4] = values[0]
                        row[7] = values[1]
                    elif pn == 9:
                        row[8:12] = values
                        row[2] = ' '.join(values[:2])
                        assert all(values)
                    elif pn == 10:
                        row[2] = row[10] = values[0]
                    else:
                        row[2] = row[4] = values[0]
                assert section and row[2], (pn, y, text)
                row[0] = section
                rows.append(row)
    numeric = [r for r in rows if r[1].isdigit()]
    assert len(numeric) == 450
    for suffix in ['', ' HIDDEN MICKEY VARIATION', ' LIGHT BULB VARIATION']:
        group = [r for r in numeric if r[0] in [family + suffix for family in ['THEN AND NOW', 'TIMELINE', 'SNACK TIME', 'CONCEPT ART']]]
        assert [int(r[1]) for r in group] == list(range(1, 151))
    assert len([r for r in rows if r[0] == 'SKETCH ARTISTS']) == 77
    return rows, raw

def build():
    cp = ROOT / 'data/set-catalog.json'
    catalog = json.loads(cp.read_text())
    record = next(r for r in catalog['sets'] if r['slug'] == SLUG)
    path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
    subprocess.run(['curl', '-sLf', '--retry', '2', '--max-time', '30', record['checklistUrl'], '-o', str(path)], check=True)
    rows, raw = read_cards(path)
    dp = ROOT / record['tableData']
    data = json.loads(dp.read_text())
    op = path.with_name(SLUG + '-odds.pdf')
    subprocess.run(['curl', '-sLf', '--retry', '2', '--max-time', '30', record['oddsUrl'], '-o', str(op)], check=True)
    odds, formats, odds_raw, issues = physical_odds_pdf(op)
    assert not issues
    # The numeric base list has four printed headings; the odds sheet calls
    # the same 150-card list Base Set. Variations have their own source lists.
    for odd in odds:
        if odd['name'].startswith('Base Set'):
            suffix = (' HIDDEN MICKEY VARIATION' if odd['name'] == 'Base Set Variation Hidden Mickey' else
                      ' LIGHT BULB VARIATION' if odd['name'] == 'Base Set Variation Red/White Bulb' else '')
            odd.update(family='BASE SET', familyAliases=[family + suffix for family in ['THEN AND NOW', 'TIMELINE', 'SNACK TIME', 'CONCEPT ART']])
    data.update(headers=HEADERS, rows=rows, rawPages=raw, unclassifiedLines=[],
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(), sectionColumn=0,
                importKind='topps-grid-pdf', dedicatedParser=PARSER, coverageComplete=True,
                odds=odds, formats=formats, oddsRawPages=odds_raw, oddsIssues=issues,
                oddsSha256=hashlib.sha256(op.read_bytes()).hexdigest(), oddsParser='scripts/official_odds_layout.py')
    dp.write_text(json.dumps(data, ensure_ascii=False) + '\n')
    note = ('All 450 printed base/Hidden Mickey/Light Bulb entries, numbered inserts and autograph/relic rows, the unnumbered Grand Prize Redemption and 77 sketch-artist entries are reconciled to original physical PDF cells. Original Subject, THEN/NOW, Land, actor First Name/Last Name, Character and Attraction fields are retained; the additional unlabelled insert column remains unlabelled. The source omits TCC-2 and prints TCC-11 twice; both printed TCC-11 rows are retained. Counts are source entries, not unique cards. The set is listed in Topps’ 2026 checklist catalog; its exact release date remains unverified. Parallel-inventory audit remains separate from checklist completeness.')
    record.update(rowCount=len(rows), sections=len({r[0] for r in rows}), sha256=data['sha256'],
                  importKind=data['importKind'], dedicatedParser=PARSER, coverageComplete=True,
                  odds=len(odds), formats=len(formats), oddsParser=data['oddsParser'],
                  oddsImportIssues=0, catalogEvidence=note, dataAudit=note)
    cp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    ip = ROOT / 'data/topps-product-official-catalog.json'
    inventory = json.loads(ip.read_text())
    inventory = [record if r['slug'] == SLUG else r for r in inventory]
    ip.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    print(record['title'], len(rows), 'source entries;', len(odds), 'odds categories;', len(formats), 'formats')

if __name__ == '__main__':
    build()
