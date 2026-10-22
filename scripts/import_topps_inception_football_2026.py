"""Reconcile Inception Football's retained generic import with physical PDF cells."""
import collections
import hashlib
import json
import re
from pathlib import Path

import pdfplumber
from import_official_catalog import clean
from import_topps_tribute_2026 import acquire, text

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-inception-football'
PARSER = 'scripts/import_topps_inception_football_2026.py'
PROOF = ROOT / 'data/parallel-audit-sources/inception-football-physical-20261022.json'
FAMILIES = {
    'BASE CARDS': 150, 'ROOKIE': 50, 'LAUNCH': 25, 'GENESIS': 24,
    'ROOKIE SHORT PRINTS': 25, 'ROOKIE AUTOGRAPHS': 46,
    'ROOKIE AUTOGRAPH VARIATIONS': 20, 'INCEPTION SILVER SIGNINGS': 10,
    'DAWN OF GREATNESS AUTOGRAPHS': 20, 'IMMERSION AUTOGRAPHS': 16,
    'CHARGED PARTICLES': 12, 'DUAL ROOKIE AUTOGRAPHS': 14,
    'NFL DRAFT COMMISIONER COMBO': 16, 'PROVENANCE PATCH AUTOGRAPHS': 43,
    'ROOKIE JUMBO RELIC AUTOGRAPHS': 39,
    'DUAL ROOKIE RELIC AUTOGRAPHED BOOK': 16,
    'NFL FIRST MILESTONE AUTOGRAPH RELIC': 12,
}
HEADERS = ['Checklist section', 'Card number', 'Name', 'Team', 'Rookie', 'Source page']


def read_cards(path):
    rows, raw, notes = [], [], []
    family = None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 12
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text()})
            lines = collections.defaultdict(list)
            for char in page.chars:
                lines[round(char['top'], 1)].append(char)
            for y, chars in sorted(lines.items()):
                line = text(chars)
                if pn == 1 and y < 110:
                    notes.append([str(pn), line])
                    continue
                if line in FAMILIES:
                    family = line
                    continue
                if line in {'BASE', 'INSERT', 'AUTOGRAPH', 'AUTOGRAPH RELIC'}:
                    continue
                assert family, (pn, line)
                # Original text-object starts preserve Name/Team boundaries,
                # independently of word wrapping or horizontally long names.
                a = next(i for i, c in enumerate(chars) if abs(c['x0'] - 132.62) < .02)
                b = next(i for i, c in enumerate(chars) if abs(c['x0'] - 269.45) < .02)
                c = next((i for i, ch in enumerate(chars) if abs(ch['x0'] - 421.27) < .02), len(chars))
                number, name, team, rookie = [text(part) for part in
                                             [chars[:a], chars[a:b], chars[b:c], chars[c:]]]
                assert re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+', number), (pn, line)
                assert name and team and rookie in {'', 'Rookie'}, (pn, line)
                rows.append([family, number, name, team, rookie, str(pn)])
    assert len(rows) == 538 and collections.Counter(r[0] for r in rows) == FAMILIES
    assert len({tuple(r[:2]) for r in rows}) == 523
    assert sum(r[4] == 'Rookie' for r in rows) == 340
    assert [int(r[1]) for r in rows if r[0] in {'BASE CARDS', 'ROOKIE'}] == list(range(1, 201))
    return rows, raw, notes


def build():
    proof = json.loads(PROOF.read_text())
    ph = hashlib.sha256(PROOF.read_bytes()).hexdigest()
    cp = ROOT / 'data/set-catalog.json'
    catalog = json.loads(cp.read_text())
    record = next(r for r in catalog['sets'] if r['slug'] == SLUG)
    dp = ROOT / record['tableData']
    data = json.loads(dp.read_text())
    assert record['checklistUrl'] == proof['source']
    path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
    digest = acquire(record['checklistUrl'], path)
    assert digest == proof['checklistSha256'], 'New source requires a reviewed physical reconciliation'
    rows, raw, notes = read_cards(path)
    if data['headers'] == HEADERS:
        assert rows == data['rows'], 'Changed physical rows require review before replacement'
    else:
        assert data['headers'] == ['Checklist section', 'Card number',
                                   'Official description (player / team / notes)', 'Source page']
        flattened = [[r[0], r[1], clean(' '.join(r[2:5])), r[5]] for r in rows]
        assert flattened == data['rows'], 'Physical cells differ from the retained generic source rows'
    assert not data.get('odds'), 'An odds update needs a separately reviewed parser'
    note = ('All 538 physical subject rows / 523 family-card identities across 17 sections retain '
            'separate Name, Team and Rookie cells. All 340 Rookie marks are literal PDF values; '
            'no flags or teams are inferred or propagated. BASE CARDS prints 1–150 and ROOKIE 151–200. '
            'Both subjects remain attached to every repeated dual code, including DRA-KS and DRRA-PL '
            'across page breaks. Original historical teams and the printed COMMISIONER heading are preserved. '
            'Published pack odds and formats are unavailable in the retained checked sources. '
            'Full guide verification and exact-family parallel numbering remain pending; search candidates '
            'are not imported as serial limits. The verified November 6 calendar schedule remains separate '
            'from checklist availability.')
    data.update(headers=HEADERS, rows=rows, originalSubjectHeaders=HEADERS,
                originalSubjectRows=rows, rawPages=raw, sourceDocumentNotes=notes,
                unclassifiedLines=[], source=record['checklistUrl'], sha256=digest,
                importKind='topps-grid-pdf', sectionColumn=0, dedicatedParser=PARSER,
                coverageComplete=True, coverageScope='All rows in the cited 12-page checklist PDF only.',
                odds=[], formats=[], formatNamesPublished=False, oddsUnitsPublished=False,
                parallelSpecifications=[], sourceSheets=[{'name': 'Official source reconciliation',
                    'notes': [[note], [proof['remainingGap']]]}])
    record.update(rowCount=538, sections=17, sha256=digest, importKind='topps-grid-pdf',
                  dedicatedParser=PARSER, coverageComplete=True, parallelData=False,
                  publishedOdds=False, verified=proof['observed'], dataAudit=note,
                  catalogEvidence=note, sourceObservation={'file': str(PROOF.relative_to(ROOT)),
                    'sha256': ph, 'source': proof['source']})
    # Keep the separately verified release-calendar mapping unchanged.
    assert record['releaseDate'] == '2026-11-06' and record['releaseStatus'] == 'Upcoming'
    assert record.get('verifiedRelease')
    dp.write_text(json.dumps(data, ensure_ascii=False) + '\n')
    cp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    ip = ROOT / 'data/topps-product-official-catalog.json'
    inventory = json.loads(ip.read_text())
    inventory = [record if r['slug'] == SLUG else r for r in inventory] if any(
        r['slug'] == SLUG for r in inventory) else inventory + [record]
    ip.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    print('Inception Football: 538 physical subjects / 523 identities, 17 sections, '
          '340 literal Rookie marks; original Name/Team cells and all dual subjects retained.')


if __name__ == '__main__':
    build()
