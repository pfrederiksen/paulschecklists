"""Reconcile Heritage Football's physical columns, annotations and qualified guides."""
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2026-topps-heritage-football'
PARSER = 'scripts/import_topps_heritage_football_2026.py'
PROOF = ROOT / 'data/parallel-audit-sources/heritage-football-2026-guides-20261014.json'
ORIGINS = [76.8, 275.2, 389.6]
ANNOTATIONS = {'', 'Rookie', 'Record Breakers', 'League Leaders', 'Team Cards', 'Championship Games', 'Super Bowl LX'}
ANNOTATIONS |= {a + ' Chrome Variation' for a in ANNOTATIONS if a not in ['', 'Rookie']}


def read_cards(path):
    original, raw = [], []
    section = None
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == 22
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text()})
            lines = collections.defaultdict(list)
            for char in page.chars:
                lines[round(char['top'], 1)].append(char)
            for y, chars in sorted(lines.items()):
                if pn == 1 and y < 94:
                    continue
                text = ''.join(c['text'] for c in chars).strip()
                if all('Bold' in c['fontname'] for c in chars):
                    assert text == text.upper(), (pn, y, text)
                    if text not in ['BASE', 'INSERT', 'AUTOGRAPH', 'RELIC', 'AUTOGRAPH RELIC']:
                        section = text
                    continue
                starts = []
                for col, x in enumerate(ORIGINS, 1):
                    matches = [i for i, c in enumerate(chars) if abs(c['x0'] - x) < .03]
                    if matches:
                        starts.append((max(matches), col))
                assert starts and starts[0][1] == 1, (pn, y, text)
                cells = [''.join(c['text'] for c in chars[:starts[0][0]]).strip(), '', '', '']
                assert re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+', cells[0]), (pn, y, cells)
                # Preserve drawing order: long redemption subjects overlap the team column.
                for j, (idx, col) in enumerate(starts):
                    end = starts[j + 1][0] if j + 1 < len(starts) else len(chars)
                    cells[col] = ''.join(c['text'] for c in chars[idx:end]).strip()
                assert section and cells[1] and cells[-1] in ANNOTATIONS, (pn, y, cells)
                original.append([section, *cells, str(pn)])
    assert len(original) == 1487 and len({r[0] for r in original}) == 30
    assert sum(r[4] == 'Rookie' for r in original) == 485
    rows = [[r[0], r[1], r[2], r[3], 'Rookie' if r[4] == 'Rookie' else '', r[4], r[5]] for r in original]
    return rows, original, raw


