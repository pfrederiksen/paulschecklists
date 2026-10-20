"""Reconcile Holiday Baseball's original Name / Team / Rookie cells and guide units."""
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pdfplumber
from import_official_catalog import run, fetch

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-holiday-baseball'
PARSER = 'scripts/import_topps_holiday_2026.py'
PROOF = ROOT / 'data/parallel-audit-sources/holiday-baseball-2026-guides-20261014.json'
ODDS_PROOF = ROOT / 'data/parallel-audit-sources/holiday-baseball-2026-odds-20261020.json'
ORIGINS = [136.94, 274.49, 426.31]


def read_odds(path):
    """Preserve all physical cells; column formats do not supply a ratio unit."""
    proof = json.loads(ODDS_PROOF.read_text())
    formats = proof['formats']
    rows, raw = [], []
    aliases = proof['familyAliases']
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 2
        for pn, page in enumerate(pdf.pages, 1):
            tables = page.find_tables()
            assert len(tables) == 1
            cells = tables[0].extract()
            assert cells[0] == ['Card', *formats]
            assert len(cells) - 1 == [49, 17][pn - 1]
            raw.append({'page': pn, 'text': page.extract_text()})
            for cells in cells[1:]:
                assert len(cells) == 4 and cells[0]
                name = cells[0]
                assert all(v == '—' or re.fullmatch(r'\d+:[\d,.]+', v) for v in cells[1:]), cells
                # Autograph odds are published but the checklist has no autograph
                # roster. An explicit separate family prevents prefix joins to base/relic cards.
                if 'AUTOGRAPH' in name:
                    base = next(s for s in proof['unjoinedPrograms'] if name == s or name.startswith(s + ' '))
                    family = base + ' (roster not published)'
                    qualification = 'Odds program has no separately published autograph roster; no subject eligibility is inferred.'
                else:
                    base = next((s for s in sorted(aliases, key=len, reverse=True) if name == s or name.startswith(s + ' ')), None)
                    assert base, name
                    family = aliases[base]
                    qualification = None
                entry = {'name': name, 'values': {f: None if v == '—' else v for f, v in zip(formats, cells[1:])},
                         'page': pn, 'family': family, 'familyBase': name == base}
                if qualification:
                    entry['qualification'] = qualification
                rows.append(entry)
    assert len(rows) == len({r['name'] for r in rows}) == 66
    assert sum(v is None for r in rows for v in r['values'].values()) == 121
    return rows, formats, raw


def read_cards(path):
    rows, raw = [], []
    section = None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 14
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text()})
            lines = collections.defaultdict(list)
            for char in page.chars:
                lines[round(char['top'], 1)].append(char)
            for y, chars in sorted(lines.items()):
                if pn == 1 and y < 144:
                    continue
                text = ''.join(c['text'] for c in chars).strip()
                if all('Bold' in c['fontname'] for c in chars):
                    assert text == text.upper(), (pn, y, text)
                    if text not in ['INSERT', 'RELIC']:
                        section = text
                    continue
                starts = []
                for col, x in enumerate(ORIGINS, 1):
                    matches = [i for i, c in enumerate(chars) if abs(c['x0'] - x) < .03]
                    if matches:
                        starts.append((max(matches), col))
                assert starts and starts[0][1] == 1, (pn, y, text)
                cells = [''.join(c['text'] for c in chars[:starts[0][0]]).strip(), '', '', '']
                assert re.fullmatch(r'H\d+|HC\d+|[A-Z]+-[A-Z0-9]+', cells[0]), (pn, y, cells)
                for j, (idx, col) in enumerate(starts):
                    end = starts[j + 1][0] if j + 1 < len(starts) else len(chars)
                    cells[col] = ''.join(c['text'] for c in chars[idx:end]).strip()
                assert section and cells[1] and cells[-1] in ['', 'Rookie'], (pn, y, cells)
                rows.append([section, *cells, str(pn)])
    assert len(rows) == 640 and len({r[0] for r in rows}) == 12
    assert sum(r[4] == 'Rookie' for r in rows) == 191
    return rows, raw


