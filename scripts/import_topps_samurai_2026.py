"""Reconcile the official Samurai Japan checklist's physical columns and odds."""
import collections, hashlib, json, re, subprocess
from datetime import date
from pathlib import Path
import pdfplumber
from import_official_catalog import odds_pdf

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-chrome-baseball-team-samurai-japan-collection'
CACHE = ROOT / 'data/catalog-sources/downloads'
FAMILIES = {
    'Base Cards': 74, 'Base Card Short Prints': 6,
    'Sensational Samurai Insert': 10, 'Generational Greats Insert': 5,
    'Neon Nights Insert': 10, 'Samurai Spirit Insert': 5,
    'Base Card Autograph Parallel': 13,
    'Generational Great Dual Autograph Parallel': 1,
}

def physical_lines(page):
    lines = []
    for word in sorted(page.extract_words(), key=lambda w: (w['top'], w['x0'])):
        line = next((line for line in lines if abs(line[0]['top'] - word['top']) < 2), None)
        if line is None:
            lines.append([word])
        else:
            line.append(word)
    return [sorted(line, key=lambda w: w['x0']) for line in lines]

def parse_cards(path):
    rows, raw, notes, family = [], [], [], None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 4
        for pn, page in enumerate(pdf.pages, 1):
            assert (page.width, page.height) == (612, 792)
            raw.append({'page': pn, 'text': page.extract_text()})
            for words in physical_lines(page):
                text = ' '.join(w['text'] for w in words)
                if text in FAMILIES:
                    family = text
                    continue
                if family is None:
                    notes.append({'page': pn, 'text': text})
                    continue
                cells = [' '.join(w['text'] for w in words if left <= w['x0'] < right)
                         for left, right in [(0, 118), (118, 320), (320, 410), (410, 612)]]
                assert re.fullmatch(r'\d+(?:SP|-A)?|(?:SS|GG|NN|SAM)-\d+A?', cells[0]), (pn, text)
                assert cells[1] and cells[2] == 'Samurai Japan', (pn, cells)
                assert cells[3] in {'', 'Mgr.', 'IF', 'OF', 'P', 'P/DH', 'C'}, (pn, cells)
                rows.append([family, *cells, str(pn)])
    assert len(rows) == 124
    assert collections.Counter(r[0] for r in rows) == FAMILIES
    assert [r[1] for r in rows if r[0] == 'Base Cards'] == [str(n) for n in range(1, 75)]
    assert [r[1] for r in rows if r[0] == 'Base Card Short Prints'] == [f'{n}SP' for n in range(75, 81)]
    assert rows[-1][1:5] == ['GG-1A', 'Shohei Ohtani / Sadaharu Oh', 'Samurai Japan', '']
    return rows, raw, notes

def parse_odds(path):
    with pdfplumber.open(path) as pdf:
        revised = len(pdf.pages) == 1
    if revised:
        entries, formats, raw, issues = odds_pdf(path)
        assert formats == ['ONE PACK', 'COLLECTORS BOX'] and len(entries) == 48 and not issues
        mappings = [('BASE CARD SHORT PRINT', 'Base Card Short Prints'),
                    ('BASE CARD', 'Base Cards'),
                    ('AUTOGRAPH', 'Base Card Autograph Parallel'),
                    ('SENSATIONAL SAMURAI', 'Sensational Samurai Insert'),
                    ('GENERATIONAL GREATS', 'Generational Greats Insert'),
                    ('SAMURAI SPIRIT', 'Samurai Spirit Insert')]
        for odd in entries:
            for prefix, family in mappings:
                if odd['name'] == prefix or odd['name'].startswith(prefix + ' '):
                    odd.update(family=family, familyBase=odd['name'] == prefix)
                    break
        return entries, formats, raw
    odds, raw = [], []
    format_name = 'Odds (Per Pack)'
    mappings = [
        ('BASE CARDS SHORTPRINTS', 'Base Card Short Prints'),
        ('BASE CARDS', 'Base Cards'),
        ('AUTOGRAPH BASE CARDS', 'Base Card Autograph Parallel'),
        ('SENSATIONAL SAMURAI', 'Sensational Samurai Insert'),
    ]
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 2
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text()})
            for words in physical_lines(page):
                text = ' '.join(w['text'] for w in words)
                if text == 'COMPONENT Odds (Per Pack)':
                    continue
                values = [w for w in words if re.fullmatch(r'\d+:\d+', w['text'])]
                assert len(values) == 1 and values[0]['x0'] > 340, (pn, text)
                name = ' '.join(w['text'] for w in words if w is not values[0])
                assert name and name.upper() == name
                odd = {'name': name, 'values': {format_name: values[0]['text']}, 'page': pn}
                for prefix, family in mappings:
                    if name == prefix or name.startswith(prefix + ' '):
                        odd['family'] = family
                        break
                # Literal unmatched odds families are retained without guessing
                # which differently named checklist subset they describe.
                odds.append(odd)
    assert len(odds) == 42
    return odds, [format_name], raw

