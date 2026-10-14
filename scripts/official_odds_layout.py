"""Read odds cells from original text-object origins inside physical row boxes."""
import collections, re
import pdfplumber
from pypdf import PdfReader

class UnsupportedOddsLayout(ValueError):
    pass

def normalized(text):
    return ' '.join(text.replace('\x02', '-').split())

def cells_from_origins(chars, objects, origins, right_edges=None, column_boxes=None):
    anchors = {}
    for x, baseline, _ in objects:
        indices = [i for i, c in enumerate(chars) if abs(c['matrix'][4] - x) < .02 and abs(c['matrix'][5] - baseline) < .02]
        if not indices:
            raise UnsupportedOddsLayout(f'Text object has no matching physical glyph origin: {x}, {baseline}')
        # A long earlier cell may cross this x coordinate. Original drawing
        # sequence identifies the actual start of the following cell.
        index = max(indices)
        column = next((j for j, box in enumerate(column_boxes) if box[0]-.02 <= x < box[2]+.02), -1) if column_boxes else max((j for j, left in enumerate(origins) if x >= left - .02), default=-1) if right_edges is None else 0 if abs(x-origins[0]) < .02 else -2
        if column == -1:
            raise UnsupportedOddsLayout('Unmapped original column')
        if index in anchors and anchors[index] != column:
            raise UnsupportedOddsLayout('Conflicting cell origins')
        anchors[index] = column
    if not anchors or min(anchors) != 0:
        raise UnsupportedOddsLayout('Unclassified glyphs before the first cell')
    result = [[] for _ in origins]
    edges = [0 for _ in origins]
    starts = sorted(anchors)
    for start, end in zip(starts, starts[1:] + [len(chars)]):
        piece = chars[start:end]
        edge = max(c['x1'] for c in piece)
        column = anchors[start]
        if column == -2:
            column = min(range(1, len(origins)), key=lambda j: abs(edge-right_edges[j]))
            if abs(edge-right_edges[column]) > 3:
                raise UnsupportedOddsLayout('Value does not align with a literal header right edge')
        result[column].append(normalized(''.join(c['text'] for c in piece)))
        edges[column] = max(edges[column], edge)
    return [normalized(' '.join(parts)) for parts in result], edges

def read_object_tables(path):
    reader = PdfReader(path)
    result, formats, raw = [], [], []
    with pdfplumber.open(path) as pdf:
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text() or ''})
            tables = page.find_tables()
            if len(tables) != 1 or len(tables[0].rows) < 2:
                raise UnsupportedOddsLayout('Not a single multi-row odds grid')
            objects = []
            def visit(text, cm, tm, font, size):
                if text.strip():
                    if abs(cm[1]) > .001 or abs(cm[2]) > .001 or cm[0] <= 0 or cm[3] <= 0:
                        raise UnsupportedOddsLayout('Rotated text needs another parser')
                    objects.append((tm[4]*cm[0]+tm[5]*cm[2]+cm[4], tm[4]*cm[1]+tm[5]*cm[3]+cm[5], text))
            reader.pages[pn-1].extract_text(visitor_text=visit)
            header_box = tables[0].rows[0].bbox
            header_objects = [o for o in objects if header_box[1] <= page.height-o[1] <= header_box[3]]
            origins = sorted(set(round(o[0], 4) for o in header_objects))
            if len(origins) < 2:
                raise UnsupportedOddsLayout('Missing original format header origins')
            for index, row in enumerate(tables[0].rows):
                box = row.bbox
                chars = [c for c in page.chars if box[0] <= (c['x0']+c['x1'])/2 <= box[2] and box[1] <= (c['top']+c['bottom'])/2 <= box[3]]
                row_objects = [o for o in objects if box[0] <= o[0] <= box[2] and box[1] <= page.height-o[1] <= box[3]]
                column_boxes = row.cells if len(row.cells) == len(origins) and all(row.cells) else None
                cells, edges = cells_from_origins(chars, row_objects, origins, None if index == 0 else header_edges, column_boxes)
                if index == 0:
                    if cells[0].lower() not in {'card', 'cards', 'all components', 'description', 'component'}:
                        raise UnsupportedOddsLayout('Unrecognized literal header caption')
                    labels = cells[1:]
                    if any(not label or len(label) > 100 for label in labels) or len(set(labels)) != len(labels):
                        raise UnsupportedOddsLayout('Invalid physical format headings')
                    if formats and labels != formats:
                        raise UnsupportedOddsLayout('Format headings change across pages')
                    formats = labels
                    header_edges = edges
                    continue
                if not cells[0] or any(value and value != '-' and not re.fullmatch(r'[\d,.]+(?::[\d,.]+)+', value) for value in cells[1:]):
                    raise UnsupportedOddsLayout(f'Nonliteral odds cell: page {pn}, {cells}')
                result.append({'name': cells[0], 'values': dict(zip(formats, [None if value in {'', '-'} else value for value in cells[1:]])), 'page': pn})
    if not result:
        raise UnsupportedOddsLayout('No physical odds rows')
    return result, formats, raw, []

