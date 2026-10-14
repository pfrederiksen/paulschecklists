"""Reconcile Masterwork and Smugglers original subject cells and artist lists."""
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
import pdfplumber
from official_odds_layout import physical_odds_pdf, normalized

ROOT = Path(__file__).resolve().parents[1]
PARSER = 'scripts/import_topps_star_wars_backfills.py'
SLUGS = ['topps-bowman-2025-star-wars-masterwork',
         'topps-bowman-2025-topps-star-wars-smugglers-outpost']
HEADERS = ['Checklist section', 'Card number', 'Player / subjects', 'Source page',
           'Additional published text', 'Additional published relic text', 'Artist roster name']

def lines(page):
    groups = []
    for c in page.chars:
        g = next((cs for y, cs in groups if abs(c['top'] - y) < 2), None)
        if g is None:
            g = []
            groups.append((c['top'], g))
        g.append(c)
    return sorted(groups)

def read_cards(path, masterwork):
    rows, raw = [], []
    section = None
    artist_heading = 'SKETCH ARTISTS' if masterwork else 'Sketch Artist List'
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == (18 if masterwork else 29)
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text()})
            for y, chars in lines(page):
                text = ''.join(c['text'] for c in chars).strip()
                if text.startswith(('Checklists provided by Topps', 'actual contents and odds')):
                    continue
                if all('Bold' in c['fontname'] for c in chars):
                    if text not in ['BASE', 'INSERT', 'INSERTS', 'AUTOGRAPH', 'AUTOGRAPHS', 'SKETCH CARDS']:
                        section = text
                    continue
                assert section, (pn, y, text)
                if section == artist_heading:
                    rows.append([section, '', text, str(pn), '', '', text])
                    continue
                origins = [136.58, 277.37, 378.79] if masterwork else [128.66, 313.73]
                if masterwork and section in ['SKELETON CREW RELIC', 'RELIC CARDS']:
                    origins[1] = 277.01
                starts = []
                for col, x in enumerate(origins):
                    indices = [i for i, c in enumerate(chars) if abs(c['x0'] - x) < .03]
                    if indices:
                        starts.append((max(indices), col))
                assert starts and starts[0][1] == 0, (pn, y, text)
                number = ''.join(c['text'] for c in chars[:starts[0][0]]).strip()
                assert re.fullmatch(r'\d+|[A-Za-z0-9]+-[A-Za-z0-9-]+', number), (pn, y, number)
                cells = ['', '', '']
                for i, (start, col) in enumerate(starts):
                    end = starts[i + 1][0] if i + 1 < len(starts) else len(chars)
                    cells[col] = ''.join(c['text'] for c in chars[start:end]).strip()
                assert cells[0], (pn, y, text)
                rows.append([section, number, cells[0], str(pn), cells[1], cells[2], ''])
    return rows, raw

def masterwork_odds(path):
    """Original text origins retain the overflowing puzzle caption and typo."""
    odds, raw, exceptions = [], [], []
    with pdfplumber.open(path) as pdf:
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text()})
            tables = page.find_tables()
            assert len(tables) == 1
            table = tables[0]
            assert [normalized(v) for v in table.extract()[0]] == ['Cards', 'SKU 1 Pack Rate']
            for row in table.rows[1:]:
                divider = row.cells[0][2]
                chars = [c for c in page.chars if row.bbox[1] <= (c['top']+c['bottom'])/2 <= row.bbox[3]]
                starts = [i for i, c in enumerate(chars) if i == 0 or
                          abs(c['top']-chars[i-1]['top']) > 1 or
                          c['x0'] < chars[i-1]['x0'] or c['x0']-chars[i-1]['x1'] > 8]
                cells = [[], []]
                for a, b in zip(starts, starts[1:]+[len(chars)]):
                    cells[0 if chars[a]['x0'] < divider else 1].append(''.join(c['text'] for c in chars[a:b]))
                name, value = [normalized(' '.join(parts)) for parts in cells]
                assert name and value, (pn, row.bbox, cells)
                item = {'name': name, 'values': {'SKU 1 Pack Rate': value}, 'page': pn}
                if not re.fullmatch(r'[\d,.]+(?::[\d,.]+)+', value):
                    assert pn == 13 and name == 'Skeleton Crew Auto Relic Black' and value == '1,249'
                    item['qualification'] = 'Official PDF prints 1,249 without a ratio separator; retained literally, with no probability inferred.'
                    exceptions.append({'name': name, 'page': pn, 'value': value, 'qualification': item['qualification']})
                odds.append(item)
    assert len(exceptions) == 1
    return odds, ['SKU 1 Pack Rate'], raw, exceptions

