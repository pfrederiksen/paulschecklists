"""Read the two currently linked UConn checklists by physical PDF column."""
import collections
import hashlib
import io
import json
import re
import urllib.request
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
PAGE = 'https://blog.paniniamerica.net/panini-to-introduce-the-first-ever-uconn-basketball-trading-card-box-set/'
URL = 'https://blog.paniniamerica.net/wp-content/uploads/2025/03/UConn-checklist1-1.pdf'
ALTERNATE = 'https://blog.paniniamerica.net/wp-content/uploads/2025/03/UConn-checklist1.pdf'
SLUG = 'panini-2025-panini-uconn-box-set-basketball'
EXPECTED = {'COLLEGE CONTENDERS':35, 'LEGENDARY CONTENDERS':15, 'SCHOOL COLORS':10,
            'CAMPUS LEGENDS':7, 'PRIZM':15, 'PRIZM STUDENT ORIENTATION':5,
            'PRIZM FEARLESS':4, 'PRIZM FIREWORKS':1, 'ON CAMPUS':5, 'COLOR BLAST':5,
            'THUNDER':6, 'PROFILES':2, 'TROPHY HUNTING':10, 'PRIVATE SIGNINGS':49}


def parse(raw, complete=True):
    rows, columns, headings = [], [], []
    family = None
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        assert len(pdf.pages) == (2 if complete else 1)
        for page in pdf.pages:
            assert (page.width, page.height) == (720, 576)
            for left, right in [(30,195), (195,360), (360,525), (525,690)]:
                bottom = 510 if (complete and page.page_number == 2) or (not complete and left >= 195) else 545
                text = page.crop((left,75,right,bottom)).extract_text()
                columns.append({'page':page.page_number, 'left':left, 'right':right, 'text':text})
                for line in text.splitlines():
                    match = re.fullmatch(r'[\uf0a3□]\s*(\S+)\s+(.+?)(?:\s+(SSP|SP))?', line)
                    if match:
                        assert family in EXPECTED
                        number, subject, mark = match.groups()
                        rows.append([family, number, subject, mark or '', str(page.page_number)])
                    elif re.fullmatch(r'[A-Z ]+', line):
                        family = line
                        assert family in EXPECTED or family == 'PINNACLE MASCOT', line
                        headings.append(line)
                    else:
                        assert not complete and ('information' in line or 'images' in line or 'determined' in line), line
    if complete:
        assert dict(collections.Counter(r[0] for r in rows)) == EXPECTED
        assert len(rows) == 169 and len(headings) == 15 and headings[-1] == 'PINNACLE MASCOT'
        assert collections.Counter(r[3] for r in rows) == {'':117, 'SP':34, 'SSP':18}
    else:
        assert len(rows) == 108
    return rows, columns, headings


