"""Official NOW identities; a product URL never supplies a printed card number."""
import re
from urllib.parse import unquote, urlparse

# Reviewed cover-card scopes. The Madden title prints 2027, while its official
# Specs explicitly publishes Product Year 2026; never derive either from a URL.
GAMING_SCOPES = {
    '2027 MADDEN NFL Cover Topps NOW®': {'Category': 'Sports', 'Sub Categories': 'Football', 'Product Year': '2026'},
    '2026 MLB The Show Cover Topps NOW®': {'Category': 'Sports', 'Sub Categories': 'Baseball', 'Product Year': '2026'},
}

def product_family(product):
    return product.get('family', product['series'])


def observation_key(product):
    if product['number']:
        return product['series'], product['number']
    assert product.get('identityKind') == 'official-single-card-product'
    return product['series'], unquote(urlparse(product['source']).path).rstrip('/')


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
