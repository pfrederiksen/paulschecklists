"""Reconcile the official MLS NOW All-Star bundle PDF with its physical columns."""
import datetime
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

import pdfplumber
import import_official_catalog as generic

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-mls-topps-now-all-star-game-set'
TITLE = '2026 All-Star Game Set - MLS Topps NOW®'
PAGE = 'https://www.topps.com/products/2026-all-star-game-set-mls-topps-now%C2%AE-11-card-set-1'
URL = 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/ASG_MLS_26_Checklist_1.pdf?v=1787975005'
EVIDENCE = 'data/parallel-audit-sources/mls-now-all-star-2026-product-20261017.json'
FAMILIES = ['Base cards', 'Base Autographs', 'Net-Jewel Autograph-Relic Cards', 'Net-Jewel Relic Cards']


def physical_rows(path):
    rows = []
    with pdfplumber.open(path) as doc:
        assert len(doc.pages) == 1, 'Review changed pagination before importing'
        page = doc.pages[0]
        assert (page.width, page.height) == (612, 792)
        words = page.extract_words()
        # Only printed left-column ASG codes anchor card rows. Physical bands
        # include the slightly lowered San Diego FC text without merging rows.
        anchors = [w for w in words if w['x0'] < 100 and re.fullmatch(r'ASG-[A-Z]+', w['text'])]
        for anchor in anchors:
            y = anchor['top']
            preceding = page.crop((45, 75, 250, y)).extract_text() or ''
            family = next((line for line in reversed(preceding.splitlines()) if line in FAMILIES), None)
            assert family, anchor
            cells = [(page.crop((left, y-0.5, right, y+13)).extract_text() or '').strip()
                     for left, right in [(45, 250), (250, 374.5), (374.5, 570)]]
            assert cells[0] == anchor['text'] and all(cells), cells
            assert all('\n' not in cell for cell in cells), cells
            rows.append([family, *cells, '1'])
        raw = [{'page': 1, 'text': page.extract_text()}]
    assert Counter(row[0] for row in rows) == dict(zip(FAMILIES, [10, 5, 9, 2]))
    assert len({row[1] for row in rows}) == len(rows) == 26
    return rows, raw


