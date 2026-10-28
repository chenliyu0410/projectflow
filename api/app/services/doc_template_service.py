"""Company Word templates: safe upload checks, field scanning, numbering and filling into document versions."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP, ROUND_UP
import hashlib
import io
import os
import re
import uuid
import zipfile

from lxml import etree

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select, update

from app.audit import log_audit
from app.models import (Document, DocumentTemplate, DocumentTemplateCounter, DocumentTemplateVersion,
                        DocumentVersion, Node, Project, now_utc)
from app.services import attachment_store as files
from app.services import document_store as store

AUTO_FIELDS = ('編號', '今天', '填寫人', '專案名稱', '節點名稱', '公司名稱')
TOTAL_FIELDS = ('小計', '稅額', '總計')
LINE_COLUMNS = ('品項', '數量', '單價', '金額')
FIELD_TYPES = {'text', 'textarea', 'number', 'date', 'select'}
ROUNDING = {'half_up': ROUND_HALF_UP, 'down': ROUND_DOWN, 'up': ROUND_UP}
MAX_FIELDS = 40
MAX_LINES = 100
MAX_UNPACKED = 30_000_000
MAX_PART = 10_000_000
TAIPEI = timezone(timedelta(hours=8))
TOKEN = re.compile(r'\{(年|月|日|序號([1-6])位)\}')
TAG = re.compile(r'\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}', re.S)
VARIABLE = re.compile(r'\{\{\s*(?:(列)\s*\.\s*)?([^\s{}.|()\[\]]+)\s*\}\}')
FOR_OPEN = re.compile(r'\{%\s*for\s+列\s+in\s+明細\s*%\}')
BODY_PART = re.compile(r'word/(document|header\d*|footer\d*)\.xml')
FOR_CLOSE = re.compile(r'\{%\s*endfor\s*%\}')


def reject(message):
    raise HTTPException(422, message)


def today():
    return datetime.now(TAIPEI).date()


# ---------- upload checks and scanning ----------

def inspect_docx(data):
    """Validate a template .docx and return (field names in order, has_lines). Raises 422 with the reason."""
    if not data or len(data) > files.MAX_BYTES:
        reject('樣板檔案為空或超過10MB')
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        reject('不是有效的 Word（.docx）檔案；加密或舊版 .doc 請另存為 .docx')
    with archive:
        entries = archive.infolist()
        names = [e.filename for e in entries]
        if len(entries) > 1000 or len(set(names)) != len(names):
            reject('Word 檔內部檔案過多或重複')
        if sum(e.file_size for e in entries) > MAX_UNPACKED or any(e.file_size > MAX_PART for e in entries):
            reject('Word 檔解壓後內容過大')
        if any(e.flag_bits & 1 for e in entries):
            reject('不接受加密的 Word 檔')
        if not {'[Content_Types].xml', 'word/document.xml'} <= set(names):
            reject('不是有效的 Word（.docx）檔案')
        if any(n.lower().endswith('vbaproject.bin') for n in names):
            reject('不接受含巨集的檔案')
        xml_parts = {}
        for entry in entries:
            lower = entry.filename.lower()
            if not (lower.endswith('.xml') or lower.endswith('.rels')):
                continue
            raw = archive.read(entry)
            upper = raw.upper()
            if b'<!DOCTYPE' in upper or b'<!ENTITY' in upper:
                reject('Word 檔含不允許的 XML 宣告')
            if lower.endswith('.rels') and b'TARGETMODE="EXTERNAL"' in upper.replace(b"'", b'"'):
                reject('樣板不可包含外部連結（超連結、外部圖片或連結檔案）；請移除後再上傳')
            if b'altChunk' in raw or b'w:attachedTemplate' in raw:
                reject('樣板不可嵌入外部文件')
            if lower.endswith('.xml'):
                # Check the parsed-and-reserialized XML, as docxtpl sees it: character references
                # such as &#123; only become a literal "{" after parsing.
                try:
                    parser = etree.XMLParser(resolve_entities=False, no_network=True)
                    xml_parts[entry.filename] = etree.tostring(etree.fromstring(raw, parser), encoding='unicode')
                except etree.XMLSyntaxError:
                    reject('Word 檔內容不是有效的 XML')
    from docxtpl import DocxTemplate
    template = DocxTemplate(io.BytesIO(data))
    parts = []
    # docxtpl renders whole XML parts (attributes included) for the body, every header/footer and footnotes,
    # so every part is checked after its own patching: tags may appear only in body/header/footer text.
    for name, xml in sorted(xml_parts.items(), key=lambda item: item[0] != 'word/document.xml'):
        try:
            patched = template.patch_xml(xml)
        except Exception:
            reject('無法讀取此 Word 檔')
        if re.search(r'\{[{%#]', ''.join(re.findall(r'<[^>]*>', patched))):
            reject('代號只能放在文字中，不可放在格式、書籤或圖片說明等屬性裡')
        if BODY_PART.fullmatch(name):
            parts.append(patched)
        elif re.search(r'\{[{%#]', re.sub(r'<[^>]+>', '', patched)):
            reject('代號只能放在本文、頁首或頁尾')
    try:
        template.init_docx()
    except Exception:
        reject('無法讀取此 Word 檔')
    order, has_lines, depth = [], False, 0
    for xml in parts:
        source = re.sub(r'<[^>]+>', '', xml)
        for tag in TAG.findall(source):
            if FOR_OPEN.fullmatch(tag):
                if depth:
                    reject('明細表不可巢狀')
                depth, has_lines = 1, True
                continue
            if FOR_CLOSE.fullmatch(tag):
                if not depth:
                    reject('明細表標記不成對')
                depth = 0
                continue
            match = VARIABLE.fullmatch(tag)
            if not match:
                reject(f'樣板只能使用 {{{{欄位名稱}}}} 與明細表標記，不接受：{tag[:40]}')
            row, name = match.groups()
            if row:
                if not depth or name not in LINE_COLUMNS:
                    reject(f'明細欄位只能是 {"、".join(LINE_COLUMNS)}，且要放在明細表列中')
                continue
            if not valid_name(name):
                reject(f'欄位名稱「{name[:20]}」無效：請用中英文或數字，不含空白與符號')
            if name in TOTAL_FIELDS:
                continue
            if name not in order:
                order.append(name)
        leftovers = TAG.sub('', source)
        if '{{' in leftovers or '{%' in leftovers or '{#' in leftovers:
            reject('樣板有未關閉的 {{ 或 {% 標記')
    if depth:
        reject('明細表標記不成對')
    uses_totals = any(re.search(r'\{\{\s*' + name + r'\s*\}\}', re.sub(r'<[^>]+>', '', xml))
                      for xml in parts for name in TOTAL_FIELDS)
    if uses_totals and not has_lines:
        reject('小計、稅額、總計只能搭配明細表使用')
    fields = [name for name in order if name not in AUTO_FIELDS]
    if len(fields) > MAX_FIELDS:
        reject(f'需要填寫的欄位不可超過{MAX_FIELDS}個')
    return order, has_lines


def valid_name(name):
    return 0 < len(name) <= 50 and name.isidentifier() and not name.startswith('_')


# ---------- settings ----------

def default_field(name):
    return {'name': name, 'label': name, 'type': 'text', 'required': False, 'unit': '', 'options': []}


def merge_fields(names, previous):
    """Keep settings for names that still exist; new placeholders start as optional text."""
    old = {f['name']: f for f in previous}
    return [old.get(name, default_field(name)) for name in names if name not in AUTO_FIELDS]


def check_numbering(value):
    if not value or len(value) > 60 or value != value.strip():
        reject('編號格式需為1至60字')
    if len(re.findall(r'\{序號[1-6]位\}', value)) != 1:
        reject('編號格式要有一個 {序號N位}（N 為 1 到 6）')
    rest = TOKEN.sub('', value)
    if re.search(r'[{}/\\<>:"|?*\x00-\x1f]', rest):
        reject('編號格式只能用 {年}{月}{日}{序號N位} 與一般文字，不含 / \\ 等符號')
    return value


def check_fields(fields, names):
    if sorted(f['name'] for f in fields) != sorted(n for n in names if n not in AUTO_FIELDS):
        reject('欄位清單與樣板代號不一致，請重新載入')
    result = []
    for field in fields:
        label = (field.get('label') or '').strip()
        kind = field.get('type')
        unit = (field.get('unit') or '').strip()
        options = [str(o).strip() for o in field.get('options') or []]
        if not 1 <= len(label) <= 100:
            reject('顯示名稱需為1至100字')
        if kind not in FIELD_TYPES:
            reject('欄位類型無效')
        if kind != 'number' and unit:
            reject('只有數字欄位可設定單位')
        if len(unit) > 30:
            reject('單位最多30字')
        if kind == 'select':
            if not 2 <= len(options) <= 50 or len(set(options)) != len(options) or any(not o or len(o) > 100 for o in options):
                reject('請設定2至50個不重複選項，每項1至100字')
        elif options:
            reject('只有下拉選項欄位可設定選項')
        if not isinstance(field.get('required'), bool):
            reject('必填設定無效')
        result.append({'name': field['name'], 'label': label, 'type': kind, 'required': field['required'], 'unit': unit, 'options': options})
    return result


def check_tax(rate, rounding):
    try:
        value = Decimal(str(rate))
    except InvalidOperation:
        reject('稅率格式無效')
    if not value.is_finite() or value < 0 or value > 100 or value.as_tuple().exponent < -2:
        reject('稅率需為0到100，最多兩位小數')
    if rounding not in ROUNDING:
        reject('進位方式無效')
    return format(value.normalize(), 'f'), rounding


# ---------- storage and template rows ----------

def require_admin(current):
    if current.user.role != 'admin':
        raise HTTPException(403, '只有系統管理員可以管理文件樣板')


def load(db, current, template_id, *, manage=False):
    row = db.scalar(select(DocumentTemplate).where(DocumentTemplate.id == template_id,
        DocumentTemplate.organization_id == current.organization.id, DocumentTemplate.status != 'deleted'))
    if row is None:
        raise HTTPException(404, '找不到文件樣板')
    if manage:
        require_admin(current)
    elif row.status != 'active' and current.user.role != 'admin':
        raise HTTPException(404, '找不到文件樣板')
    return row


def current_version(db, template):
    return db.scalar(select(DocumentTemplateVersion).where(DocumentTemplateVersion.template_id == template.id,
        DocumentTemplateVersion.organization_id == template.organization_id,
        DocumentTemplateVersion.version == template.current_version))


def out(template, version, admin):
    return {'id': template.id, 'name': template.name, 'category': template.category, 'status': template.status,
            'version': template.current_version, 'filename': version.filename, 'fields': version.fields,
            'auto_fields': [n for n in AUTO_FIELDS], 'numbering': version.numbering, 'tax_rate': version.tax_rate,
            'rounding': version.rounding, 'has_lines': version.has_lines, 'can_manage': admin}


def listing(db, current):
    admin = current.user.role == 'admin'
    query = select(DocumentTemplate).where(DocumentTemplate.organization_id == current.organization.id,
        DocumentTemplate.status.in_(('active', 'disabled') if admin else ('active',))).order_by(DocumentTemplate.created_at)
    rows = db.scalars(query).all()
    return {'items': [out(row, current_version(db, row), admin) for row in rows], 'can_manage': admin}


def store_file(db, current, data):
    """Write template bytes to attachment storage and charge the company quota; returns (key, sha256)."""
    root = files.storage_root()
    key = uuid.uuid4().hex
    temporary = files.storage_path(root, key, True)
    with temporary.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        files.validate_content(temporary, '.docx')
        quota = files.lock_quota(db, current.organization.id)
        if quota.charged_bytes + len(data) > files.quota_limit():
            raise HTTPException(413, '公司容量已滿')
        quota.charged_bytes += len(data)
        os.replace(temporary, files.storage_path(root, key))
    finally:
        temporary.unlink(missing_ok=True)
    return key, hashlib.sha256(data).hexdigest()


def read_file(version):
    path = files.storage_path(files.storage_root(), version.storage_key)
    if not path.is_file():
        raise files.unavailable()
    return path.read_bytes()


def add_version(db, current, template, *, filename, key, size, sha, fields, numbering, tax_rate, rounding, has_lines):
    template.current_version += 1
    row = DocumentTemplateVersion(id=str(uuid.uuid4()), organization_id=template.organization_id, template_id=template.id,
        version=template.current_version, filename=filename, storage_key=key, size_bytes=size, sha256=sha, fields=fields,
        numbering=numbering, tax_rate=tax_rate, rounding=rounding, has_lines=has_lines, created_by=current.user.id, created_at=now_utc())
    db.add(row)
    return row


def check_meta(name, category):
    name, category = (name or '').strip(), (category or '').strip()
    if not 1 <= len(name) <= 100:
        reject('樣板名稱需為1至100字')
    if len(category) > 50:
        reject('類別最多50字')
    return name, category or '一般'


def create(db, current, data, filename, name, category, *, numbering='DOC-{年}-{序號3位}', fields=None, tax_rate='5', rounding='half_up'):
    require_admin(current)
    name, category = check_meta(name, category)
    if files.validate_filename(filename) != '.docx':
        raise HTTPException(415, '樣板只接受 Word（.docx）檔')
    names, has_lines = inspect_docx(data)
    settings = merge_fields(names, fields or [])
    check_numbering(numbering)
    try:
        key, sha = store_file(db, current, data)
        template = DocumentTemplate(id=str(uuid.uuid4()), organization_id=current.organization.id, name=name, category=category,
            current_version=0, status='active', created_by=current.user.id, created_at=now_utc())
        db.add(template)
        db.flush()
        add_version(db, current, template, filename=filename, key=key, size=len(data), sha=sha, fields=settings,
            numbering=numbering, tax_rate=tax_rate, rounding=rounding, has_lines=has_lines)
        log_audit(db, current, 'doc_template.create', payload={'template_id': template.id, 'version': 1, 'name': name,
            'fields': [f['name'] for f in settings]})
        db.commit()
    except Exception:
        db.rollback()
        raise
    return out(template, current_version(db, template), True)


def check_expected(template, expected):
    if template.current_version != expected:
        raise HTTPException(409, '樣板已被修改，請重新載入')


def replace_file(db, current, template_id, data, filename, expected):
    template = load(db, current, template_id, manage=True)
    check_expected(template, expected)
    if files.validate_filename(filename) != '.docx':
        raise HTTPException(415, '樣板只接受 Word（.docx）檔')
    names, has_lines = inspect_docx(data)
    previous = current_version(db, template)
    settings = merge_fields(names, previous.fields)
    try:
        key, sha = store_file(db, current, data)
        add_version(db, current, template, filename=filename, key=key, size=len(data), sha=sha, fields=settings,
            numbering=previous.numbering, tax_rate=previous.tax_rate, rounding=previous.rounding, has_lines=has_lines)
        log_audit(db, current, 'doc_template.revise', payload={'template_id': template.id, 'version': template.current_version,
            'file': True, 'fields': [f['name'] for f in settings]})
        db.commit()
    except Exception:
        db.rollback()
        raise
    return out(template, current_version(db, template), True)


def update_settings(db, current, template_id, payload):
    template = load(db, current, template_id, manage=True)
    check_expected(template, payload['expected_version'])
    previous = current_version(db, template)
    name, category = check_meta(payload['name'], payload['category'])
    fields = check_fields(payload['fields'], [f['name'] for f in previous.fields])
    numbering = check_numbering(payload['numbering'])
    tax_rate, rounding = check_tax(payload['tax_rate'], payload['rounding'])
    template.name, template.category = name, category
    add_version(db, current, template, filename=previous.filename, key=previous.storage_key, size=previous.size_bytes,
        sha=previous.sha256, fields=fields, numbering=numbering, tax_rate=tax_rate, rounding=rounding, has_lines=previous.has_lines)
    log_audit(db, current, 'doc_template.revise', payload={'template_id': template.id, 'version': template.current_version,
        'file': False, 'fields': [f['name'] for f in fields]})
    db.commit()
    return out(template, current_version(db, template), True)


def set_status(db, current, template_id, status):
    template = load(db, current, template_id, manage=True)
    if status not in {'active', 'disabled', 'deleted'}:
        reject('狀態無效')
    template.status = status
    log_audit(db, current, 'doc_template.delete' if status == 'deleted' else 'doc_template.status',
              payload={'template_id': template.id, 'status': status})
    db.commit()
    return {'id': template.id, 'status': status}


# ---------- numbering ----------

def period_for(numbering, day):
    if '{日}' in numbering:
        return day.strftime('%Y%m%d')
    if '{月}' in numbering:
        return day.strftime('%Y%m')
    if '{年}' in numbering:
        return day.strftime('%Y')
    return 'all'


def next_number(db, organization_id, template_id, numbering, day):
    """Increment the per-company, per-template, per-period counter and commit before the document is built."""
    period = period_for(numbering, day)
    if db.bind.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    key = dict(organization_id=organization_id, template_id=template_id, period=period)
    db.execute(insert(DocumentTemplateCounter).values(**key, value=0).on_conflict_do_nothing())
    # The UPDATE takes the row (PostgreSQL) or database (SQLite) write lock, so concurrent callers serialize here.
    db.execute(update(DocumentTemplateCounter).filter_by(**key).values(value=DocumentTemplateCounter.value + 1))
    value = db.scalar(select(DocumentTemplateCounter.value).filter_by(**key))
    db.commit()

    def token(match):
        if match.group(1) == '年':
            return day.strftime('%Y')
        if match.group(1) == '月':
            return day.strftime('%m')
        if match.group(1) == '日':
            return day.strftime('%d')
        return str(value).zfill(int(match.group(2)))
    return TOKEN.sub(token, numbering)


# ---------- values, lines and rendering ----------

def number_text(value):
    if value == value.to_integral_value():
        return f'{int(value):,}'
    return f'{value:,f}'.rstrip('0').rstrip('.')


def parse_number(raw, label):
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        reject(f'「{label}」要填數字')
    try:
        value = Decimal(str(raw).replace(',', '').strip())
    except InvalidOperation:
        reject(f'「{label}」要填數字')
    if not value.is_finite() or abs(value) >= Decimal('1e12'):
        reject(f'「{label}」要填合理的數字')
    return value


def check_values(fields, values):
    if not isinstance(values, dict) or set(values) - {f['name'] for f in fields}:
        reject('包含未知欄位')
    result = {}
    for field in fields:
        raw = values.get(field['name'])
        if raw is None or isinstance(raw, str) and not raw.strip():
            if field['required']:
                reject(f'請填寫「{field["label"]}」')
            result[field['name']] = ''
            continue
        if field['type'] == 'number':
            result[field['name']] = str(parse_number(raw, field['label']))
            continue
        if not isinstance(raw, str) or len(raw) > 4000:
            reject(f'「{field["label"]}」的值不符合欄位格式')
        value = raw.strip() if field['type'] != 'textarea' else raw.strip('\n ')
        if field['type'] == 'select' and value not in field['options']:
            reject(f'「{field["label"]}」請從選項中選擇')
        if field['type'] == 'date':
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                    raise ValueError()
                datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                reject(f'「{field["label"]}」日期格式要是 YYYY-MM-DD')
        result[field['name']] = value
    return result


def check_lines(lines, has_lines):
    if not has_lines:
        if lines:
            reject('此樣板沒有明細表')
        return []
    if not isinstance(lines, list) or not 1 <= len(lines) <= MAX_LINES:
        reject(f'明細請填1到{MAX_LINES}列')
    result = []
    for number, line in enumerate(lines, 1):
        if not isinstance(line, dict) or set(line) - {'品項', '數量', '單價'}:
            reject('明細欄位只能是品項、數量、單價')
        item = line.get('品項')
        if not isinstance(item, str) or not 1 <= len(item.strip()) <= 200:
            reject(f'第{number}列請填品項（200字內）')
        quantity = parse_number(line.get('數量'), f'第{number}列數量')
        price = parse_number(line.get('單價'), f'第{number}列單價')
        if quantity <= 0 or price < 0:
            reject(f'第{number}列數量要大於0，單價不可為負')
        result.append({'品項': item.strip(), '數量': str(quantity), '單價': str(price)})
    return result


def compute(lines, tax_rate, rounding):
    """Integer-yuan amounts: each line, subtotal, tax and total, rounded by the template's rule."""
    mode = ROUNDING[rounding]
    rows, subtotal = [], 0
    for line in lines:
        amount = int((Decimal(line['數量']) * Decimal(line['單價'])).quantize(Decimal(1), rounding=mode))
        subtotal += amount
        rows.append({**line, '金額': amount})
    tax = int((Decimal(subtotal) * Decimal(tax_rate) / 100).quantize(Decimal(1), rounding=mode))
    return rows, {'小計': subtotal, '稅額': tax, '總計': subtotal + tax}