def build():
    catalog = json.loads((ROOT / 'data/set-catalog.json').read_text())
    record = next(s for s in catalog['sets'] if s['slug'] == SLUG)
    path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
    temporary = path.with_suffix('.part')
    subprocess.run(['curl', '-sLf', '--retry', '2', '--max-time', '45', record['checklistUrl'], '-o', str(temporary)], check=True)
    temporary.replace(path)
    rows, original, raw = read_cards(path)
    proof = json.loads(PROOF.read_text())
    proof_hash = hashlib.sha256(PROOF.read_bytes()).hexdigest()

    def table(name, headers, contents):
        return {'name': name, 'worksheet': 'Official guide; retain source units and scope',
                'headers': [*headers, 'Official source'], 'rows': [[*r, proof['source']] for r in contents],
                'source': proof['source'], 'evidenceFile': str(PROOF.relative_to(ROOT)), 'evidenceSha256': proof_hash}

    note = ('All 1,487 physical subject rows across 30 sections reconciled, retaining the 400-number paper base and '
            '399-number Chrome program (408 subject rows each). Chrome prints two 142 entries and omits 259; '
            'repeated League Leaders numbers remain unchanged. Keep 485 literal Rookie marks, subset annotations, '
            'six blank game-card team cells and all 34 long Walter Payton redemption subjects. '
            'Original team assignments remain unchanged. Gold /50 applies only to Heritage Rookie Autographs. '
            'Guide-described cut numbering remains unassigned among CA-WP1–CA-WP5; Nickname/No Name and missing '
            '1976 buyback-autograph roster joins remain unresolved. Box contents and format-specific availability '
            'remain separate from pack odds; no odds PDF verified and exhaustive parallel reconciliation remains pending.')
    data_path = ROOT / record['tableData']
    data = json.loads(data_path.read_text())
    assert not data.get('odds'), 'Review newly published odds before replacing this import'
    data.update(headers=['Checklist section', 'Card number', 'Name', 'Team', 'Rookie', 'Published annotation', 'Source page'],
                rows=rows, originalSubjectHeaders=['Checklist section', 'Card number', 'Name', 'Team', 'Published annotation', 'Source page'],
                originalSubjectRows=original, rawPages=raw, unclassifiedLines=[], sectionColumn=0,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(), importKind='topps-grid-pdf', dedicatedParser=PARSER,
                publishedSpecifications=[
                    table('Box contents and availability (not pack odds)', ['Published format', 'Published configuration', 'Official availability'], proof['configuration']),
                    table('CUT SIGNATURES', ['Guide-described card', 'Published limit (guide scope)', 'Checklist reconciliation'], proof['qualifiedLimits']),
                    table('Guide-only autograph programs (roster reconciliation pending)', ['Guide-described program', 'Published signers', 'Checklist reconciliation'], proof['guideOnlyPrograms'])
                ], sourceSheets=[{'name': 'Official source reconciliation', 'notes': [[note]]}],
                productConfigurationEvidence={'file': str(PROOF.relative_to(ROOT)), 'sha256': proof_hash, 'source': proof['source']})
    data_path.write_text(json.dumps(data, ensure_ascii=False) + '\n')
    record.update(sourcePage=proof['productSource'], releaseStatus='Upcoming', releaseDate=proof['releaseDate'],
                  releaseEvidence=proof['productSource'], importKind=data['importKind'], dedicatedParser=PARSER,
                  sha256=data['sha256'], rowCount=1487, sections=30, catalogEvidence=note, dataAudit=note,
                  description='A 400-card vintage-design NFL checklist with separate Chrome, variation, autograph, relic and redemption programs. Browse original player, team and rookie fields, plus family-scoped parallel details; Hobby and Value availability starts October 21, with Mega on November 4.')
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
    entries = [dict(family=family, name=name, numbering=numbering, source=proof['source'],
                    qualification=qualifier + '. Individual-card eligibility is not inferred.',
                    sourceHeading='What’s Inside / format descriptions / FAQs',
                    evidenceFile=str(PROOF.relative_to(ROOT)), evidenceSha256=proof_hash)
               for family, name, numbering, qualifier in proof['parallelPrograms']]
    entries += [dict(family=family, name=name, numbering=numbering, source=proof['historySource'],
                     qualification=qualifier, sourceHeading='Collector FAQs / Heritage Rookie Autographs',
                     evidenceFile=str(PROOF.relative_to(ROOT)), evidenceSha256=proof_hash)
                for family, name, numbering, qualifier in proof['exactNumbering']]
    registry['sets'][SLUG] = entries
    registry['conflicts'] = [c for c in registry.get('conflicts', []) if c['slug'] != SLUG] + [
        {'slug': SLUG, 'family': family, 'issue': proof['remainingGaps'][index], 'source': proof['source'],
         'evidenceFile': str(PROOF.relative_to(ROOT)), 'evidenceSha256': proof_hash}
        for family, index in [('BASE CARDS NO NAME VARIATION', 1), ('1976 ORIGINAL BUYBACK AUTOGRAPHS', 2), ('CUT SIGNATURES', 3)]
    ]
    registry['conflicts'].append({'slug': SLUG, 'family': 'BASE CARDS CHROME VARIATION',
                                  'issue': proof['remainingGaps'][5], 'source': proof['checklistSource'],
                                  'evidenceFile': str(PROOF.relative_to(ROOT)), 'evidenceSha256': proof_hash})
    rp.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + '\n')
    print('Reconciled Heritage Football: 1487 rows, 30 sections, 485 Rookie marks; 19 guide-scoped specifications, including Gold /50 in its exact autograph family.')


if __name__ == '__main__':
    build()
