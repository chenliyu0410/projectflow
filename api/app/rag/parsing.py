import csv
from collections import Counter
import io
import multiprocessing
import zipfile
from pathlib import Path
from xml.etree import ElementTree

MAX_BYTES = 10 * 1024 * 1024
MAX_TEXT = 240000
MAX_PAGES = 200
MAX_UNCOMPRESSED = 20 * 1024 * 1024
MAX_PDF_PAGE_STREAM = 2 * 1024 * 1024
MAX_PDF_TOTAL_STREAM = 20 * 1024 * 1024
PDF_TIMEOUT = 30


def parse_file(path, filename):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('file_too_large')
    suffix = Path(filename).suffix.lower()
    sections = []
    total_chars = 0
    def add(text, locator):
        nonlocal total_chars
        text = text.strip()
        if text:
            sections.append({'text': text, 'locator': locator})
            total_chars += len(text)
        if total_chars > MAX_TEXT or len(sections) > 2000:
            raise ValueError('text_limit')
    try:
        if suffix in {'.txt', '.csv'}:
            raw = path.read_bytes().decode('utf-8-sig')
            if len(raw) > MAX_TEXT:
                raise ValueError('text_limit')
            if suffix == '.csv':
                reader = csv.reader(io.StringIO(raw))
                headers = next(reader, [])
                header_counts = Counter(h.strip() for h in headers)
                add(' | '.join(headers), {'section': '第 1 列'})
                for number, row in enumerate(reader, 2):
                    fields = []
                    for column, value in enumerate(row):
                        name = headers[column].strip() if column < len(headers) else ''
                        if not name:
                            name = f'第{column + 1}欄'
                        elif header_counts[name] > 1:
                            name += f'（第{column + 1}欄）'
                        fields.append(f'{name}: {value}')
                    add(' | '.join(fields), {'section': f'第 {number} 列'})
            else:
                add(raw, {'section': '全文'})
        elif suffix == '.pdf':
            context = multiprocessing.get_context('spawn')
            receiver, sender = context.Pipe(duplex=False)
            worker = context.Process(target=_pdf_worker, args=(str(path), sender, MAX_PAGES, MAX_TEXT, MAX_PDF_PAGE_STREAM, MAX_PDF_TOTAL_STREAM), daemon=True)
            worker.start()
            sender.close()
            try:
                if not receiver.poll(PDF_TIMEOUT):
                    raise ValueError('parse_timeout')
                message = receiver.recv()
                if isinstance(message, str):
                    raise ValueError(message)
                for section in message:
                    add(section['text'], section['locator'])
            finally:
                receiver.close()
                if worker.is_alive():
                    worker.terminate()
                worker.join(timeout=5)
                worker.close()
        elif suffix == '.docx':
            with zipfile.ZipFile(path) as archive:
                infos = archive.infolist()
                if len(infos) > 2000 or sum(i.file_size for i in infos) > MAX_UNCOMPRESSED:
                    raise ValueError('archive_limit')
                info = archive.getinfo('word/document.xml')
                if info.file_size > MAX_UNCOMPRESSED or info.file_size / max(1, info.compress_size) > 200:
                    raise ValueError('archive_limit')
                data = archive.read(info)
                if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
                    raise ValueError('unsafe_xml')
                tree = ElementTree.fromstring(data)
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                for number, para in enumerate(tree.findall('.//w:p', ns), 1):
                    add(''.join(t.text or '' for t in para.findall('.//w:t', ns)), {'section': f'段落 {number}'})
        else:
            raise ValueError('unsupported_format')
    except ValueError as exc:
        if str(exc) in {'text_limit', 'encrypted_pdf', 'page_limit', 'archive_limit', 'unsafe_xml', 'unsupported_format', 'parse_timeout'}:
            raise
        raise ValueError('parse_failed') from None
    except (Exception,) as exc:
        raise ValueError('parse_failed') from None
    if not sections:
        raise ValueError('no_extractable_text')
    return sections


def _pdf_worker(path, sender, max_pages, max_text, page_limit, total_limit):
    """Isolate pypdf parsing and decompression; parent enforces a wall deadline."""
    try:
        from pypdf import PdfReader
        from pypdf.generic import ArrayObject
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ValueError('encrypted_pdf')
        if len(reader.pages) > max_pages:
            raise ValueError('page_limit')
        sections = []
        decoded_total = text_total = 0
        for number, page in enumerate(reader.pages, 1):
            decoded_page = 0
            seen = set()
            def check_stream(stream, depth=0):
                nonlocal decoded_page
                if depth > 20 or len(seen) >= 200:
                    raise ValueError('text_limit')
                obj = stream.get_object()
                identity = id(obj)
                if identity in seen:
                    return
                seen.add(identity)
                decoded_page += len(obj.get_data())
                if decoded_page > page_limit:
                    raise ValueError('text_limit')
                check_resources(obj.get('/Resources'), depth + 1)
            def check_resources(resources, depth=0):
                if resources is None:
                    return
                resources = resources.get_object()
                xobjects = resources.get('/XObject')
                if xobjects is not None:
                    for item in xobjects.get_object().values():
                        obj = item.get_object()
                        if obj.get('/Subtype') == '/Form':
                            check_stream(obj, depth)
            contents = page.get('/Contents')
            if contents is not None:
                contents = contents.get_object()
                streams = contents if isinstance(contents, ArrayObject) else [contents]
                if len(streams) > 200:
                    raise ValueError('text_limit')
                for stream in streams:
                    check_stream(stream)
            check_resources(page.get('/Resources'))
            decoded_total += decoded_page
            if decoded_total > total_limit:
                raise ValueError('text_limit')
            text = (page.extract_text() or '').strip()
            text_total += len(text)
            if text_total > max_text:
                raise ValueError('text_limit')
            if text:
                sections.append({'text': text, 'locator': {'page': number}})
        sender.send(sections)
    except ValueError as error:
        sender.send(str(error) if str(error) in {'encrypted_pdf', 'page_limit', 'text_limit'} else 'parse_failed')
    except Exception:
        sender.send('parse_failed')
    finally:
        sender.close()
