"""Official NOW identities; a product URL never supplies a printed card number."""
import re
import json
import hashlib
from urllib.parse import unquote, urlparse

# Reviewed cover-card scopes. The Madden title prints 2027, while its official
# Specs explicitly publishes Product Year 2026; never derive either from a URL.
GAMING_SCOPES = {
    '2027 MADDEN NFL Cover Topps NOW®': {'Category': 'Sports', 'Sub Categories': 'Football', 'Product Year': '2026'},
    '2026 MLB The Show Cover Topps NOW®': {'Category': 'Sports', 'Sub Categories': 'Baseball', 'Product Year': '2026'},
}


def collector_edition_title(title):
    """Keep the explicitly named MLB edition separate from the regular number."""
    match = re.fullmatch(r"(.+?) - (2026 MLB Topps NOW®) Card ([A-Za-z0-9-]+) - (Collector's Edition) # to (\d+)", title)
    if not match:
        return None
    subject, base_series, number, edition, limit = match.groups()
    return {'series': base_series + ' ' + edition, 'number': number,
            'subject': subject, 'limit': limit}


def verified_collector_edition(title, fields, lines):
    identity = collector_edition_title(title)
    if not identity:
        return None
    required = {'Category': 'Sports', 'Sub Categories': 'Baseball', 'Brand': 'Topps',
                'Sub Brand': 'Topps NOW®', 'Sub Type': 'Cards',
                'Product Type': 'Print on Demand', 'Product Year': '2026'}
    specification = f"Collector's Edition numbered to {identity['limit']}, featuring gold foil details and 130pt premium stock!"
    if specification not in lines or not fields.get('Subjects') or any(fields.get(k) != v for k, v in required.items()):
        return None
    return {**identity, 'specification': specification}

def product_family(product):
    return product.get('family', product['series'])


def observation_key(product):
    if product['number']:
        return product['series'], product['number']
    assert product.get('identityKind') == 'official-single-card-product'
    return product['series'], unquote(urlparse(product['source']).path).rstrip('/')


def apply_identity_revisions(root, products):
    """Retain reviewed earlier identities without publishing duplicate cards.

    Both factual snapshots must hash-check and print the same SKU. A shared
    number or similar name is insufficient; no automatic identity joins occur.
    """
    registry = root / 'data/topps-now-identity-revisions.json'
    if not registry.exists():
        return
    reviewed = json.loads(registry.read_text())
    assert reviewed['sourceKind'] == 'reviewed-official-product-identity-revisions'
    by_key = {observation_key(p): p for p in products}
    seen = set()
    for revision in reviewed['revisions']:
        pair = []
        for side in ['previous', 'current']:
            ref = revision[side]
            key = (ref['series'], ref['number'])
            product = by_key[key]
            assert product['source'] == ref['url']
            if side == 'previous':
                assert product['evidence']['sha256'] == ref['sha256']
            snapshot = json.loads((root / ref['snapshotFile']).read_text())
            assert snapshot['sourceKind'] == 'official-browser-product'
            lines = next(p['lines'] for p in snapshot['products'] if p['url'] == ref['url'])
            lines = [line.strip() for line in lines]
            assert hashlib.sha256('\n'.join(lines).encode()).hexdigest() == ref['sha256']
            fields = dict(line.split('  | ', 1) for line in lines if '  | ' in line)
            assert fields['SKU'] == revision['sku'] == product['evidence']['fields']['SKU']
            assert re.search(r' - ' + re.escape(ref['series']) + r' - Card ' + re.escape(ref['number']) + r'$', lines[0])
            pair.append(product)
        before, current = pair
        assert before['number'] == current['number'] and observation_key(before) != observation_key(current)
        assert observation_key(before) not in seen and not current.get('supersededBy')
        seen.add(observation_key(before))
        before['supersededBy'] = revision['current']


