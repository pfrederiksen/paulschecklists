"""Verify every official MLS NOW All-Star PDF cell and product-level scope."""
import hashlib
import json
import re
from pathlib import Path
from collections import Counter

import pdfplumber
import import_official_catalog as generic
from import_topps_now_mls_allstar_2026 import SLUG, URL, PAGE, EVIDENCE, FAMILIES

root = Path(__file__).resolve().parents[1]
path = root / 'data/catalog-sources/downloads' / (SLUG + '.pdf')
data = json.loads((root / 'data/imports' / (SLUG + '.json')).read_text())
assert data['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest() and data['source'] == URL
assert data['headers'] == ['Checklist section', 'Card Number', 'Subject', 'Team', 'Source page']
assert Counter(r[0] for r in data['rows']) == dict(zip(FAMILIES, [10, 5, 9, 2]))
assert len(data['rows']) == len({r[1] for r in data['rows']}) == 26
with pdfplumber.open(path) as pdf:
    assert len(pdf.pages) == 1
    words = pdf.pages[0].extract_words()
    anchors = [w for w in words if w['x0'] < 100 and re.fullmatch('ASG-[A-Z]+', w['text'])]
    # Independent word origins include the San Diego cell's 0.69pt baseline
    # offset and preserve each original Subject/Team boundary.
    physical = []
    for anchor in anchors:
        line = sorted([w for w in words if abs(w['top']-anchor['top']) < 1], key=lambda w: w['x0'])
        physical.append([' '.join(w['text'] for w in line if lo <= w['x0'] < hi)
                         for lo, hi in [(45,250),(250,374.5),(374.5,570)]])
    assert physical == [r[1:4] for r in data['rows']]
by_number = {r[1]: r for r in data['rows']}
assert by_number['ASG-TM'][2:4] == ['Thomas Müller', 'Vancouver Whitecaps FC']
assert by_number['ASG-MMAR'][2:4] == ['Mbekezeli Mbokazi', 'Chicago Fire FC']
assert by_number['ASG-AD'][2:4] == ['Anders Dreyer', 'San Diego FC']
assert data['rows'][-1] == ['Net-Jewel Relic Cards','ASG-MMR','Mbekezeli Mbokazi','Chicago Fire FC','1']
assert not any(r[1] == 'Net-Jewel' for r in data['rows'])
assert not data.get('odds') and not data.get('formats') and not data.get('serialColumn')
assert not any(re.search('rookie|print run|numbering', h, re.I) for h in data['headers'])
evidence = json.loads((root / EVIDENCE).read_text())
assert data['sourceProducts'][0]['sha256'] == hashlib.sha256((root / EVIDENCE).read_bytes()).hexdigest()
assert data['sourceProducts'][0]['url'] == PAGE
assert evidence['title'].endswith('11 Card Set - PR: 2677')
spec = data['publishedSpecifications'][0]
assert spec['name'] not in FAMILIES, 'Bundle context must not become a family-wide limit'
assert spec['source'] == PAGE and spec['headers'] == ['Official field','Published term','Qualification']
assert spec['rows'][0][1] == '2677' and 'bundle' in spec['rows'][0][2]
assert 'Match-used net jewel 1/1 relic or autograph-relic redemption' in spec['rows'][1][1]
assert spec['rows'][1][1] in evidence['lines']
assert 'no per-card print run' in spec['rows'][1][2]
fields = {r[0]: r[1] for r in spec['rows'][2:]}
assert fields['Available From'] == 'Jul 27, 2026' and fields['Available Until'] == 'Aug 3, 2026'
assert fields['Sub Type'] == 'Set' and fields['Product Type'] == 'Print on Demand'
set_record = next(s for s in json.loads((root / 'data/set-catalog.json').read_text())['sets'] if s['slug'] == SLUG)
assert set_record['releaseDate'] is None and set_record['releaseStatus'] == 'Unverified'
assert set_record['dedicatedParser'] == 'scripts/import_topps_now_mls_allstar_2026.py'
assert generic.run(set_record.copy()) == set_record, 'Generic refresh must preserve dedicated PDF imports'
observations = json.loads((root / 'data/topps-now-observations.json').read_text())
assert not any(p['source'] == PAGE for p in observations), 'A bundle is not one numbered NOW card'
assert not json.loads((root / 'data/topps-now-archive-index.json').read_text())['coverageComplete']
print('Verified all 26 physical MLS All-Star NOW rows, four families, original teams/accents, bundle print run and sale dates, qualified unjoined 1/1 context and unavailable odds/rookie fields.')