def build():
    catalog_path = ROOT / 'data/set-catalog.json'
    catalog = json.loads(catalog_path.read_text())
    record = next(s for s in catalog['sets'] if s['slug'] == SLUG)
    assert run(dict(record)) == record, 'The generic importer must preserve this dedicated dataset'
    path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
    temporary = path.with_suffix('.part')
    subprocess.run(['curl', '-sLf', '--retry', '2', '--max-time', '45', record['checklistUrl'], '-o', str(temporary)], check=True)
    temporary.replace(path)
    rows, raw = read_cards(path)
    proof = json.loads(PROOF.read_text())
    proof_hash = hashlib.sha256(PROOF.read_bytes()).hexdigest()

    def table(name, headers, contents):
        return {'name': name, 'worksheet': 'Official guide; retain source units and scope',
                'headers': [*headers, 'Official source'], 'rows': [[*r, proof['source']] for r in contents],
                'source': proof['source'], 'evidenceFile': str(PROOF.relative_to(ROOT)), 'evidenceSha256': proof_hash}

    note = ('All 640 physical subject rows across 12 sections reconciled, retaining both 200-card base programs, '
            '191 printed Rookie marks, five faux relic subjects with blank teams and the printed H202 variation. '
            'Official guide parallel programs and box/tin/calendar/case units are preserved separately from pack odds. '
            'The five-player Hidden Elf guide description conflicts with the 25 separately named PDF subjects; '
            'the guides also describe autographs absent from the current PDF roster. All 66 literal odds categories across '
            'MEGA BOX / COLLECTOR TIN / ADVENT CALENDAR are imported with null cells and no named ratio unit. '
            'Autograph odds remain separate from non-autograph rosters. No serial limits are inferred; '
            'exhaustive parallel reconciliation remains pending.')
    data_path = ROOT / record['tableData']
    data = json.loads(data_path.read_text())
    odds_proof = json.loads(ODDS_PROOF.read_text())
    odds_path = path.with_name(SLUG + '-odds.pdf')
    odds_blob = fetch(odds_proof['url'], odds_path)
    assert hashlib.sha256(odds_blob).hexdigest() == odds_proof['sha256']
    odds, formats, odds_raw = read_odds(odds_path)
    data.update(headers=['Checklist section', 'Card number', 'Name', 'Team', 'Rookie', 'Source page'],
                rows=rows, rawPages=raw, unclassifiedLines=[], sectionColumn=0,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(), importKind='topps-grid-pdf', dedicatedParser=PARSER,
                publishedSpecifications=[
                    table('Box, tin and calendar contents (not pack odds)', ['Published format', 'Published configuration'], proof['configuration']),
                    table('Published distribution terms (retain source units)', ['Checklist family', 'Published term', 'Source qualification'], proof['distribution'])
                ], sourceSheets=[{'name': 'Official source reconciliation', 'notes': [[note]]}],
                productConfigurationEvidence={'file': str(PROOF.relative_to(ROOT)), 'sha256': proof_hash, 'source': proof['source']},
                odds=odds, formats=formats, oddsSource=odds_proof['url'], oddsSha256=odds_proof['sha256'],
                oddsRawPages=odds_raw, oddsIssues=[], oddsUnitsPublished=False, formatNamesPublished=True,
                oddsEvidence={'file': str(ODDS_PROOF.relative_to(ROOT)), 'sha256': hashlib.sha256(ODDS_PROOF.read_bytes()).hexdigest()})
    data_path.write_text(json.dumps(data, ensure_ascii=False) + '\n')
    record.update(sourcePage=proof['productSource'], releaseStatus='Upcoming', releaseDate=proof['releaseDate'],
                  releaseEvidence=proof['collectorGuide'], importKind=data['importKind'], dedicatedParser=PARSER,
                  sha256=data['sha256'], rowCount=640, sections=12, catalogEvidence=note, dataAudit=note,
                  odds=66, formats=3, oddsUrl=odds_proof['url'], oddsImportIssues=0,
                  description='Two 200-card paper and Chrome base programs, holiday variations, ornaments, Hidden Elf, Making the Nice List and relics. Browse original player, team and rookie fields, 66 literal odds categories across three formats and qualified guide terms; serial limits remain unverified.')
    for name in ['set-catalog.json', 'topps-product-official-catalog.json']:
        p = ROOT / 'data' / name
        obj = json.loads(p.read_text())
        items = obj['sets'] if isinstance(obj, dict) else obj
        for i, item in enumerate(items):
            if item['slug'] == SLUG:
                items[i] = record
                break
        else:
            items.append(record)
        p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')
    rp = ROOT / 'data/parallel-specifications.json'
    registry = json.loads(rp.read_text())
    registry['sets'][SLUG] = [dict(family=family, name=name, numbering=numbering, source=proof['source'],
                                  qualification=qualifier + '. Individual-card eligibility is not inferred.',
                                  sourceHeading='What’s Inside / format descriptions / FAQs',
                                  evidenceFile=str(PROOF.relative_to(ROOT)), evidenceSha256=proof_hash)
                              for family, name, numbering, qualifier in proof['parallelPrograms']]
    for spec in registry['sets'][SLUG]:
        name = odds_proof['guideOddsJoins'].get(spec['name'])
        if name:
            assert any(o['name'] == name and o['family'] == spec['family'] for o in odds)
            spec['oddsName'] = name
    registry['conflicts'] = [c for c in registry.get('conflicts', []) if c['slug'] != SLUG] + [
        {'slug': SLUG, 'family': 'HIDDEN ELF', 'issue': proof['remainingGaps'][2], 'source': proof['source'],
         'evidenceFile': str(PROOF.relative_to(ROOT)), 'evidenceSha256': proof_hash},
        {'slug': SLUG, 'family': 'AUTOGRAPHS', 'issue': proof['remainingGaps'][3], 'source': proof['collectorGuide'],
         'evidenceFile': str(PROOF.relative_to(ROOT)), 'evidenceSha256': proof_hash}
    ]
    rp.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + '\n')
    print('Reconciled Holiday Baseball: 640 rows, 12 sections, 191 Rookie marks; all 66 three-column odds, 121 nulls and 14 qualified guide programs. Ratio unit and serial limits remain unstated.')


if __name__ == '__main__':
    build()