def unnumbered_entertainment_title(title):
    match = re.fullmatch(r'(20\d\d) (Marvel|Disney|Star Wars) Topps NOW®?:? (.+?)(?: - PR: ([\d,]+))?', title, re.I)
    if not match:
        return None
    year, franchise, subject, print_run = match.groups()
    franchise = {'marvel': 'Marvel', 'disney': 'Disney', 'star wars': 'Star Wars'}[franchise.lower()]
    return {'series': year + ' ' + franchise + ' Topps NOW®',
            'family': re.sub(r' - PR: [\d,]+$', '', title),
            'printRun': print_run or ''}


def unnumbered_product_title(title):
    if len(re.findall(r'\bPR\s*:', title, re.I)) > 1:
        return None
    identity = unnumbered_entertainment_title(title)
    if identity:
        return identity
    # The reviewed NBA title explicitly prints an empty Card label. Preserve
    # that blank; the URL/SKU are identity keys, never a source for its number.
    blank = re.fullmatch(r'(.+?) - (2025-26 NBA Topps NOW®) - Card - PR: ([\d,]+)', title)
    if blank:
        return {'series': blank[2], 'family': re.sub(r' - PR: [\d,]+$', '', title),
                'printRun': blank[3], 'subject': blank[1], 'blankPrintedNumber': True}
    for series in GAMING_SCOPES:
        caption = re.escape(series)
        pattern = rf'.+? - ({caption})(?: - PR:\s*([\d,]+))?' if 'MADDEN' in series else rf'({caption}) - .+?(?: - PR:\s*([\d,]+))?'
        match = re.fullmatch(pattern, title)
        if match:
            return {'series': series, 'family': re.sub(r' - PR:\s*[\d,]+$', '', title), 'printRun': match[2] or ''}
    return None


def verified_single_card(title, fields, lines):
    identity = unnumbered_product_title(title)
    if not identity:
        return None
    required = {'Category': 'Entertainment', 'Brand': 'Topps', 'Sub Brand': 'Topps NOW®',
                'Sub Type': 'Cards', 'Product Type': 'Print on Demand',
                'Product Year': identity['series'][:4]}
    required.update(GAMING_SCOPES.get(identity['series'], {}))
    if identity.get('blankPrintedNumber'):
        required.update({'Category': 'Sports', 'Sub Categories': 'Basketball',
                         'Product Year': '2026', 'Subjects': identity['subject']})
    # Marvel publishes this property explicitly. Disney's reviewed products do
    # not publish a Properties cell; their official title supplies the series.
    if ' Marvel ' in identity['series']:
        required['Properties'] = 'Marvel Studios'
    single_base = any(re.fullmatch(r'(?:\* )?Open[- ]Edition Base Card', line, re.I) for line in lines)
    bundle = re.search(r'\b\d+[- ]*(?:Card|Sticker)[- ]+(?:(?:Team|Game)[- ]+)?(?:Set|Pack)\b|\b(?:Bundle|Box)\b', title, re.I)
    printed_number = any(re.fullmatch(r'Card(?: number| #)?', k, re.I) and v for k, v in fields.items())
    if bundle or printed_number or not single_base or not fields.get('Subjects') or any(fields.get(k) != v for k, v in required.items()):
        return None
    return identity


def verified_print_run_conflict(title, fields, lines):
    """Retain a printed MLB identity while selecting neither conflicting run."""
    match = re.fullmatch(r'(.+?) - (2026 MLB Topps NOW®) - Card (\d+) - PR: ([\d,]+) - PR: ([\d,]+)', title)
    if not match or match[4] == match[5]:
        return None
    required = {'Category': 'Sports', 'Sub Categories': 'Baseball', 'Brand': 'Topps',
                'Sub Brand': 'Topps NOW®', 'Sub Type': 'Cards',
                'Product Type': 'Print on Demand', 'Product Year': '2026',
                'Subjects': match[1]}
    single_base = any(re.fullmatch(r'(?:\* )?Open[- ]Edition Base Card', line, re.I) for line in lines)
    if not single_base or any(fields.get(k) != v for k, v in required.items()):
        return None
    return {'series': match[2], 'number': match[3], 'subject': match[1],
            'conflictingPrintRuns': [match[4], match[5]]}
