"""Attach reviewed, explicitly unjoined Panini guide context to shared imports."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def apply_context(record, payload, evidence):
    raw = (ROOT/evidence['file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == evidence['sha256']
    proof = json.loads(raw)
    ids = proof['mapping'].get(record['slug'], [])
    if not ids:
        return
    snapshots = [s for s in proof['snapshots'] if s['id'] in ids]
    assert len(snapshots) == len(ids)
    for snapshot in snapshots:
        facts = json.dumps(snapshot['facts'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        assert hashlib.sha256(facts).hexdigest() == snapshot['factsSha256']
        payload.setdefault('sourceSheets', []).append({
            'name':'Qualified manufacturer guide context', 'source':snapshot['source'],
            'notes':[['Original box/case units and product scope retained. No pack odds or new family numbering joins inferred.']],
            'evidenceFile':evidence['file'], 'evidenceSha256':evidence['sha256']})
        payload.setdefault('publishedSpecifications', []).append({
            'name':'Manufacturer context: '+snapshot['id'],
            'worksheet':'Product-wide guide context; no checklist-family join inferred',
            'headers':['Field','Value','Scope / qualifier','Official source'],
            'rows':[[*row,snapshot['source']] for row in snapshot['facts']],
            'source':snapshot['source'],'evidenceFile':evidence['file'],'evidenceSha256':evidence['sha256']})
        record.setdefault('additionalSources', []).append({'title':'Reviewed official product / guide context','url':snapshot['source']})
    record['guideReview'] = payload['guideReview'] = evidence
    if record['slug'] == 'panini-2025-panini-caitlin-clark-chronicled-basketball':
        note = ' The original official December 15, 2025 announcement already describes Target availability; this is not a newly verified calendar-2026 release. General release day remains unverified.'
        record['catalogEvidence'] += note
        record['dataAudit'] += note
