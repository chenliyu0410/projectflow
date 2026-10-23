"""Local-only policy boundary for AI data requests (not a cloud adapter)."""
from dataclasses import dataclass
import json

from app.ai import masking, model, policy, store

LEVELS = {"public": 0, "internal": 1, "confidential": 2}


@dataclass
class Prepared:
    info: dict
    content: dict | None
    config: dict
    documents: list
    catalog: list
    cloud_content: dict | None = None

    def preview(self):
        # Only data fields; fixed system instructions and HTTP envelope are omitted.
        return {"gateway": dict(self.info), "content": self.content, "cloud_content": self.cloud_content}

    def run(self):
        if self.info["route"] != "local" or self.content is None:
            raise ValueError("No permitted model request")
        try:
            if self.info["function"] == "rag":
                result = model.answer(self.config, self.content["question"], self.documents, self.content.get("as_of"))
            else:
                result = model.choose_query(self.config, self.content["question"], self.catalog)
        except Exception:
            self.info["outcome"] = "failed"
            raise
        self.info["outcome"] = "completed"
        return result


def prepare(company, role, function, question, documents=(), catalog=(), *, use_model=True, reason=None, as_of=None, mask_terms=()):
    if company not in store.COMPANIES or function not in {"rag", "sql", "work_orders"}:
        raise ValueError("Unsupported gateway scope")
    level, classification_reason = "internal", "question_floor"
    for d in documents:
        try:
            metadata = json.loads(d["metadata"])
            roles = json.loads(d["roles"])
            if not isinstance(metadata, dict) or not isinstance(roles, list):
                raise ValueError()
            if metadata.get("company_id") != company or role not in roles:
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise PermissionError("Invalid document scope") from None
        classification = metadata.get("classification")
        if not isinstance(classification, str) or classification not in LEVELS:
            level, classification_reason = "confidential", "unclassified"
        elif LEVELS[classification] > LEVELS[level]:
            level, classification_reason = classification, "source_level"
    # The company level is inherited by operational files (formal index); teaching packs keep their own labels.
    company_policy = policy.load(company)
    eligible, cloud_reason, masked = policy.cloud_decision(company_policy, level)
    info = dict(policy="local_only", cloud_enabled=False, function=function,
                classification=level, classification_reason=classification_reason,
                route="none", reason=reason or "model_disabled", outcome="not_sent",
                source_count=len(documents), sent_count=0, model="", ai_policy=company_policy["mode"],
                cloud=dict(eligible=eligible, reason=cloud_reason, masked=masked, provider=None, sent=False))
    content = None
    config = {}
    sent = []
    if use_model:
        if function == "rag":
            # Ranked order is kept; sources that do not fit are listed to the user but not sent.
            sent = model.fit_documents(question, documents, as_of)
            content = model.answer_content(question, sent, as_of) if sent else None
        else:
            content = model.query_content(question, catalog)
        try:
            config = model.settings(company)
            if not isinstance(config, dict) or type(config.get("enabled")) is not bool:
                raise ValueError("Invalid settings")
            if config["enabled"]:
                model.validate_config(config)
                if content is None:
                    info.update(reason="context_too_large")
                else:
                    info.update(route="local", reason="local_only", model=config["model"])
        except (OSError, KeyError, TypeError, ValueError):
            info.update(route="blocked", reason="invalid_config")
            content = None
    if info["route"] == "local":
        info["sent_count"] = len(sent)
    cloud_content = None
    if eligible and content is not None:
        cloud_content = cloud_payload(content, mask_terms if masked else None)
        info["cloud"]["masked_counts"] = cloud_content.pop("_counts")
    return Prepared(info, content, config, sent, list(catalog), cloud_content)


def cloud_payload(content, terms):
    """What a cloud request would carry: internal text masked, the placeholder mapping kept out."""
    masker = masking.Masker(terms) if terms is not None else None
    def clean(text):
        return masker.mask(text) if masker and isinstance(text, str) else text
    payload = dict(question=clean(content["question"]))
    if "as_of" in content:
        payload["as_of"] = content["as_of"]
    if "sources" in content:
        payload["sources"] = [dict(s, text=clean(s["text"]), title=clean(s.get("title", ""))) for s in content["sources"]]
    if "queries" in content:
        payload["queries"] = content["queries"]
    payload["_counts"] = dict(masker.counts) if masker else {}
    return payload
