"""Retain Holiday Football's original number/name/team/rookie text objects."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from import_official_catalog import run, fetch, CACHE

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-holiday-football'
PARSER = 'scripts/import_topps_holiday_football_2026.py'
URL = 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Holiday_FB_Checklist.pdf?v=1790609327'
PRODUCT = 'https://www.topps.com/pages/topps-holiday-football'
PROOF = ROOT / 'data/parallel-audit-sources/holiday-football-2026-product-guides-20261020.json'
HEADERS = ['Checklist section', 'Card number', 'Name', 'Team', 'Rookie', 'Source page']
FAMILIES = {
    'BASE CARDS': 150, 'ROOKIES': 50,
    'BASE CARDS CHROME VARIATION': 150, 'ROOKIES CHROME VARIATION': 50,
    'BASE HOLIDAY BACK VARIATION SHORT PRINTS': 40,
    'ROOKIES HOLIDAY BACK VARIATION SHORT PRINTS': 10,
    'BASE HOLIDAY SPIRIT VARIATION': 40, 'ROOKIES HOLIDAY SPIRIT VARIATION': 10,
    'HIDDEN ELF': 25, 'SNOW GLOBE MOMENTS': 25, 'DECK THE FIELDS': 25,
    'FROZEN FIELDS': 25, 'BASE AUTOGRAPHS': 94, 'ROOKIE AUTOGRAPHS': 40,
    'DEAR SANTA': 29,
}


def read_cards(path):
    rows, raw, notes = [], [], []
    family = None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 16
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text() or ''})
            groups = collections.defaultdict(list)
            for char in page.chars:
                groups[round(char['matrix'][5], 2)].append(char)
            for y, chars in sorted(groups.items(), reverse=True):
                text = ''.join(c['text'] for c in chars).strip()
                if pn == 1 and y > 680:
                    notes.append([str(pn), text])
                    continue
                if all('Bold' in c['fontname'] for c in chars):
                    if text not in {'BASE', 'INSERT', 'AUTOGRAPHS'}:
                        assert text in FAMILIES, (pn, text)
                        family = text
                    continue
                starts = [0]
                for x in [133.32, 270.84]:
                    indices = [i for i, c in enumerate(chars) if abs(c['x0'] - x) < .02]
                    assert len(indices) == 1, (pn, y, x, text)
                    starts.append(indices[0])
                rookie = [i for i, c in enumerate(chars) if abs(c['x0'] - 422.64) < .02]
                assert len(rookie) <= 1
                starts += rookie
                assert starts == sorted(set(starts))
                cells = [''.join(c['text'] for c in chars[a:b]).strip()
                         for a, b in zip(starts, starts[1:] + [len(chars)])]
                if not rookie:
                    cells.append('')
                assert family and re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+', cells[0])
                assert cells[1] and cells[2] and cells[3] in {'', 'Rookie'}
                rows.append([family, *cells, str(pn)])
    assert collections.Counter(r[0] for r in rows) == FAMILIES
    assert len(rows) == len({tuple(r[:2]) for r in rows}) == 763
    assert sum(r[4] == 'Rookie' for r in rows) == 188
    return rows, raw, notes


def build():
    cp = ROOT / 'data/set-catalog.json'
    catalog = json.loads(cp.read_text())
    record = next((r for r in catalog['sets'] if r['slug'] == SLUG), None)
    if record is None:
        record = dict(title='2026 Topps Holiday Football', manufacturer='Topps / Bowman',
                      sport='football', year='2026', slug=SLUG, page='sets/' + SLUG + '.html',
                      sourcePage=PRODUCT, checklistUrl=URL, releaseStatus='Upcoming',
                      releaseDate=None, verified='2026-10-20', checklistFirstObserved='2026-10-20')
        record = run(record)
        catalog['sets'].append(record)
    blob = fetch(URL, CACHE / (SLUG + '.pdf'))
    digest = hashlib.sha256(blob).hexdigest()
    rows, raw, notes = read_cards(CACHE / (SLUG + '.pdf'))
    proof = json.loads(PROOF.read_text())
    assert proof['checklistSha256'] == digest
    evidence = dict(file=str(PROOF.relative_to(ROOT)),
                    sha256=hashlib.sha256(PROOF.read_bytes()).hexdigest(), source=PRODUCT)
    note = ('All 763 original subject rows across 15 sections retain separate printed card '
            'numbers, names, teams and 188 literal Rookie flags. Paper and Chrome each have '
            '150 veteran and 50 rookie entries. Printed team assignments remain unchanged. '
            'The guide calls Dear Santa all rookies, but DS-BT Brenen Thompson has no printed '
            'Rookie flag and remains blank. The guide URL/FAQ uses 2025-26 wording separately '
            'from the 2026 title. No pack odds or numeric serial ladder is published in the '
            'checked product/current global sources; exhaustive parallel eligibility remains incomplete.')
    data = dict(title=record['title'], headers=HEADERS, rows=rows,
                originalSubjectHeaders=HEADERS, originalSubjectRows=rows,
                rawPages=raw, sourceDocumentNotes=notes, unclassifiedLines=[],
                source=URL, sha256=digest, importKind='topps-grid-pdf',
                dedicatedParser=PARSER, sectionColumn=0, coverageComplete=True,
                odds=[], formats=[], formatNamesPublished=False, oddsUnitsPublished=False,
                publishedSpecifications=[], sourceObservation=evidence,
                sourceSheets=[dict(name='Official source reconciliation',
                                   notes=[[note], *[[g] for g in proof['remainingGaps']]])])
    dp = ROOT / 'data/imports' / (SLUG + '.json')
    dp.write_text(json.dumps(data, ensure_ascii=False) + '\n')
    record.update(status='Source table', tableData=str(dp.relative_to(ROOT)), rowCount=len(rows),
                  sections=len(FAMILIES), sha256=digest, importKind=data['importKind'],
                  dedicatedParser=PARSER, coverageComplete=True, sourceObservation=evidence,
                  catalogEvidence=note, dataAudit=note, odds=0, formats=0,
                  additionalSources=[{'label':'Official product guide','url':g['url']}
                                     for g in proof['facts']['guides']],
                  releaseStatus='Upcoming', releaseDate=None,
                  description='Paper and Chrome base programs, Holiday Back and Holiday Spirit '
                  'variations, Hidden Elf, winter inserts, autographs and Dear Santa relic autographs. '
                  'Browse original teams and literal rookie marks; pack odds and serial limits remain unavailable.')
    record.pop('importIssue', None)
    cp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    ip = ROOT / 'data/topps-product-official-catalog.json'
    inventory = json.loads(ip.read_text())
    inventory = [record if r['slug'] == SLUG else r for r in inventory]
    if not any(r['slug'] == SLUG for r in inventory):
        inventory.append(record)
    ip.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    print('Holiday Football: 763 original rows, 15 sections, 188 Rookie flags; odds and numbering unverified.')


if __name__ == '__main__':
    build()
