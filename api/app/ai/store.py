import collections
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile

COMPANIES = {'food', 'hemu', 'electronics', 'events', 'software', 'construction'}
TABLES = ('companies', 'people', 'projects', 'tasks', 'suppliers', 'purchase_orders', 'expenses', 'quality_checks', 'risks', 'notes')
PROJECT_TABLES = {'projects', 'tasks', 'purchase_orders', 'expenses', 'quality_checks', 'risks'}
AS_OF = '2026-10-11'


def root():
    return Path(os.environ.get('PF_AI_ROOT', '/var/lib/projectflow-ai'))


def tokens(text):
    result = []
    for word in re.findall(r'[a-z0-9]+(?:[-_][a-z0-9]+)*|[\u4e00-\u9fff]+', text.lower()):
        if '\u4e00' <= word[0] <= '\u9fff':
            result.extend(word[i:i+2] for i in range(len(word)-1))
        else:
            result.append(word)
    return result


def connect(company, dataset='dataset-v1'):
    if dataset not in {'dataset-v1', 'starter-v1'}: raise ValueError('Unknown dataset')
    if company not in COMPANIES: raise FileNotFoundError('Unknown company')
    path = root() / dataset / f'{company}.sqlite'
    db = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    return db


def import_pack(pack, destination):
    """Publish only a fully validated import; never touch the operational DB."""
    pack, destination = Path(pack), Path(destination)
    manifest = json.loads((pack/'manifest.json').read_text(encoding='utf-8'))
    fingerprint = hashlib.sha256((pack/'manifest.json').read_bytes()).hexdigest()
    destination.mkdir(parents=True, exist_ok=True)
    final = destination/'dataset-v1'
    if final.exists():
        installed = json.loads((final/'import.json').read_text(encoding='utf-8'))
        if installed['fingerprint'] != fingerprint: raise ValueError('Different data already installed')
        return dict(installed, already_imported=True)
    for relative, digest in manifest['files'].items():
        p = (pack/relative).resolve()
        if not p.is_relative_to(pack.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:
            raise ValueError('Source checksum mismatch')
    documents = [json.loads(line) for line in (pack/'rag/documents.jsonl').read_text(encoding='utf-8').splitlines()]
    questions = [json.loads(line) for line in (pack/'evaluation/sql_questions.jsonl').read_text(encoding='utf-8').splitlines()]
    first_company = questions[0]['company_id']
    source_queries = [q['sql'] for q in questions if q['company_id']==first_company]
    trusted_catalog = catalog()
    if source_queries != [q['sql'] for q in trusted_catalog]: raise ValueError('Unexpected query catalog')
    if any(d['company_id'] not in COMPANIES or not isinstance(d['allowed_roles'],list) for d in documents): raise ValueError('Invalid document scope')
    stage = Path(tempfile.mkdtemp(prefix='.import-',dir=destination))
    try:
        source = sqlite3.connect((pack/'projectflow_demo.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
        try:
            if source.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or source.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('Invalid source database')
            actual_tables={r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if actual_tables!=set(TABLES): raise ValueError('Unexpected tables')
            for cid in sorted(COMPANIES):
                db = sqlite3.connect(stage/f'{cid}.sqlite')
                try:
                    source.backup(db)
                    for table in TABLES: db.execute(f'DELETE FROM {table} WHERE company_id<>?',(cid,))
                    if db.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('Foreign key mismatch')
                    db.execute('CREATE TABLE documents (document_id TEXT PRIMARY KEY, project_id TEXT, title TEXT, kind TEXT, current INTEGER, roles TEXT, body TEXT, metadata TEXT)')
                    db.execute('CREATE VIRTUAL TABLE search USING fts5(document_id UNINDEXED, words)')
                    project_ids={r[0] for r in db.execute('SELECT project_id FROM projects')}
                    for d in (d for d in documents if d['company_id']==cid):
                        if d['project_id'] and d['project_id'] not in project_ids: raise ValueError('Invalid document project')
                        db.execute('INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)',(d['document_id'],d['project_id'],d['title'],d['document_type'],int(d['is_current']),json.dumps(d['allowed_roles']),d['text'],json.dumps({k:v for k,v in d.items() if k!='text'},ensure_ascii=False)))
                        db.execute('INSERT INTO search VALUES (?,?)',(d['document_id'],' '.join(tokens(d['title']+' '+d['text']))))
                    db.commit()
                    db.execute('VACUUM')
                    if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Invalid import')
                finally: db.close()
        finally: source.close()
        result={'fingerprint':fingerprint,'as_of':AS_OF,'documents':len(documents),'counts':manifest['counts']['counts'],'companies':sorted(COMPANIES)}
        (stage/'import.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
        stage.rename(final)
        return result
    finally:
        if stage.exists():
            assert stage.resolve().parent == destination.resolve()
            shutil.rmtree(stage)


def catalog():
    return json.loads(Path(__file__).with_name('queries.json').read_text(encoding='utf-8'))


def search(db, question, role, project_id=None, include_history=False, limit=6):
    clean = re.sub('目前|有哪些|請問|一下|幫我|什麼|多少|資料|專案', ' ', question)
    words = list(dict.fromkeys(tokens(clean)))[:60]
    if not words: return []
    match = ' OR '.join('"'+w.replace('"','""')+'"' for w in words)
    query = '''SELECT d.*, bm25(search) AS rank FROM search JOIN documents d ON d.document_id=search.document_id
        WHERE search MATCH ? AND (d.current=1 OR ?) AND EXISTS (SELECT 1 FROM json_each(d.roles) WHERE value=?)
        AND (? IS NULL OR d.project_id=? OR d.project_id IS NULL) ORDER BY rank,d.document_id LIMIT ?'''
    return [dict(r) for r in db.execute(query,(match,int(include_history),role,project_id,project_id,limit))]


def execute_query(db, query_id, company, project_id=None):
    query=next((q for q in catalog() if q['query_id']==query_id),None)
    if query is None: raise ValueError('Unknown query')
    params={'company_id':company,'as_of':AS_OF,'project_id':project_id}
    sql=query['sql']
    if project_id:
        ctes=[f'{table} AS (SELECT * FROM main.{table} WHERE project_id=:project_id)' for table in sorted(PROJECT_TABLES)]
        sql='WITH '+', '.join(ctes)+' '+sql
    allowed_functions={'count','sum','round','substr'}
    def authorize(action, arg1, arg2, database, trigger):
        if action==sqlite3.SQLITE_SELECT: return sqlite3.SQLITE_OK
        if action==sqlite3.SQLITE_READ and arg1 in TABLES: return sqlite3.SQLITE_OK
        if action==sqlite3.SQLITE_FUNCTION and arg2 in allowed_functions: return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    remaining=[10000]
    def progress():
        remaining[0]-=1
        return int(remaining[0]<=0)
    db.set_authorizer(authorize)
    db.set_progress_handler(progress,1000)
    try:
        cursor=db.execute(sql,params)
        records=[dict(r) for r in cursor.fetchmany(201)]
        return dict(query_id=query_id,label=query['label'],sql=sql,parameters=params,columns=[d[0] for d in cursor.description],rows=records[:200],truncated=len(records)>200)
    finally:
        db.set_authorizer(None)
        db.set_progress_handler(None,0)
