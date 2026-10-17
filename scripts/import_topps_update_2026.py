"""Reconcile the revised Update PDF's original name/team cells and rookie tiles."""
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
URL = 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Update_Series_Baseball_Checklist_10-12.pdf?v=1791908509'
BASE = ['VETERAN I', 'VETERANS II', 'ROOKIES', 'ROOKIE DEBUT', 'VETERAN COMBOS', 'SEASON HIGHLIGHTS']


def acquire(url, path):
    temporary = path.with_suffix('.refresh.pdf')
    subprocess.run(['curl', '-sLf', '--retry', '2', '--max-time', '45', url, '-o', str(temporary)], check=True)
    assert temporary.read_bytes().startswith(b'%PDF')
    temporary.replace(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_cards(path):
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


def build():
    cp = ROOT / 'data/set-catalog.json'
    catalog = json.loads(cp.read_text())
    record = next(r for r in catalog['sets'] if r['slug'] == SLUG)
    dp = ROOT / record['tableData']
    data = json.loads(dp.read_text())
    path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
    fingerprint = acquire(URL, path)
    rows, raw, captions = read_cards(path)
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
    note = ('The revised October 12 checklist is reconciled to all 3,795 physical subject rows across '
            f'{len(families)} families, including 121 unnumbered redemption subjects. Original Name/Team '
            'cells, source spellings and repeated signer codes remain intact. Name pages 1–27 align with '
            f'Rookie continuation pages 74–100, retaining {sum(r[4] == "Rookie" for r in rows)} printed flags. '
            'No Rookie continuation is printed for name pages 28–73. All 281 odds categories and nine '
            'literal format columns are retained; no ratio unit is stated. Supplementary numbering and '
            'unmatched odds-family mappings remain incomplete. The Fanatics 75th Anniversary Gifts '
            'cell prints malformed 1:-401,280, retained literally without correction or rate inference.')
    data.update(headers=['Checklist section', 'Card number', 'Name', 'Team', 'Rookie', 'Source page'],
                rows=rows, rawPages=raw, sourceCaptions=captions, unclassifiedLines=[],
                source=URL, sha256=fingerprint, importKind='topps-grid-pdf', dedicatedParser=PARSER,
                sectionColumn=0, odds=odds, formats=formats, oddsRawPages=odds_raw, oddsIssues=[],
                oddsSource=record['oddsUrl'], oddsSha256=odds_hash, oddsUnitsPublished=False,
                oddsParser='scripts/official_odds_layout.py', oddsLiteralExceptions=[exception], coverageComplete=False)
    dp.write_text(json.dumps(data, ensure_ascii=False) + '\n')
    record.update(checklistUrl=URL, sha256=fingerprint, rowCount=len(rows), sections=len(families),
                  importKind=data['importKind'], dedicatedParser=PARSER, odds=len(odds), formats=len(formats),
                  oddsParser=data['oddsParser'], oddsImportIssues=0, publishedOdds=True,
                  dataAudit=note, catalogEvidence=note, coverageComplete=False, verified='2026-10-17')
    cp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    ip = ROOT / 'data/topps-product-official-catalog.json'
    inventory = json.loads(ip.read_text())
    inventory = [r for r in inventory if r['slug'] != SLUG] + [record]
    ip.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    print(note)


if __name__ == '__main__':
    build()
