"""Reconcile a retained, fresh official active-listing read with published NOW rows.

This does not fetch sources or establish historical archive completeness. Refresh
the listing checkpoint through actual official UI reads before running it.
"""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse
from topps_now_identity import product_family, unnumbered_product_title, collector_edition_title

ROOT = Path(__file__).resolve().parents[1]


def reconcile(listing, observations, published):
    def path(url):
        return unquote(urlparse(url).path).rstrip('/')
    by_url = {path(p['source']): p for p in observations
              if urlparse(p['source']).hostname == 'www.topps.com'}
    rows = {(r[0], r[1]): r for r in published['rows']}
    results = []
    for source in listing['listings']:
        assert len(source['products']) == source['reportedProductCount'], 'Incomplete active-listing pagination'
        assert len({path(p['url']) for p in source['products']}) == len(source['products']), 'Duplicate active products'
        for item in source['products']:
            p = by_url.get(path(item['url']))
            status = 'missing-observation'
            title_identity = re.search(r'\s*-\s*(20\d\d.*?NOW®.*?) (?:- )?(?:Card |Sticker # )([A-Za-z0-9-]+)', item['title'])
            single = unnumbered_product_title(item['title'])
            edition = collector_edition_title(item['title'])
            identity_matches = p and (bool(title_identity) and (p['series'], p['number']) == (title_identity[1], title_identity[2].rstrip('-')) or
                                     bool(edition) and (p['series'], p['number']) == (edition['series'], edition['number']) or
                                     bool(single) and p.get('identityKind') == 'official-single-card-product' and
                                     not p['number'] and single['family'] == product_family(p))
            if p and not identity_matches:
                results.append({**item, 'status': 'missing-current-identity'})
                continue
            if p:
                key = (product_family(p), p['number'])
                if not p['saleFromISO']:
                    status = 'pending-official-sale-date'
                elif p['saleFromISO'] < '2026-01-01':
                    status = 'outside-calendar-scope'
                elif key not in rows:
                    status = 'missing-published-row'
                else:
                    expected = [product_family(p), p['number'], p['name'], p['printRun'], p['saleFrom'], p['saleUntil'], '; '.join(p['parallels']), p['terms'], p['source']]
                    assert rows[key] == expected, 'Published active card differs from its observation: ' + item['title']
                    status = 'published'
            results.append({**item, 'status': status})
    return results


def main():
    checkpoint = ROOT / 'data/topps-now-active-listings.json'
    listing = json.loads(checkpoint.read_text())
    assert listing['sourceKind'] == 'official-browser-active-listing'
    results = reconcile(listing, json.loads((ROOT / 'data/topps-now-observations.json').read_text()),
                        json.loads((ROOT / 'data/imports/topps-now-2026.json').read_text()))
    report = {'observed': listing['observed'], 'listingSha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
              'historicalCoverageComplete': False, 'products': results,
              'publishedCount': sum(p['status'] == 'published' for p in results),
              'remaining': [p for p in results if p['status'] not in {'published', 'outside-calendar-scope'}]}
    (ROOT / 'data/topps-now-active-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    assert not any(p['status'].startswith('missing-') for p in results), 'Active NOW products are missing from observations or published rows'
    print(f"Active NOW checkpoint {listing['observed']}: {report['publishedCount']}/{len(results)} published; {len(report['remaining'])} explicit pending gaps. Historical coverage remains partial.")


if __name__ == '__main__':
    main()
