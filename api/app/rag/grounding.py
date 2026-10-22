"""Validate quoted evidence and execute only bounded, grounded arithmetic."""
from decimal import Decimal, Inexact, localcontext
import re

NUMBER = r'-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?'


def evidence_catalog(sources):
    """Keep source text server-owned; the model selects short, bounded IDs."""
    units = [(source, line.strip()) for source in sources for line in source['excerpt'].splitlines() if line.strip()]
    if len(units) > 96:
        units = [(source, source['excerpt']) for source in sources]
    catalog, mapping = [], {}
    for number, (source, quote) in enumerate(units, 1):
        eid = f'E{number}'
        catalog.append(dict(evidence_id=eid, title=source.get('title', ''), project_title=source.get('project_title',''), version=source.get('version'), text=quote))
        mapping[eid] = dict(source_id=source['source_id'], quote=quote)
    return catalog, mapping


def numeric_catalog(mapping):
    catalog, numbers = [], {}
    for eid, item in mapping.items():
        for raw in re.findall(r'(?<![\d.,])' + NUMBER + r'(?![\d.,])', item['quote']):
            value = raw.replace(',', '')
            if len(value) > 24 or abs(Decimal(value)) > Decimal('1e15'):
                continue
            nid = f'{eid}:{value}'
            if nid in numbers:
                continue
            if len(numbers) == 256:
                return catalog, numbers
            numbers[nid] = dict(evidence_id=eid, value=value)
            catalog.append(dict(number_id=nid, evidence_id=eid, value=value))
    return catalog, numbers


def resolve_evidence(value, mapping, numbers=None):
    if not isinstance(value, dict) or not isinstance(value.get('evidence'), list) or len(value['evidence']) > 12 or not isinstance(value.get('calculation'), dict):
        raise ValueError('invalid_citations')
    def resolve(eid):
        if not isinstance(eid, str) or eid not in mapping:
            raise ValueError('invalid_citations')
        return dict(mapping[eid])
    calc = dict(value['calculation'])
    operands = calc.get('operands')
    if not isinstance(operands, list) or len(operands) > 8:
        raise ValueError('invalid_calculation')
    expanded = []
    for item in operands:
        if not isinstance(item, dict):
            raise ValueError('invalid_calculation')
        nid = item.get('number_id')
        if not isinstance(nid, str) or nid not in (numbers or {}):
            raise ValueError('invalid_calculation')
        number = numbers[nid]
        expanded.append(dict(resolve(number['evidence_id']), value=number['value'], label=item.get('label')))
    calc['operands'] = expanded
    result = dict(answer=value.get('answer'), evidence=[resolve(eid) for eid in value['evidence']], calculation=calc)
    if 'blocks' in value:
        if not isinstance(value['blocks'],list) or len(value['blocks']) > 24:
            raise ValueError('invalid_citations')
        result['blocks'] = []
        for block in value['blocks']:
            if not isinstance(block,dict) or not isinstance(block.get('evidence'),list) or not 1 <= len(block['evidence']) <= 12:
                raise ValueError('invalid_citations')
            result['blocks'].append(dict(text=block.get('text'),evidence=[resolve(eid) for eid in block['evidence']]))
    return result


def grounded_answer(value, sources):
    allowed = {s['source_id']: s['excerpt'] for s in sources}
    citations = []

    def quote(item):
        if not isinstance(item, dict):
            raise ValueError('invalid_citations')
        sid, text = item.get('source_id'), item.get('quote')
        if not isinstance(sid, str) or sid not in allowed or not isinstance(text, str) or not text.strip():
            raise ValueError('invalid_citations')
        if text not in allowed[sid]:
            raise ValueError('invalid_citations')
        if sid not in citations:
            citations.append(sid)
        return text

    if not isinstance(value, dict) or not isinstance(value.get('answer'), str) or not value['answer'].strip() or len(value['answer']) > 6000:
        raise ValueError('invalid_citations')
    evidence, calc = value.get('evidence'), value.get('calculation')
    if not isinstance(evidence, list) or len(evidence) > 12 or not isinstance(calc, dict):
        raise ValueError('invalid_citations')
    for item in evidence:
        quote(item)
    operation, operands = calc.get('operation'), calc.get('operands')
    if not isinstance(operation, str) or operation not in {'none', 'add', 'subtract', 'multiply', 'divide'} or not isinstance(operands, list):
        raise ValueError('invalid_calculation')
    answer = value['answer'].strip()
    if operation != 'none':
        if not 2 <= len(operands) <= 8 or (operation in {'subtract', 'divide'} and len(operands) != 2):
            raise ValueError('invalid_calculation')
        numbers, labels = [], []
        for item in operands:
            text = quote(item)
            raw, label = item.get('value'), item.get('label')
            if not isinstance(raw, str) or len(raw) > 24 or not re.fullmatch(NUMBER, raw) or not isinstance(label, str) or len(label) > 100:
                raise ValueError('invalid_calculation')
            number = Decimal(raw.replace(',', ''))
            tokens = re.findall(r'(?<![\d.,])' + NUMBER + r'(?![\d.,])', text)
            if number not in [Decimal(t.replace(',', '')) for t in tokens] or abs(number) > Decimal('1e15'):
                raise ValueError('invalid_calculation')
            numbers.append(number)
            labels.append(label)
        unit = calc.get('unit')
        if not isinstance(unit, str) or len(unit) > 30:
            raise ValueError('invalid_calculation')
        with localcontext() as ctx:
            ctx.prec = 200
            ctx.clear_flags()
            result = numbers[0]
            for number in numbers[1:]:
                if operation == 'add': result += number
                elif operation == 'subtract': result -= number
                elif operation == 'multiply': result *= number
                elif number == 0: raise ValueError('invalid_calculation')
                else: result /= number
            if abs(result) > Decimal('1e24'):
                raise ValueError('invalid_calculation')
            def display(n):
                text = format(n, ',f')
                return text.rstrip('0').rstrip('.') if '.' in text else text
            symbol = {'add': ' + ', 'subtract': ' − ', 'multiply': ' × ', 'divide': ' ÷ '}[operation]
            parts = '；'.join(f'{label}：{display(n)}' for label, n in zip(labels, numbers))
            approximate = ctx.flags[Inexact]
            # Recurring quotients use a labelled, significant-digit approximation;
            # finite decimal operands and results retain their actual precision.
            rendered = format(result, '.12g') if approximate else display(result)
            answer = parts + '。\n計算：' + symbol.join(display(n) for n in numbers) + (' ≈ ' if approximate else ' = ') + rendered + (' ' + unit if unit else '') + '。'
    elif operands:
        raise ValueError('invalid_calculation')
    blocks = []
    if 'blocks' in value and operation == 'none':
        citations.clear()
        for block in value['blocks']:
            if not isinstance(block.get('text'),str) or not block['text'].strip() or len(block['text']) > 6000:
                raise ValueError('invalid_citations')
            ids = []
            for item in block['evidence']:
                quote(item)
                if item['source_id'] not in ids:
                    ids.append(item['source_id'])
            blocks.append(dict(text=block['text'].strip(),source_ids=ids))
        if sum(len(b['text']) for b in blocks) > 6000:
            raise ValueError('invalid_citations')
        answer = '\n\n'.join(b['text'] for b in blocks)
    elif citations:
        blocks = [dict(text=answer,source_ids=list(citations))]
    if not citations:
        answer = '目前來源不足以支持答案。'
    return {'answer': answer, 'citations': citations, 'blocks': blocks}