def main():
    raw = urllib.request.urlopen(URL, timeout=30).read()
    alternate = urllib.request.urlopen(ALTERNATE, timeout=30).read()
    assert hashlib.sha256(raw).hexdigest() == 'c98ddf7a3c08e94fbcd2defc46f6f0e195228bb6e2b367d5d642b9f5b5856d4e', 'Review revised primary PDF before replacing retained evidence'
    assert hashlib.sha256(alternate).hexdigest() == 'bc868a989c102c173a7eb8f5fed946f4c20aa33f0efd88ff7b8ec193eddbc47b', 'Review revised alternate PDF before replacing retained evidence'
    rows, columns, headings = parse(raw)
    shorter, _, _ = parse(alternate, False)
    # The shorter current link omits 61 entries; all 108 overlapping facts agree.
    assert not (collections.Counter(tuple(r[:4]) for r in shorter) - collections.Counter(tuple(r[:4]) for r in rows))
    sha = hashlib.sha256(raw).hexdigest()
    pdf = f'data/official-panini/{SLUG}.pdf'
    alt = f'data/official-panini/alternates/{SLUG}-{hashlib.sha256(alternate).hexdigest()[:12]}.pdf'
    (ROOT/pdf).write_bytes(raw)
    (ROOT/alt).write_bytes(alternate)
    proof_file = 'data/official-panini/uconn-pdf-observations-20261021-0300.json'
    note = ('All 169 printed entries and 52 literal SP/SSP marks from the two-page official PDF are retained. '
            'The second currently linked one-page PDF contains 108 matching entries and omits 61; neither link establishes a revision date. '
            'Repeated Private Signings codes and separate marked/unmarked versions remain separate source rows. '
            'Pinnacle Mascot is an empty printed heading, with no published card roster. '
            'The official CSV export is header-only; its evidence is retained separately. '
            'No teams, rookie flags, serial limits or pack odds are printed in these checklists. '
            'SP/SSP are source designations, not numeric odds or serial numbers. Card-image handwriting is not imported. '
            'The March 13, 2025 announcement and preorder wording do not establish a general release date. '
            'Exhaustive product-guide/parallel reconciliation and calendar-year release coverage remain incomplete.')
    proof = {'observed':'2026-10-21', 'source':PAGE, 'method':'Fresh official article link read; both linked PDFs fetched and parsed in four physical columns. Two-page source visually checked against rendered pages. No OCR-derived facts.',
             'primary':{'url':URL,'file':pdf,'sha256':sha,'bytes':len(raw),'rows':169,'populatedSections':14},
             'alternate':{'url':ALTERNATE,'file':alt,'sha256':hashlib.sha256(alternate).hexdigest(),'bytes':len(alternate),'rows':108,'allOverlappingEntriesAgree':True,'omittedEntries':61},
             'emptyHeading':'PINNACLE MASCOT', 'printedMarks':{'SP':34,'SSP':18}, 'note':note}
    (ROOT/proof_file).write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n')
    evidence = {'file':proof_file,'sha256':hashlib.sha256((ROOT/proof_file).read_bytes()).hexdigest(),'source':PAGE}
    csv_proof = 'data/official-panini/older-year-observations-20261021-0300.json'
    csv_evidence = {'file':csv_proof,'sha256':hashlib.sha256((ROOT/csv_proof).read_bytes()).hexdigest(),
                    'sourceExport':f'data/official-panini/{SLUG}.csv'}
    payload = {'title':'2025 Panini UConn Box Set Basketball', 'source':URL,'sha256':sha,
               'importKind':'panini-pdf','dedicatedParser':'scripts/import_panini_uconn_2025.py',
               'headers':['Checklist section','Card number','Player / subjects','Published SP / SSP mark','Source page'],
               'rows':rows,'sectionColumn':0,'coverageComplete':True,'sourceObservation':evidence,
               'headerOnlyCsvEvidence':csv_evidence,'rawColumns':columns,'printedHeadings':headings,
               'sourceSheets':[{'name':'Official source reconciliation','notes':[[note]],'source':PAGE}]}
    dest = f'data/imports/{SLUG}.json'
    record = {'title':payload['title'],'slug':SLUG,'page':f'sets/{SLUG}.html','manufacturer':'Panini',
              'sport':'basketball','year':'2025','sourcePage':PAGE,'checklistUrl':URL,'releaseStatus':'Unverified',
              'releaseDate':None,'verified':'2026-10-21','checklistFirstObserved':'2026-10-21',
              'status':'Source table','tableData':dest,'rowCount':169,'sections':14,'parallelData':False,
              'publishedOdds':False,'importKind':'panini-pdf','dedicatedParser':payload['dedicatedParser'],
              'sha256':sha,'coverageComplete':True,'sourceObservation':evidence,'headerOnlyCsvEvidence':csv_evidence,
              'catalogEvidence':note,'dataAudit':note,
              'additionalSources':[{'title':'Shorter currently linked official checklist','url':ALTERNATE}]}
    csv_observation = json.loads((ROOT/csv_proof).read_text())
    guide = next(r['guideReview'] for r in csv_observation['exports'] if r['slug']==SLUG)
    from panini_guide_context import apply_context
    apply_context(record,payload,guide)
    (ROOT/dest).write_text(json.dumps(payload, ensure_ascii=False)+'\n')
    for path in ['data/set-catalog.json','data/panini-official-catalog.json']:
        collection = json.loads((ROOT/path).read_text())
        records = collection['sets'] if isinstance(collection,dict) else collection
        index = next((i for i,r in enumerate(records) if r['slug']==SLUG),None)
        if index is None:records.append(record)
        else:records[index]=record
        (ROOT/path).write_text(json.dumps(collection, ensure_ascii=False, indent=2)+'\n')
    print('Imported 169 UConn entries / 14 populated sections; 34 SP and 18 SSP marks, both linked PDFs and header-only CSV evidence retained.')


if __name__ == '__main__':
    main()
