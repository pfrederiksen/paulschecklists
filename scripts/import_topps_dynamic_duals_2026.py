"""Preserve physical player/team cells, booklet continuations and ruled odds."""
import collections, hashlib, json, re, subprocess
from pathlib import Path
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-dynamic-duals-baseball'
CACHE = ROOT / 'data/catalog-sources/downloads'
BOOKLET = 'Dynamic "Dozen" Autograph Booklet'
FAMILIES = {'Base Cards': 55, 'Dynamic "Duels" Super Short-Printed Pairings': 5,
            'Fence Busters': 5, 'Future Forward': 5, 'Youth Impact': 10,
            BOOKLET: 1, 'Base Card Dual Autographs': 50}

def literal(chars):
    return ' '.join(''.join(c['text'] for c in chars).split())

def parse_cards(path):
    rows, raw, teams, signers, notes, family = [], [], [], [], [], None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 4
        for pn, page in enumerate(pdf.pages, 1):
            assert (page.width, page.height) == (612, 792)
            raw.append({'page': pn, 'text': page.extract_text()})
            groups = []
            for char in page.chars:
                line = next((line for line in groups if abs(line[0]['top'] - char['top']) < 1), None)
                if line is None:
                    groups.append([char])
                else:
                    line.append(char)
            for chars in sorted(groups, key=lambda line: line[0]['top']):
                text = literal(chars)
                if text in FAMILIES:
                    family = text
                    continue
                if family is None or text in {'Insert Cards', 'Autograph Content'} or text.startswith('Card #'):
                    notes.append({'page': pn, 'text': text})
                    continue
                # Drawing sequence, rather than x-sorting, keeps long player
                # cells separate even where glyphs overlap adjacent columns.
                origins = [96, 199] if family == BOOKLET else [96, 199, 293, 397]
                starts = [max(i for i, c in enumerate(chars) if abs(c['x0'] - x) < .01) for x in origins]
                assert starts == sorted(starts), (pn, text)
                cells = [literal(chars[:starts[0]])] + [literal(chars[start:end]) for start, end in zip(starts, starts[1:] + [len(chars)])]
                if family == BOOKLET:
                    code, name, team = cells
                    assert code in {'', 'DDO-01'} and name and team, cells
                    signers.append([name, team, str(pn)])
                    if code:
                        assert not any(r[1] == code for r in rows)
                        rows.append([family, code, name, str(pn), name, '', team, ''])
                        teams.append([team])
                    else:
                        assert rows[-1][1] == 'DDO-01'
                        rows[-1][2] += '; ' + name
                        rows[-1][4] += '; ' + name
                        rows[-1][6] += '; ' + team
                        if team not in teams[-1]:
                            teams[-1].append(team)
                else:
                    code, player1, player2, team1, team2 = cells
                    assert re.fullmatch(r'\d+(?:-A)?|(?:DD|FB|FF|YI)-\d+', code), (pn, cells)
                    assert all([player1, player2, team1, team2]), (pn, cells)
                    rows.append([family, code, player1 + ' / ' + player2, str(pn), player1, player2, team1, team2])
                    teams.append(list(dict.fromkeys([team1, team2])))
    assert collections.Counter(r[0] for r in rows) == FAMILIES
    assert len(rows) == len(teams) == 131 and len(signers) == 12
    assert [r[1] for r in rows if r[0] == 'Base Cards'] == [str(i) for i in range(1, 56)]
    assert [r[1] for r in rows if r[0] == 'Base Card Dual Autographs'] == [f'{i}-A' for i in range(1, 51)]
    return rows, raw, teams, signers, notes

