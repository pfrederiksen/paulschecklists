"""Official NOW identities; a product URL never supplies a printed card number."""
import re
from urllib.parse import unquote, urlparse


def product_family(product):
    return product.get('family', product['series'])


def observation_key(product):
    if product['number']:
        return product['series'], product['number']
    assert product.get('identityKind') == 'official-single-card-product'
    return product['series'], unquote(urlparse(product['source']).path).rstrip('/')


def unnumbered_marvel_title(title):
    match = re.fullmatch(r'(20\d\d) Marvel Topps NOW®?:? (.+?)(?: - PR: ([\d,]+))?', title, re.I)
    if not match:
        return None
    year, subject, print_run = match.groups()
    return {'series': year + ' Marvel Topps NOW®',
            'family': re.sub(r' - PR: [\d,]+$', '', title),
            'printRun': print_run or ''}


def verified_single_card(title, fields, lines):
    identity = unnumbered_marvel_title(title)
    if not identity:
        return None
    required = {'Category': 'Entertainment', 'Properties': 'Marvel Studios',
                'Sub Type': 'Cards', 'Product Type': 'Print on Demand',
                'Product Year': identity['series'][:4]}
    single_base = any(re.fullmatch(r'(?:\* )?Open[- ]Edition Base Card', line, re.I) for line in lines)
    bundle = re.search(r'\d+[- ]+Card (?:Set|Pack)|\b(?:Bundle|Box)\b', title, re.I)
    printed_number = any(re.fullmatch(r'Card(?: number| #)?', k, re.I) and v for k, v in fields.items())
    if bundle or printed_number or not single_base or not fields.get('Subjects') or any(fields.get(k) != v for k, v in required.items()):
        return None
    return identity