def render(data, context):
    from docxtpl import DocxTemplate
    from jinja2.sandbox import SandboxedEnvironment
    template = DocxTemplate(io.BytesIO(data))
    environment = SandboxedEnvironment(autoescape=True)
    template.render(context, jinja_env=environment, autoescape=True)
    output = io.BytesIO()
    template.save(output)
    return output.getvalue()


def display_context(version, values, lines, auto):
    from docxtpl import Listing
    context = dict(auto)
    for field in version.fields:
        value = values.get(field['name'], '')
        if field['type'] == 'number' and value != '':
            value = number_text(Decimal(value)) + (f' {field["unit"]}' if field['unit'] else '')
        elif field['type'] == 'textarea' and value:
            value = Listing(value)
        context[field['name']] = value
    if version.has_lines:
        rows, totals = compute(lines, version.tax_rate, version.rounding)
        context['明細'] = [{'品項': r['品項'], '數量': number_text(Decimal(r['數量'])), '單價': number_text(Decimal(r['單價'])),
                           '金額': f'{r["金額"]:,}'} for r in rows]
        context.update({k: f'{v:,}' for k, v in totals.items()})
    return context


def safe_filename(name, number):
    base = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', f'{name}-{number}')[:190]
    return base + '.docx'


def scope_names(db, current, node_id, project_id):
    if node_id is not None:
        node = db.scalar(select(Node).where(Node.id == node_id, Node.organization_id == current.organization.id))
        project = db.scalar(select(Project).where(Project.id == node.project_id, Project.organization_id == current.organization.id))
        return project.title, node.title
    project = db.scalar(select(Project).where(Project.id == project_id, Project.organization_id == current.organization.id))
    return project.title, project.title