def acquire(url, path):
    subprocess.run(['curl', '-sLf', '--retry', '2', '--max-time', '30', url, '-o', str(path)], check=True)
    path.with_suffix('.pdf.url').write_text(url)
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    cp = ROOT / 'data/set-catalog.json'
    catalog = json.loads(cp.read_text())
    registry_path = ROOT / 'data/parallel-specifications.json'
    registry = json.loads(registry_path.read_text())
    history_path = ROOT / 'data/revision-history.json'
    history = json.loads(history_path.read_text())
    for slug in SLUGS:
        master = 'masterwork' in slug
        record = next(r for r in catalog['sets'] if r['slug'] == slug)
        dp = ROOT / record['tableData']
        data = json.loads(dp.read_text())
        path = ROOT / 'data/catalog-sources/downloads' / (slug + '.pdf')
        fingerprint = acquire(data['source'], path)
        rows, raw = read_cards(path, master)
        op = path.with_name(slug + '-odds.pdf')
        odds_hash = acquire(data['oddsSource'], op)
        odds, formats, odds_raw, exceptions = masterwork_odds(op) if master else physical_odds_pdf(op)
        sections = {r[0] for r in rows}
        aliases = {'Base Cards': 'CHARACTERS', 'Ultimate Book Card Autos': 'ULTIMATE BOOK CARD AUTOGRAPHS',
                   'Skeleton Crew Auto Relic': 'SKELETON CREW AUTOGRAPH RELIC',
                   'ROTJ Film Cell Auto Relic': 'ROTJ FILM CEL AUTOGRAPH RELIC', 'ROTJ Film Cell': 'ROTJ FILM CEL',
                   'Harrison Ford Buyback On Card Autographs': 'HARRISON FORD BUYBACK ON CARD AUTOS'} if master else {}
        canonical = lambda x: re.sub(r'[^A-Z0-9]', '', x.upper())
        for odd in odds:
            candidates = [(prefix, family) for prefix, family in aliases.items() if odd['name'] == prefix or odd['name'].startswith(prefix + ' ')]
            candidates += [(family, family) for family in sections if canonical(odd['name']).startswith(canonical(family))]
            if candidates:
                prefix, family = max(candidates, key=lambda pair: len(canonical(pair[0])))
                odd.update(family=family, familyBase=canonical(odd['name']) == canonical(prefix))
        # Existing guide facts remain intact, but obsolete duplicated parser
        # prefixes and casing must join the literal printed family captions.
        if not master:
            previous_specs = copy.deepcopy(registry['sets'].get(slug, []))
            for spec in registry['sets'].get(slug, []):
                if spec.get('oddsName') and spec['oddsName'] not in {o['name'] for o in odds}:
                    old = spec['oddsName']
                    prefix = spec['family'].title()
                    corrected = old.replace(prefix + ' ' + prefix + ' ', prefix + ' ', 1)
                    assert corrected in {o['name'] for o in odds}, (old, corrected)
                    spec['oddsName'] = corrected
                family = 'Stellar Signatures Autograph' if spec['family'] == 'STELLAR SIGNATURES AUTOGRAPHS' else next(s for s in sections if canonical(s) == canonical(spec['family']))
                spec['family'] = family
                key = lambda text: canonical(re.sub(r'\bparallel\b', '', text, flags=re.I))
                matches = [o for o in odds if key(o['name']) == key(family + ' ' + spec['name'])]
                if not spec.get('oddsName') and len(matches) == 1:
                    spec['oddsName'] = matches[0]['name']
            new_specs = registry['sets'].get(slug, [])
            facts = lambda specs: [{k:v for k,v in s.items() if k not in ['family', 'oddsName']} for s in specs]
            digest = lambda value: hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
            # Changing an adapter join while every hash-checked guide fact
            # stays identical is a parsing correction, not a source revision.
            if previous_specs != new_specs and facts(previous_specs) == facts(new_specs):
                prior = history.get(slug)
                if prior and prior['state'].get('specificationHash') == digest(previous_specs):
                    prior['state']['specificationHash'] = digest(new_specs)
                    prior['fingerprint'] = digest(prior['state'])
        numbered = sum(bool(r[1]) for r in rows)
        artists = len(rows) - numbered
        note = (f'All {numbered} printed numbered subject rows and {artists} unnumbered sketch artists are reconciled to physical PDF cells. '
                'Repeated multi-signer card numbers and original unlabelled actor/character/relic text columns are retained separately; counts represent source entries, not unique cards. '
                f'All {len(odds)} printed odds categories and the literal SKU 1 Pack Rate heading are retained. '
                'Exhaustive parallel-numbering coverage and a calendar release date have not been established.')
        if master:
            note += ' Skeleton Crew Auto Relic Black is printed as 1,249 without a ratio separator; it remains literal with no inferred probability. The full underlying Lothal Jedi Temple Mortis Gods Painting Puzzle caption is retained even though the printed cell clips it.'
        data.update(headers=HEADERS, rows=rows, rawPages=raw, unclassifiedLines=[], sha256=fingerprint,
                    sectionColumn=0, importKind='topps-grid-pdf', dedicatedParser=PARSER, coverageComplete=True,
                    odds=odds, formats=formats, oddsRawPages=odds_raw, oddsSha256=odds_hash,
                    oddsIssues=[], oddsLiteralExceptions=exceptions,
                    oddsParser=PARSER if master else 'scripts/official_odds_layout.py',
                    sourceSheets=[{'name': 'Official source reconciliation', 'notes': [['Source scope', note]]}])
        dp.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
        record.update(rowCount=len(rows), sections=len(sections), sha256=fingerprint,
                      importKind=data['importKind'], dedicatedParser=PARSER, coverageComplete=True,
                      odds=len(odds), formats=len(formats), oddsParser=data['oddsParser'],
                      oddsImportIssues=0, catalogEvidence=note, dataAudit=note)
        print(record['title'], numbered, 'numbered subject rows;', artists, 'artists;', len(odds), 'odds')
    cp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n')
    ip = ROOT / 'data/topps-product-official-catalog.json'
    inventory = json.loads(ip.read_text())
    updated = {r['slug']: r for r in catalog['sets'] if r['slug'] in SLUGS}
    ip.write_text(json.dumps([updated.get(r['slug'], r) for r in inventory], ensure_ascii=False, indent=2) + '\n')

if __name__ == '__main__':
    build()
