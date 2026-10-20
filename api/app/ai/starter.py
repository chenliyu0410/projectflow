"""Additive, immutable import of the small synthetic document corpus."""
import hashlib
import json
import re
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

from pypdf import PdfReader

from app.ai import store

DATASET = "starter-v1"
AS_OF = "2026-10-20"
ROLES = {"admin", "project_owner", "reviewer", "member", "readonly"}


def safe_file(root, relative):
    if not isinstance(relative, str) or "\\" in relative:
        raise ValueError("Invalid relative path")
    p = (root / relative).resolve()
    if not p.is_relative_to(root) or not p.is_file():
        raise ValueError("Source path outside pack or missing")
    return p


def extract(path):
    if path.stat().st_size > 10_000_000:
        raise ValueError("Source too large")
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        if reader.is_encrypted or len(reader.pages) > 30:
            raise ValueError("Unsupported PDF")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if len(text.strip()) < 30:
            raise ValueError("PDF has no usable text; OCR is not supported")
        return text
    if path.suffix.lower() not in {".md", ".txt"}:
        raise ValueError("Unsupported source format")
    return path.read_text(encoding="utf-8")


def load_pack(pack):
    pack = Path(pack).resolve()
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "projectflow-rag-starter-v1" or manifest.get("as_of") != AS_OF:
        raise ValueError("Unsupported starter pack")
    files = manifest["files"]
    for relative, digest in files.items():
        if hashlib.sha256(safe_file(pack, relative).read_bytes()).hexdigest() != digest:
            raise ValueError("Source checksum mismatch")
    if "machine/documents.jsonl" not in files:
        raise ValueError("Missing document manifest")
    records = [json.loads(s) for s in safe_file(pack, "machine/documents.jsonl").read_text(encoding="utf-8").splitlines()]
    if len(records) != 24:
        raise ValueError("Expected 24 starter documents")
    seen, paths = set(), set()
    for d in records:
        doc_id, company, relative = d["document_id"], d["company_id"], d["source_path"]
        if not re.fullmatch(r"(MTG|WO|MAIL|PDF)-\d{3}", doc_id) or doc_id in seen:
            raise ValueError("Duplicate or invalid document id")
        if company not in {"food", "electronics"}:
            raise ValueError("Unknown starter company")
        if not relative.startswith("corpus/") or relative not in files or relative in paths:
            raise ValueError("Missing or duplicate canonical source")
        if d.get("synthetic") is not True or d.get("as_of") != AS_OF or type(d["is_current"]) is not bool:
            raise ValueError("Invalid source metadata")
        if type(d["version"]) is not int or d["version"] < 1 or not re.fullmatch(r"[A-Z0-9-]{1,60}", d["project_id"]):
            raise ValueError("Invalid version or project")
        date.fromisoformat(d["document_date"])
        source_roles = set(d["allowed_roles"])
        if d["classification"] == "confidential" and source_roles == {"hr", "admin"}:
            d["allowed_roles"] = ["admin"]
        elif d["classification"] == "internal" and source_roles == {"employee", "hr", "admin"}:
            d["allowed_roles"] = sorted(ROLES)
        else:
            raise ValueError("Unsupported source permission policy")
        d["text"] = extract(safe_file(pack, relative))
        seen.add(doc_id)
        paths.add(relative)
    for d in records:
        if d.get("supersedes"):
            prior = next((p for p in records if p["document_id"] == d["supersedes"]), None)
            if not prior or prior["is_current"] or prior["company_id"] != d["company_id"] or prior["project_id"] != d["project_id"]:
                raise ValueError("Invalid superseded document")
    return records, hashlib.sha256((pack / "manifest.json").read_bytes()).hexdigest()