async def generate(db, current, template_id, values, lines, *, node_id=None, project_id=None):
    store.permission(db, current, node_id, True, project_id)
    template = load(db, current, template_id)
    if template.status != 'active':
        raise HTTPException(409, '此樣板已停用')
    version = current_version(db, template)
    clean = check_values(version.fields, values)
    clean_lines = check_lines(lines, version.has_lines)
    data = read_file(version)
    day = today()
    project_title, node_title = scope_names(db, current, node_id, project_id)
    org_id, template_name = current.organization.id, template.name
    number = next_number(db, org_id, template.id, version.numbering, day)
    auto = {'編號': number, '今天': day.isoformat(), '填寫人': current.user.display_name, '專案名稱': project_title,
            '節點名稱': node_title, '公司名稱': current.organization.name}
    built = await run_in_threadpool(render, data, display_context(version, clean, clean_lines, auto))
    fill = {'template_id': template.id, 'template_version': version.version, 'number': number, 'values': clean, 'lines': clean_lines}

    async def chunks():
        yield built
    return await store.save(db, current, node_id, chunks(), safe_filename(template_name, number), f'由樣板「{template_name}」產生',
        project_id=project_id, template=(version.id, fill, [f['name'] for f in version.fields]))


def generated_version(db, current, document_id):
    doc, allowed, _ = store.get_document(db, current, document_id)
    row = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == doc.id,
        DocumentVersion.organization_id == current.organization.id, DocumentVersion.version == doc.current_version))
    if row is None or row.template_version_id is None:
        raise HTTPException(409, '此文件不是由樣板產生，請改用上傳新版本')
    version = db.scalar(select(DocumentTemplateVersion).where(DocumentTemplateVersion.id == row.template_version_id,
        DocumentTemplateVersion.organization_id == current.organization.id))
    template = db.get(DocumentTemplate, version.template_id)
    return doc, row, version, template, allowed