def build():
    path = generic.CACHE / (SLUG + '.pdf')
    subprocess.run(['curl', '-fsSL', '--retry', '2', '--max-time', '60', URL, '-o', str(path)], check=True)
    path.with_suffix('.pdf.url').write_text(URL)
    record = {'title': TITLE, 'manufacturer': 'Topps / Bowman', 'sport': 'soccer', 'year': '2026',
              'slug': SLUG, 'page': 'sets/' + SLUG + '.html', 'sourcePage': PAGE, 'checklistUrl': URL,
              'releaseStatus': 'Unverified', 'releaseDate': None, 'verified': datetime.date.today().isoformat()}
    rows, raw = physical_rows(path)
    destination = ROOT / 'data' / 'imports' / (SLUG + '.json')
    prior = destination.read_bytes() if destination.exists() else None
    try:
        record = generic.run(record)
        assert 'importIssue' not in record, record
        baseline = json.loads(destination.read_text())
    finally:
        # Generic parsing is an independent comparison, never a replacement
        # for a previously validated import if a later assertion fails.
        if prior is not None:
            destination.write_bytes(prior)
        elif destination.exists():
            destination.unlink()
    # The generic number regex mistakes two mixed-case Net-Jewel headings for
    # card codes. Their exact captions are physical family headings above rows.
    captions = [r for r in baseline['rows'] if r[1] == 'Net-Jewel']
    assert [r[2] for r in captions] == ['Autograph-Relic Cards', 'Relic Cards']
    baseline_rows = [r for r in baseline['rows'] if r[1] != 'Net-Jewel']
    assert [r[1] for r in rows] == [r[1] for r in baseline_rows]
    # Independent generic text order must retain every physical subject/team
    # glyph, including tightly spaced Mbokazi/Chicago and the Müller umlaut.
    compact = lambda text: re.sub(r'\s+', '', text)
    assert [compact(r[2] + r[3]) for r in rows] == [compact(r[2]) for r in baseline_rows]
    evidence_path = ROOT / EVIDENCE
    evidence = json.loads(evidence_path.read_text())
    assert evidence['url'] == PAGE and evidence['checklistUrl'] == URL
    fields = dict(line.split('  | ', 1) for line in evidence['lines'] if '  | ' in line)
    assert fields['Available From'] == 'Jul 27, 2026' and fields['Available Until'] == 'Aug 3, 2026'
    assert fields['Sub Type'] == 'Set' and fields['Product Year'] == '2026'
    statement = next(line for line in evidence['lines'] if line.startswith('The biggest and brightest'))
    qualification = ('Product-level bundle configuration; no per-card print run, pack probability or exact '
                     'family-wide numbering is inferred from this sentence. The 11-card configuration '
                     'contains ten base cards plus one additional card; the PDF lists 26 possible entries.')
    specifications = [{'name': 'Set-wide product configuration and sale dates',
                       'worksheet': 'Official product page · bundle scope, not per-card numbering',
                       'source': PAGE, 'headers': ['Official field', 'Published term', 'Qualification'],
                       'rows': [['Published bundle print run (title)', '2677', 'Published for the bundle; not assigned to each checklist entry.'],
                                ['Published distribution and numbering statement', statement, qualification],
                                *[[key, value, 'Original official Specs field; store availability is not a general release date.']
                                  for key, value in fields.items() if key != 'Download checklist']]}]
    payload = {'title': TITLE, 'headers': ['Checklist section', 'Card Number', 'Subject', 'Team', 'Source page'],
               'rows': rows, 'source': URL, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
               'rawPages': raw, 'importKind': 'topps-grid-pdf', 'sectionColumn': 0,
               'publishedSpecifications': specifications,
               'sourceProducts': [{**evidence, 'snapshotFile': EVIDENCE,
                                   'sha256': hashlib.sha256(evidence_path.read_bytes()).hexdigest()}]}
    (ROOT / record['tableData']).write_text(json.dumps(payload, ensure_ascii=False) + '\n')
    record.update(importKind='topps-grid-pdf', dedicatedParser='scripts/import_topps_now_mls_allstar_2026.py',
                  rowCount=26, sections=4, parallelData=True, publishedOdds=False, sha256=payload['sha256'],
                  description='A made-to-order 11-card bundle: ten base cards plus one additional card. The official checklist lists 26 entries across four programs. Bundle print run 2677 and July 27–August 3 sale dates remain product-level facts; pack odds and exhaustive parallel eligibility are unverified.',
                  catalogEvidence='Official product page links the complete 26-entry PDF. All printed card numbers, subjects and teams are imported. Available From July 27, 2026 establishes calendar-year inclusion, not a general release date. The product-level net-jewel 1/1 wording stays qualified and unjoined to individual families. No numeric pack odds or named base/autograph parallel ladder is published in the checked product page or current global odds catalog. Historical NOW series coverage remains partial.',
                  dataAudit='All 26 physical rows reconcile to independent PDF text: 10 Base cards, 5 Base Autographs, 9 Net-Jewel Autograph-Relic Cards and 2 Net-Jewel Relic Cards. Original Subject/Team cells are separate; no rookie flags or per-card print runs are inferred.')
    for name in ['topps-product-official-catalog.json', 'set-catalog.json']:
        file = ROOT / 'data' / name
        catalog = json.loads(file.read_text())
        sets = catalog['sets'] if isinstance(catalog, dict) else catalog
        index = next((i for i, item in enumerate(sets) if item['slug'] == SLUG), None)
        if index is None:
            sets.append(record)
        else:
            sets[index] = record
        file.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    print('Imported 26 MLS All-Star NOW PDF entries across four families; bundle-level terms remain qualified.')


if __name__ == '__main__':
    build()
