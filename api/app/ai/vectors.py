"""Local embedding vectors for isolated previews: a ranking signal only, never a permission source."""
from array import array
from contextlib import closing, contextmanager
import hashlib
import math
import operator
import os
import sqlite3
import tempfile
import threading

from app.ai import model, store

# Ollama returns JSON floats; eight 1024-dim vectors stay well under the 256KB response cap.
BATCH = 8
CANDIDATES = 30
RRF_K = 60
KEYWORD_ANCHORS = 3
# Semantic-only hits below this cosine similarity are noise for bge-m3 on short Chinese text;
# keyword hits are always kept. Calibrated with deploy/check_retrieval.py.
MIN_SIMILARITY = 0.45
_locks = {}
_guard = threading.Lock()


def model_name():
    if os.environ.get('PF_ACCEPTANCE_MODE') != 'true':
        return ''
    return os.environ.get('PF_AI_VECTOR_MODEL', '').strip()


def enabled():
    return bool(model_name())


def available(company):
    """Vectors are configured and the company's local model connection is switched on."""
    if not enabled():
        return False
    try:
        return model.settings(company).get('enabled') is True
    except (OSError, ValueError, AttributeError):
        return False


def normalize(values):
    if not isinstance(values, list) or not values or not all(type(x) in (int, float) for x in values):
        raise ValueError('Invalid embedding')
    norm = math.sqrt(sum(x * x for x in values))
    if not norm or not math.isfinite(norm):
        raise ValueError('Invalid embedding')
    return array('f', (x / norm for x in values))


def embed(company, texts):
    """Embed through the company's validated local endpoint; long input fails instead of truncating."""
    name = model_name()
    config = model.settings(company)
    if not name or not isinstance(config, dict) or config.get('enabled') is not True:
        raise ValueError('Vector model unavailable')
    config = dict(config, model=name)
    model.validate_config(config)
    vectors = []
    for start in range(0, len(texts), BATCH):
        batch = texts[start:start + BATCH]
        values = model.request(config, '/api/embed', dict(model=name, input=batch, truncate=False)).get('embeddings')
        if not isinstance(values, list) or len(values) != len(batch):
            raise ValueError('Invalid embedding response')
        vectors.extend(normalize(v) for v in values)
    if len({len(v) for v in vectors}) > 1:
        raise ValueError('Inconsistent embedding size')
    return vectors


def pack(vector):
    return vector.tobytes()


def unpack(blob):
    vector = array('f')
    vector.frombytes(blob)
    return vector


def similarity(a, b):
    return sum(map(operator.mul, a, b)) if len(a) == len(b) else -1.0


def rank(query, stored, allowed_ids):
    """Top candidates among ids that already passed every permission and version filter."""
    scored = [(similarity(query, stored[i]), i) for i in allowed_ids if i in stored]
    scored = [(s, i) for s, i in scored if s >= MIN_SIMILARITY]
    return [i for s, i in sorted(scored, key=lambda item: (-item[0], item[1]))[:CANDIDATES]]


def fuse(keyword, semantic):
    """Keep the top keyword hits in place, then fill by Reciprocal Rank Fusion (ties keep keyword order).

    Documents in one small corpus are all fairly similar to each other, so plain fusion can push a strong
    exact-term match out of the top results. Anchoring keeps keyword quality and adds what it missed."""
    anchors = list(keyword[:KEYWORD_ANCHORS])
    scores, first = {}, {}
    for ranking in (keyword, semantic):
        for position, key in enumerate(ranking):
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + position + 1)
            first.setdefault(key, len(first))
    return anchors + [key for key in sorted(scores, key=lambda key: (-scores[key], first[key])) if key not in anchors]


@contextmanager
def locked(path):
    with _guard:
        lock = _locks.setdefault(str(path), threading.Lock())
    with lock:
        yield


def starter_path(company):
    slug = hashlib.sha256(model_name().encode()).hexdigest()[:16]
    return store.root() / 'vectors' / 'starter-v1' / f'{company}-{slug}.sqlite'


def starter_vectors(db, company):
    """Vectors for the immutable starter corpus, built once per content digest beside it."""
    rows = db.execute('SELECT document_id, title, body FROM documents ORDER BY document_id').fetchall()
    expected = {r['document_id']: hashlib.sha256((r['title'] + '\n' + r['body']).encode()).hexdigest() for r in rows}
    path = starter_path(company)
    with locked(path):
        existing = {}
        if path.exists():
            try:
                with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)) as index:
                    existing = {i: (d, unpack(v)) for i, d, v in index.execute('SELECT document_id, digest, vector FROM vectors')}
            except (sqlite3.Error, ValueError):
                existing = {}  # A damaged side file is derived data: rebuild it.
        missing = [r for r in rows if existing.get(r['document_id'], (None,))[0] != expected[r['document_id']]]
        if missing:
            fresh = embed(company, [r['title'] + '\n' + r['body'] for r in missing])
            kept = {i: value for i, value in existing.items() if i in expected and value[0] == expected[i]}
            kept.update({r['document_id']: (expected[r['document_id']], v) for r, v in zip(missing, fresh)})
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix='.vectors-', suffix='.sqlite', dir=path.parent)
            os.close(fd)
            try:
                with closing(sqlite3.connect(temporary)) as index:
                    index.execute('CREATE TABLE vectors(document_id TEXT PRIMARY KEY, digest TEXT, vector BLOB)')
                    index.executemany('INSERT INTO vectors VALUES (?,?,?)', [(i, d, pack(v)) for i, (d, v) in kept.items()])
                    index.commit()
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            existing = kept
    return {i: existing[i][1] for i in expected}