def fill_detail(db, current, document_id):
    doc, row, version, template, allowed = generated_version(db, current, document_id)
    return {'document_id': doc.id, 'current_version': doc.current_version, 'template_name': template.name,
            'template_version': version.version, 'fields': version.fields, 'has_lines': version.has_lines,
            'tax_rate': version.tax_rate, 'rounding': version.rounding, 'number': row.fill_values['number'],
            'values': row.fill_values['values'], 'lines': row.fill_values['lines'], 'can_write': allowed}


async def regenerate(db, current, document_id, expected, values, lines):
    """Same template version and number; a new document version with edited values."""
    doc, row, version, template, _ = generated_version(db, current, document_id)
    store.get_document(db, current, document_id, True)
    store.check_expected(doc, expected)
    clean = check_values(version.fields, values)
    clean_lines = check_lines(lines, version.has_lines)
    data = read_file(version)
    number = row.fill_values['number']
    project_title, node_title = scope_names(db, current, doc.node_id, doc.project_id)
    auto = {'編號': number, '今天': today().isoformat(), '填寫人': current.user.display_name, '專案名稱': project_title,
            '節點名稱': node_title, '公司名稱': current.organization.name}
    built = await run_in_threadpool(render, data, display_context(version, clean, clean_lines, auto))
    fill = {'template_id': template.id, 'template_version': version.version, 'number': number, 'values': clean, 'lines': clean_lines}

    async def chunks():
        yield built
    return await store.save(db, current, doc.node_id, chunks(), row.filename, '修改內容重新產生', document_id=doc.id,
        expected=expected, project_id=doc.project_id, template=(version.id, fill, [f['name'] for f in version.fields]))


