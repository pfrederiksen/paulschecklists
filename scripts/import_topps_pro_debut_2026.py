"""Import the 2026 Pro Debut PDF by its original card/name/team origins."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from import_official_catalog import run, fetch, CACHE

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-pro-debut-baseball'
PARSER = 'scripts/import_topps_pro_debut_2026.py'
URL = 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Pro_Debut_Checklist.pdf?v=1792417707'
PRODUCT = 'https://www.topps.com/pages/topps-pro-debut-baseball'
PROOF = ROOT / 'data/parallel-audit-sources/pro-debut-baseball-2026-product-20261019.json'
HEADERS = ['Checklist section', 'Card number', 'Name', 'Team', 'Source page']
FAMILIES = {
    'BASE CARDS': 200, 'BASE CARDS CHROME VARIATION': 200,
    '2025 ARIZONA FALL LEAGUE STARS': 20, 'PIPELINE PAIRINGS': 48,
    'PRO DEBUT GAMERS': 24, 'BALLPARK PROMOS': 22, 'STARS OF MILB': 24,
    'BASE CARDS AUTOGRAPH PARALLEL': 172,
    '2025 ARIZONA FALL LEAGUE STARS AUTOGRAPH PARALLEL': 17,
    'PRO DEBUT GAMERS AUTOGRAPH PARALLEL': 20,
    'BASE CARDS CHROME AUTOGRAPHS': 159, 'FUTURE CORNERSTONES': 26,
    'PRO DEBUT DUAL AUTOGRAPHS': 30, 'PRO DEBUT TRIPLE AUTOGRAPHS': 42,
    'STARS OF MILB AUTOGRAPH PARALLEL': 19,
    'PRO DEBUT JUMBO AUTOGRAPH RELIC': 21,
}


def read_cards(path):
    rows, raw, notes = [], [], []
    family = None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 20
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text() or ''})
            groups = collections.defaultdict(list)
            for char in page.chars:
                groups[round(char['matrix'][5], 2)].append(char)
            for y, chars in sorted(groups.items(), reverse=True):
                text = ''.join(c['text'] for c in chars).strip()
                if pn == 1 and y > 725:
                    notes.append([str(pn), text])
                    continue
                if all('Bold' in c['fontname'] for c in chars):
                    if text not in {'BASE', 'INSERT', 'AUTOGRAPH', 'AUTOGRAPH RELIC'}:
                        assert text in FAMILIES, (pn, text)
                        family = text
                    continue
                starts = []
                for x in [53.04, 133.34, 270.89]:
                    indices = [i for i, c in enumerate(chars) if abs(c['x0'] - x) < .02]
                    assert len(indices) == 1, (pn, y, x, text)
                    starts.append(indices[0])
                assert starts == sorted(starts) and starts[0] == 0
                cells = [''.join(c['text'] for c in chars[a:b]).strip()
                         for a, b in zip(starts, starts[1:] + [len(chars)])]
                assert family and re.fullmatch(r'[A-Z]+-[A-Z0-9]+', cells[0])
                assert cells[1] and cells[2]
                rows.append([family, *cells, str(pn)])
    assert collections.Counter(r[0] for r in rows) == FAMILIES
    assert len(rows) == 1044 and len({tuple(r[:2]) for r in rows}) == 977
    return rows, raw, notes


def build():
    cp = ROOT / 'data/set-catalog.json'
    catalog = json.loads(cp.read_text())
    record = next((r for r in catalog['sets'] if r['slug'] == SLUG), None)
    if record is None:
        record = dict(title='2026 Topps Pro Debut Baseball', manufacturer='Topps / Bowman',
                      sport='baseball', year='2026', slug=SLUG, page='sets/' + SLUG + '.html',
                      sourcePage=PRODUCT, checklistUrl=URL, releaseStatus='Upcoming',
                      releaseDate=None, verified='2026-10-19')
        # Bootstrap with the shared official importer, then replace generic text
        # rows with verified original physical cells before publishing anything.
        record = run(record)
        assert record.get('tableData'), record
        catalog['sets'].append(record)
    path = CACHE / (SLUG + '.pdf')
    blob = fetch(URL, path)
    digest = hashlib.sha256(blob).hexdigest()
    rows, raw, notes = read_cards(path)
    proof = json.loads(PROOF.read_text())
    assert proof['checklistSha256'] == digest
    evidence = dict(file=str(PROOF.relative_to(ROOT)),
                    sha256=hashlib.sha256(PROOF.read_bytes()).hexdigest(), source=PRODUCT)
    note = ('All 1,044 physical subject rows / 977 family-card identities across 16 sections '
            'are reconciled to separate original Name and Team cells. Both 200-card paper and '
            'Chrome base programs, all 24 two-subject Pipeline Pairings, 15 dual autograph cards '
            'and 14 triple autograph cards are retained. The 2025 Arizona Fall League headings '
            'belong to this 2026 product. No rookie field is published. October 19 is explicitly '
            'a preorder, not a general release date. No official odds link or numeric parallel '
            'ladder was published in the checked current product/global sources; exhaustive '
            'parallel and release coverage remain unverified.')
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
                  releaseStatus='Upcoming', releaseDate=None,
                  description='Separate 200-card paper and Chrome base programs, Minor League '
                  'inserts and multi-signer autographs. Browse original names and teams; '
                  'October 19 is a preorder. Pack odds and numeric parallel limits remain unavailable.')
    cp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    ip = ROOT / 'data/topps-product-official-catalog.json'
    inventory = json.loads(ip.read_text())
    inventory = [record if r['slug'] == SLUG else r for r in inventory]
    if not any(r['slug'] == SLUG for r in inventory):
        inventory.append(record)
    ip.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    ip = ROOT / 'data/topps-official-catalog.json'
    inventory = json.loads(ip.read_text())
    if not any(r['url'] == URL for r in inventory):
        inventory.append(dict(id=SLUG, title=record['title'], url=URL))
    ip.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    print('Pro Debut: 1,044 physical rows, 977 identities, 16 families; preorder remains separate from release.')


if __name__ == '__main__':
    build()
