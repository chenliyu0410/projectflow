"""Company AI policy and classification overrides for isolated previews (stored beside AI data)."""
from contextlib import contextmanager
import json
import os
import tempfile
import threading

from app.ai import store

LEVELS = {"public": 0, "internal": 1, "confidential": 2}
MODES = ("local_only", "mixed", "cloud_allowed")
SCOPES = ("project", "node", "document")
# Unclassified operational files stay confidential until an administrator explicitly relaxes the company level.
_locks = {}
_guard = threading.Lock()
DEFAULT = dict(mode="local_only", company="confidential", overrides={})


def path(company):
    return store.root() / "policy" / f"{company}.json"


def load(company):
    """Unreadable or invalid policy files fail closed to the strictest sensible defaults."""
    if company not in store.COMPANIES:
        raise ValueError("Unknown company")
    try:
        value = json.loads(path(company).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return json.loads(json.dumps(DEFAULT))
    except (OSError, ValueError):
        return dict(mode="local_only", company="confidential", overrides={})
    overrides = value.get("overrides") if isinstance(value, dict) else None
    if (not isinstance(value, dict) or value.get("mode") not in MODES or value.get("company") not in LEVELS
            or not isinstance(overrides, dict) or any(v not in LEVELS for v in overrides.values())):
        return dict(mode="local_only", company="confidential", overrides={})
    return value


@contextmanager
def locked(company):
    """Serialize load-modify-save per company within this process (the isolated preview is single-process)."""
    with _guard:
        lock = _locks.setdefault(company, threading.Lock())
    with lock:
        yield


def save(company, value):
    directory = path(company).parent
    directory.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".policy-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False)
        os.replace(name, path(company))
    finally:
        if os.path.exists(name):
            os.unlink(name)


def stricter(*levels):
    return max((level for level in levels if level), key=LEVELS.__getitem__)


class Resolver:
    """Effective level = strictest of company, project, every ancestor node and the item itself."""

    def __init__(self, value, nodes):
        self.value, self.nodes, self.cache = value, nodes, {}

    def own(self, scope, item_id):
        return self.value["overrides"].get(f"{scope}:{item_id}")

    def project(self, project_id):
        return stricter(self.value["company"], self.own("project", project_id))

    def node(self, node_id):
        # Walk up to the first cached ancestor (or the root), then resolve downwards; `seen` stops cycles.
        chain, seen, current = [], set(), node_id
        while current in self.nodes and current not in self.cache and current not in seen:
            seen.add(current)
            chain.append(current)
            current = self.nodes[current].parent_id
        level = self.cache.get(current)
        for item in reversed(chain):
            node = self.nodes[item]
            level = stricter(level, self.project(node.project_id), self.own("node", item))
            self.cache[item] = level
        return self.cache.get(node_id, self.value["company"])

    def document(self, document_id, node_id, project_id):
        inherited = self.node(node_id) if node_id else self.project(project_id)
        return stricter(inherited, self.own("document", document_id))

    def inherited(self, scope, item_id, *, node_id=None, project_id=None, parent_id=None):
        """Level a scope gets from above; an override may not be looser than this."""
        if scope == "project":
            return self.value["company"]
        if scope == "node":
            return self.node(parent_id) if parent_id else self.project(project_id)
        return self.node(node_id) if node_id else self.project(project_id)


def cloud_decision(value, level):
    """Return (eligible, reason, masked). No provider exists here, so nothing is ever sent."""
    if value["mode"] == "local_only":
        return False, "policy_local_only", False
    if level == "confidential":
        return False, "confidential_local_only", False
    return True, "no_cloud_provider", level != "public"