# ---------- built-in fictional samples ----------

def field(name, label=None, kind='text', required=True, options=None):
    return {'name': name, 'label': label or name, 'type': kind, 'required': required, 'unit': '', 'options': options or []}


SAMPLES = [
    {'name': '會議紀錄', 'category': '會議', 'numbering': 'MTG-{年}-{序號3位}', 'title': '會議紀錄',
     'rows': [('編號', '編號'), ('會議名稱', '會議名稱'), ('日期時間', '日期時間'), ('出席者', '出席者'), ('決議', '決議'),
              ('待辦／期限', '待辦'), ('所屬專案', '專案名稱'), ('記錄人', '填寫人')],
     'fields': [field('會議名稱'), field('日期時間'), field('出席者', kind='textarea'), field('決議', kind='textarea'),
                field('待辦', '待辦／期限', 'textarea')]},
    {'name': '報價單', 'category': '業務', 'numbering': 'Q-{年}-{月}{日}-{序號2位}', 'title': '報價單',
     'rows': [('單號', '編號'), ('客戶名稱', '客戶名稱'), ('報價日', '今天'), ('有效期限', '有效期限'), ('業務窗口', '填寫人')],
     'lines': True, 'notes': '付款條件：月結 30 天。本報價單為虛構範例。',
     'fields': [field('客戶名稱'), field('有效期限', kind='date')]},
    {'name': '工單', 'category': '工單', 'numbering': 'WO-{序號3位}', 'title': '工單',
     'rows': [('工單號', '編號'), ('工單名稱', '工單名稱'), ('負責人', '負責人'), ('期限', '期限'), ('需求說明', '需求說明'),
              ('完成條件', '完成條件'), ('申請人', '填寫人'), ('提出日', '今天'), ('所屬專案', '專案名稱')],
     'fields': [field('工單名稱'), field('負責人'), field('期限', kind='date'), field('需求說明', kind='textarea'),
                field('完成條件', kind='textarea')]},
]