def parse_odds(path):
    odds, raw = [], []
    aliases = [('BASE CARD DUAL AUTO VARIATION', 'Base Card Dual Autographs'),
               ('BASE CARD', 'Base Cards'),
               ('SUPER SHORT PRINTED DYNAMIC "DUEL" PAIRINGS', 'Dynamic "Duels" Super Short-Printed Pairings'),
               ('DYNAMIC DOZEN AUTOGRAPH BOOKLET', BOOKLET),
               ('FENCE BUSTERS', 'Fence Busters'), ('FUTURE FORWARD', 'Future Forward'), ('YOUTH IMPACT', 'Youth Impact')]
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 1
        page = pdf.pages[0]
        raw.append({'page': 1, 'text': page.extract_text()})
        tables = page.extract_tables()
        assert len(tables) == 1 and tables[0][0] == ['Description', 'Packs']
        for description, value in tables[0][1:]:
            description = ' '.join(description.split())
            assert description.startswith('26TDDB - ') and re.fullmatch(r'\d+:\d+', value)
            odd = {'name': description, 'values': {'Packs': value}, 'page': 1}
            category = description.removeprefix('26TDDB - ')
            odd['categoryName'] = category
            for prefix, family in aliases:
                if category == prefix or category.startswith(prefix + ' '):
                    odd['family'] = family
                    if category == prefix:
                        odd['familyBase'] = True
                    break
            if category.startswith('SHORT PRINT'):
                odd['family'] = 'Short Print'
            odds.append(odd)
    assert len(odds) == 37 and len({o['name'] for o in odds}) == 37
    return odds, ['Packs'], raw

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
    card_path, odds_path = CACHE / (SLUG + '.pdf'), CACHE / (SLUG + '-odds.pdf')
    card_hash, odds_hash = refresh(record['checklistUrl'], card_path), refresh(record['oddsUrl'], odds_path)
    rows, raw, teams, signers, notes = parse_cards(card_path)
    odds, formats, odds_raw = parse_odds(odds_path)
    payload = {'title': record['title'], 'headers': ['Checklist section', 'Card number', 'Player / subjects', 'Source page', 'Player 1', 'Player 2', 'Team 1', 'Team 2'],
               'rows': rows, 'teamColumns': [6, 7], 'rowTeams': teams, 'bookletSigners': signers,
               'source': record['checklistUrl'], 'sha256': card_hash, 'rawPages': raw,
               'unclassifiedLines': notes, 'importKind': 'pdf', 'sectionColumn': 0,
               'odds': odds, 'formats': formats, 'oddsSource': record['oddsUrl'], 'oddsSha256': odds_hash,
               'oddsRawPages': odds_raw, 'oddsIssues': [], 'coverageComplete': False,
               'dedicatedParser': 'scripts/import_topps_dynamic_duals_2026.py'}
    (ROOT / record['tableData']).write_text(json.dumps(payload, ensure_ascii=False) + '\n')
    record.update(rowCount=131, sections=7, odds=37, formats=1, sha256=card_hash,
                  sourcePage='https://www.topps.com/pages/topps-mlb-dynamic-duals',
                  dedicatedParser=payload['dedicatedParser'], coverageComplete=False,
                  dataAudit='All 131 card numbers, seven printed subsets, both player/team columns and all 12 DDO-01 signer continuations reconciled to physical PDF cells. All 37 Description/Packs odds categories retained, including the production-code dash. No rookie flags, serial limits or SP eligibility inferred.',
                  catalogEvidence='Official Topps product page and checklist. Exact release date is not verified. The single published odds column is Packs; it does not name a Hobby format. Short Print odds remain a separate published family because the checklist does not label individual base cards as short prints. DDO-01 retains all 12 printed signers on its one booklet card. Serial limits and exhaustive parallel coverage require further official specification reconciliation.')
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    inventory_path = ROOT / 'data/topps-product-official-catalog.json'
    inventory = json.loads(inventory_path.read_text())
    inventory = [r for r in inventory if r['slug'] != SLUG] + [record]
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    print('Imported 131 Dynamic Duals cards, seven subsets, 12 booklet signers and 37 literal Packs odds categories.')

if __name__ == '__main__':
    build()