def import_starter(pack, destination):
    records, fingerprint = load_pack(pack)
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    final = destination / DATASET
    if final.exists():
        previous = json.loads((final / "import.json").read_text(encoding="utf-8"))
        if previous["fingerprint"] != fingerprint:
            raise ValueError("Different starter data already installed; overwrite is forbidden")
        return dict(previous, already_imported=True)
    # The temporary directory is a direct child of the verified destination.
    # Directory publication is atomic, preserving both the legacy data and readers.
    with tempfile.TemporaryDirectory(prefix=".starter-", dir=destination) as temporary:
        stage = Path(temporary).resolve()
        if stage.parent != destination:
            raise ValueError("Invalid staging directory")
        content = stage / DATASET
        content.mkdir()
        for company in sorted({d["company_id"] for d in records}):
            db = sqlite3.connect(content / f"{company}.sqlite")
            try:
                db.executescript("""
                    CREATE TABLE documents (document_id TEXT PRIMARY KEY, project_id TEXT,
                        title TEXT, kind TEXT, current INTEGER, roles TEXT, body TEXT, metadata TEXT);
                    CREATE VIRTUAL TABLE search USING fts5(document_id UNINDEXED, words);
                    CREATE TABLE work_orders (document_id TEXT PRIMARY KEY, owner TEXT,
                        due_date TEXT, status TEXT);
                """)
                for d in (r for r in records if r["company_id"] == company):
                    metadata = {k: v for k, v in d.items() if k != "text"}
                    db.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)", (
                        d["document_id"], d["project_id"], d["title"], d["document_type"],
                        int(d["is_current"]), json.dumps(d["allowed_roles"]),
                        d["text"], json.dumps(metadata, ensure_ascii=False)))
                    # Repeated header metadata does not improve relevance.
                    body = d["text"].split("## ", 1)[-1] if "## " in d["text"] else d["text"]
                    db.execute("INSERT INTO search VALUES (?,?)", (d["document_id"], " ".join(store.tokens(d["title"] + " " + body))))
                    if d["document_type"] == "工單":
                        match = re.search(r"負責人：(.+?)。期限：(\d{4}-\d{2}-\d{2})。截至" + AS_OF + r"狀態：(未開始|處理中|待確認|已完成)。", d["text"])
                        if not match:
                            raise ValueError("Incomplete work-order fields")
                        date.fromisoformat(match[2])
                        db.execute("INSERT INTO work_orders VALUES (?,?,?,?)", (d["document_id"], *match.groups()))
                db.commit()
                if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Invalid generated database")
            finally:
                db.close()
        result = dict(fingerprint=fingerprint, as_of=AS_OF, documents=len(records),
                      companies=sorted({d["company_id"] for d in records}), dataset=DATASET)
        (content / "import.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        try:
            content.rename(final)
        except OSError:
            if not (final / "import.json").is_file():
                raise
            published = json.loads((final / "import.json").read_text(encoding="utf-8"))
            if published["fingerprint"] != fingerprint:
                raise ValueError("Different starter data already installed; overwrite is forbidden") from None
            return dict(published, already_imported=True)
    return result


def visible_projects(db, role):
    titles = {"ONBOARD-10": "十月新人報到", "TRAIN-10": "十月新人課程",
              "KIT-10": "新人歡迎包", "GENERAL": "一般作業指南",
              "HR-BUDGET": "人資預算", "HF-TRAIN-10": "新人課程"}
    rows = [dict(r) for r in db.execute("""
        SELECT DISTINCT project_id, project_id AS title FROM documents
        WHERE EXISTS (SELECT 1 FROM json_each(roles) WHERE value=?) ORDER BY project_id
    """, (role,))]
    for row in rows:
        row["title"] = titles.get(row["project_id"], row["project_id"])
    return rows


def pending_orders(db, role, project_id=None):
    rows = [dict(r) for r in db.execute("""
        SELECT d.*, w.owner, w.due_date, w.status FROM work_orders w
        JOIN documents d USING(document_id)
        WHERE w.status != '已完成' AND d.current=1
          AND EXISTS (SELECT 1 FROM json_each(d.roles) WHERE value=?)
          AND (? IS NULL OR d.project_id=?) ORDER BY w.due_date, d.document_id
    """, (role, project_id, project_id))]
    for row in rows:
        row["overdue_days"] = max(0, (date.fromisoformat(AS_OF) - date.fromisoformat(row["due_date"])).days)
    return rows