def sample_docx(sample):
    """Build a plain fictional Word template with python-docx (a docxtpl dependency)."""
    from docx import Document as Word
    from docx.shared import Pt
    word = Word()
    word.styles['Normal'].font.size = Pt(12)
    word.add_heading('{{公司名稱}}　' + sample['title'], level=1)
    table = word.add_table(rows=0, cols=2)
    table.style = 'Table Grid'
    for label, name in sample['rows']:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = '{{' + name + '}}'
    if sample.get('lines'):
        word.add_paragraph('')
        lines = word.add_table(rows=1, cols=4)
        lines.style = 'Table Grid'
        for cell, text in zip(lines.rows[0].cells, ('品項', '數量', '單價', '金額')):
            cell.text = text
        lines.add_row().cells[0].text = '{%tr for 列 in 明細 %}'
        for cell, name in zip(lines.add_row().cells, LINE_COLUMNS):
            cell.text = '{{列.' + name + '}}'
        lines.add_row().cells[0].text = '{%tr endfor %}'
        for label, name in (('小計', '小計'), ('營業稅', '稅額'), ('總計', '總計')):
            cells = lines.add_row().cells
            cells[2].text = label
            cells[3].text = '{{' + name + '}}'
    if sample.get('notes'):
        word.add_paragraph(sample['notes'])
    word.add_paragraph('本文件由專流文件樣板產生；範例公司與內容皆為虛構。')
    output = io.BytesIO()
    word.save(output)
    return output.getvalue()


def add_samples(db, current):
    require_admin(current)
    existing = set(db.scalars(select(DocumentTemplate.name).where(DocumentTemplate.organization_id == current.organization.id,
        DocumentTemplate.status != 'deleted')).all())
    added = []
    for sample in SAMPLES:
        if sample['name'] in existing:
            continue
        create(db, current, sample_docx(sample), f'{sample["name"]}範例.docx', sample['name'], sample['category'],
               numbering=sample['numbering'], fields=sample['fields'])
        added.append(sample['name'])
    return {**listing(db, current), 'added': added}