def read_single_column(path):
    """A literal two-cell header can anchor a borderless single odds column."""
    result, raw, formats = [], [], []
    with pdfplumber.open(path) as pdf:
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text() or ''})
            tables = page.find_tables()
            if tables:
                if len(tables) != 1 or len(tables[0].rows) != 1:
                    raise UnsupportedOddsLayout('Not a single header-only grid')
                header = tables[0].extract()[0]
                boxes = tables[0].rows[0].cells
                if len(header) != 2 or header[0] not in {'Card', 'Cards'} or not header[1] or any(box is None for box in boxes):
                    raise UnsupportedOddsLayout('Missing literal single-column heading')
                if formats and formats != [normalized(header[1])]:
                    raise UnsupportedOddsLayout('Single-column label changes across pages')
                formats = [normalized(header[1])]
                body_top = tables[0].bbox[3]
                previous_width = page.width
            elif formats and page.width == previous_width:
                body_top = 0
            else:
                raise UnsupportedOddsLayout('No verified continuing column geometry')
            groups = collections.defaultdict(list)
            for word in page.extract_words():
                if word['top'] >= body_top:
                    groups[round(word['top'], 1)].append(word)
            for words in groups.values():
                name = normalized(' '.join(w['text'] for w in words if w['x0'] < boxes[1][0]))
                value = normalized(' '.join(w['text'] for w in words if w['x0'] >= boxes[1][0]))
                if not name or not re.fullmatch(r'[\d,.]+(?::[\d,.]+)+', value):
                    raise UnsupportedOddsLayout('Unclassified single-column body line')
                result.append({'name': name, 'values': {formats[0]: value}, 'page': pn})
    return result, formats, raw, []

def read_ruled_cells(path):
    result, formats, raw = [], [], []
    with pdfplumber.open(path) as pdf:
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text() or ''})
            tables = page.find_tables()
            if len(tables) != 1:
                raise UnsupportedOddsLayout('Missing single ruled-cell table')
            table = tables[0]
            values = table.extract()
            if not values or len(values[0]) < 2 or any(cell is None for row in table.rows for cell in row.cells):
                raise UnsupportedOddsLayout('Column borders are not published for every cell')
            header = [normalized(v or '') for v in values[0]]
            if header[0].lower() not in {'card', 'cards', 'description', 'component', 'all components'}:
                raise UnsupportedOddsLayout('Unrecognized ruled-cell header')
            if formats and formats != header[1:]:
                raise UnsupportedOddsLayout('Ruled-cell headings change across pages')
            formats = header[1:]
            if any(not label or len(label)>100 for label in formats) or len(set(formats))!=len(formats):
                raise UnsupportedOddsLayout('Invalid literal ruled format headings')
            for row in values[1:]:
                cells = [normalized(v or '') for v in row]
                if len(cells) != len(formats)+1 or not cells[0] or any(v not in {'', '-'} and not re.fullmatch(r'[\d,.]+(?::[\d,.]+)+', v) for v in cells[1:]):
                    raise UnsupportedOddsLayout('Unclassified ruled odds cell')
                result.append({'name': cells[0], 'values': dict(zip(formats, [None if v in {'', '-'} else v for v in cells[1:]])), 'page': pn})
    return result, formats, raw, []

def physical_odds_pdf(path):
    failures = []
    for parser in [read_ruled_cells, read_object_tables, read_single_column, read_unnamed_column]:
        try:
            return parser(path)
        except UnsupportedOddsLayout as error:
            failures.append(str(error))
    raise UnsupportedOddsLayout(' | '.join(failures))

def read_unnamed_column(path):
    """Keep a headerless literal ratio column without inventing its format/unit."""
    label = 'Published odds (format not named)'
    result, raw = [], []
    with pdfplumber.open(path) as pdf:
        for pn, page in enumerate(pdf.pages, 1):
            raw.append({'page': pn, 'text': page.extract_text() or ''})
            tables = page.find_tables()
            if len(tables) != 1 or any(len(row.cells) != 1 for row in tables[0].rows):
                raise UnsupportedOddsLayout('Not a bordered category column with external ratios')
            table = tables[0]
            words = page.extract_words()
            for row, values in zip(table.rows, table.extract()):
                name = normalized(values[0] or '')
                ratio_words = [w for w in words if w['x0'] >= table.bbox[2] and row.bbox[1] <= (w['top']+w['bottom'])/2 < row.bbox[3]]
                value = normalized(' '.join(w['text'] for w in ratio_words))
                if not name or not re.fullmatch(r'[\d,.]+(?::[\d,.]+)+', value):
                    raise UnsupportedOddsLayout('Unclassified headerless category/ratio row')
                result.append({'name': name, 'values': {label: value}, 'page': pn})
    return result, [label], raw, []
