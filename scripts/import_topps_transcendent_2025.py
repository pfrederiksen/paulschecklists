"""Retain Transcendent's original glyph columns, including overlapping cells."""
import collections, hashlib, json, re, subprocess
from pathlib import Path
import pdfplumber
ROOT = Path(__file__).resolve().parents[1]
SLUG = 'topps-bowman-2025-topps-transcendent-collection-baseball'
PARSER = 'scripts/import_topps_transcendent_2025.py'
OUTER = {'BASE', 'INSERT', 'AUTOGRAPH', 'AUTOGRAPH RELIC', 'RELIC'}
ORIGINS = [132.62, 269.45, 421.27]

def read_cards(path):
 rows, raw = [], []
 section = None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages) == 27
  for pn, page in enumerate(pdf.pages, 1):
   raw.append({'page': pn, 'text': page.extract_text()})
   lines = collections.defaultdict(list)
   for char in page.chars: lines[round(char['top'], 1)].append(char)
   for y, chars in sorted(lines.items()):
    if pn == 1 and y < 95: continue
    starts = []
    for column, origin in enumerate(ORIGINS, 1):
     indices = [i for i, c in enumerate(chars) if abs(c['x0'] - origin) < .03]
     if indices: starts.append((max(indices), column))
    if starts and starts[0][1] == 1:
     # Cell origins, rather than the first digit or a hyphen, identify a row.
     # This retains alpha-only codes and distinguishes year-leading headings.
     cells = [''.join(c['text'] for c in chars[:starts[0][0]]).strip(), '', '', '']
     for j, (index, column) in enumerate(starts):
      end = starts[j + 1][0] if j + 1 < len(starts) else len(chars)
      cells[column] = ''.join(c['text'] for c in chars[index:end]).strip()
     assert section and re.fullmatch(r'[A-Z0-9-]+', cells[0]) and cells[1], (pn, y, cells)
     assert cells[3] in ['', 'Rookie'], (pn, y, cells)
     rows.append([section, *cells, str(pn)])
    else:
     text = ''.join(c['text'] for c in chars).strip()
     assert text and text == text.upper() and re.search('[A-Z]', text), (pn, y, text)
     if text not in OUTER: section = text
 assert len(rows) == 1385 and len({r[0] for r in rows}) == 35
 for name in ['TRANSCENDENT ICONS CHROME BASE CARDS', 'TRANSCENDENT ICONS CHROME IMAGE VARIATIONS']:
  assert [int(r[1]) for r in rows if r[0] == name] == list(range(1, 101))
 assert sum(r[4] == 'Rookie' for r in rows) == 383
 assert [r[1] for r in rows if r[0] == 'GEMSTONES'] == ['CYCS', 'CRCS', 'CRCS', 'CFCS', 'PRCS', 'PRCS']
 return rows, raw

def build():
 catalog = json.loads((ROOT / 'data/set-catalog.json').read_text())
 record = next(s for s in catalog['sets'] if s['slug'] == SLUG)
 path = ROOT / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
 subprocess.run(['curl', '-sLf', '--retry', '2', '--max-time', '30', record['checklistUrl'], '-o', str(path)], check=True)
 rows, raw = read_cards(path)
 data_path = ROOT / record['tableData']
 data = json.loads(data_path.read_text())
 data.update(headers=['Checklist section', 'Card number', 'Name', 'Team', 'Rookie', 'Source page'], rows=rows, rawPages=raw, unclassifiedLines=[], sha256=hashlib.sha256(path.read_bytes()).hexdigest(), sectionColumn=0, importKind='topps-grid-pdf', dedicatedParser=PARSER)
 data_path.write_text(json.dumps(data, ensure_ascii=False) + '\n')
 record.update(rowCount=len(rows), sections=35, sha256=data['sha256'], importKind=data['importKind'], dedicatedParser=PARSER, dataAudit='All 1,385 physical subject rows across 35 sections reconciled to original cell origins, including six Gemstones, year-leading autograph headings and 383 printed Rookie marks. Repeated card codes, apparent source name/code mismatches and printed rookie annotations are retained without correction. Parallel numbering is guide-scoped; pack odds and a calendar release date are not established.')
 for name in ['set-catalog.json', 'topps-product-official-catalog.json']:
  p = ROOT / 'data' / name
  c = json.loads(p.read_text())
  items = c['sets'] if isinstance(c, dict) else c
  present = any(s['slug'] == SLUG for s in items)
  items[:] = [record if s['slug'] == SLUG else s for s in items]
  if not present: items.append(record)
  p.write_text(json.dumps(c, ensure_ascii=False, indent=2) + '\n')
 print('Transcendent: 1,385 original subject rows, 35 sections, 383 printed Rookie marks; no inferred odds or release date.')

if __name__ == '__main__': build()