def refresh(url, path):
    temporary = path.with_suffix('.refresh.pdf')
    subprocess.run(['curl', '-sLf', '--retry', '2', '--max-time', '30', url, '-o', str(temporary)], check=True)
    assert temporary.read_bytes().startswith(b'%PDF')
    temporary.replace(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    catalog_path = ROOT / 'data/set-catalog.json'
    catalog = json.loads(catalog_path.read_text())
    record = next(r for r in catalog['sets'] if r['slug'] == SLUG)
    cards_path, odds_path = CACHE / (SLUG + '.pdf'), CACHE / (SLUG + '-odds.pdf')
    card_hash = refresh(record['checklistUrl'], cards_path)
    odds_hash = refresh(record['oddsUrl'], odds_path)
    rows, raw, notes = parse_cards(cards_path)
    odds, formats, odds_raw = parse_odds(odds_path)
    payload = {'title': record['title'], 'headers': ['Checklist section', 'Card number', 'Player / subjects', 'Team', 'Published position', 'Source page'],
               'rows': rows, 'source': record['checklistUrl'], 'sha256': card_hash,
               'rawPages': raw, 'unclassifiedLines': notes, 'importKind': 'pdf', 'sectionColumn': 0,
               'odds': odds, 'formats': formats, 'oddsSource': record['oddsUrl'], 'oddsSha256': odds_hash,
               'oddsRawPages': odds_raw, 'oddsIssues': [], 'coverageComplete': False,
               'dedicatedParser': 'scripts/import_topps_samurai_2026.py',
               'oddsUnitsPublished': formats == ['Odds (Per Pack)'],
               'oddsParser': 'scripts/official_odds_layout.py'}
    (ROOT / record['tableData']).write_text(json.dumps(payload, ensure_ascii=False) + '\n')
    record.update(verified=date.today().isoformat(),rowCount=124, sections=8, odds=len(odds), formats=len(formats), sha256=card_hash,
                  dedicatedParser=payload['dedicatedParser'], coverageComplete=False,
                  oddsParser=payload['oddsParser'],
                  dataAudit='All 124 printed rows, eight literal subset headings and physical subject/team/position columns reconciled. The current indexed odds sheet supplies 48 categories and 96 literal values across ONE PACK / COLLECTORS BOX; no ratio unit is stated. Six 75SP–80SP short prints retained. No inferred rookie flags or serial limits.',
                  catalogEvidence='Listed in Topps’ 2026 checklist catalog; an exact release date is not verified. The October 17 source review replaces the older 42-category single-column odds sheet with the current indexed 48-category two-format sheet. TOKYO NEON NIGHTS and DUAL AUTOGRAPHS lack an exact printed checklist-family name and remain unjoined. Source format headings do not establish a ratio unit. Published categories alone do not establish exhaustive parallel or numbering coverage.')
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    inventory_path = ROOT / 'data/topps-product-official-catalog.json'
    inventory = json.loads(inventory_path.read_text())
    inventory = [r for r in inventory if r['slug'] != SLUG] + [record]
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    print('Imported 124 Samurai Japan rows, eight subsets and 96 literal values across two formats; ratio units are not stated.')

if __name__ == '__main__':
    build()
