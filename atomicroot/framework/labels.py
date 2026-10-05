"""Explicit owner labels bind one resource version/digest and purpose set."""
import hashlib
from atomicroot.authority.policy_engine import valid_identity, finite_strings
from atomicroot.authority.ticket import freeze_json


def content_digest(content):
    if type(content) is not str or len(content.encode("utf-8")) > 8192:
        raise ValueError("content must be a string <=8192 bytes")
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


class StorageService:
    def __init__(self, store): self.store = store

    def ingest(self, resource, content, principal, *, source="owner upload"):
        valid_identity(resource)
        principal.require("owner", resource=resource)
        digest = content_digest(content)
        if source not in {"owner upload", "trusted metadata", "external document"}:
            raise ValueError("unregistered provenance source")
        with self.store.transaction() as conn:
            _, old = self.store.value(conn, f"document:{resource}")
            version = (old["version"] if old else 0) + 1
            data = {"resource": resource, "digest": digest, "version": version,
                    "content": content, "source": source, "stored_by": principal.subject,
                    "instruction_trust": "UNTRUSTED", "factual_accuracy": "UNVERIFIED"}
            self.store.put(conn, f"document:{resource}", data)
            # Every content/version update invalidates label scope, even same bytes.
            self.store.put(conn, f"label:{resource}", {"label": "UNKNOWN", "digest": digest,
                "version": version, "purposes": [], "label_set_by": "StorageService",
                "source": "official default: new version", "resource": resource})
            self.store.audit(conn, "INGEST", principal.subject, {k: v for k, v in data.items() if k != "content"})
        return {"resource": resource, "digest": digest, "version": version}


class LabelManager:
    def __init__(self, store): self.store = store

    def set_label(self, resource, digest, version, label, purposes, principal):
        valid_identity(resource)
        principal.require("owner", resource=resource)
        if label not in {"PUBLIC", "SENSITIVE", "UNKNOWN"}: raise ValueError("unsupported label")
        purposes = list(finite_strings(freeze_json(purposes)))
        if not purposes: raise ValueError("explicit purpose scope required")
        with self.store.transaction() as conn:
            _, document = self.store.value(conn, f"document:{resource}")
            if not document or document["digest"] != digest or document["version"] != version:
                raise ValueError("label requires current content version and digest")
            data = {"resource": resource, "digest": digest, "version": version, "label": label,
                    "purposes": purposes, "source": "authenticated owner attestation",
                    "label_set_by": principal.subject}
            self.store.put(conn, f"label:{resource}", data)
            self.store.audit(conn, "LABEL", principal.subject, data)
        return data

    @staticmethod
    def resolve(reader, resource, digest, purpose):
        document = reader.read(f"document:{resource}")
        label = reader.read(f"label:{resource}")
        if document["digest"] != digest: raise ValueError("resource digest changed; resolve before authorization")
        if label["label"] not in {"PUBLIC", "SENSITIVE", "UNKNOWN"}: raise ValueError("invalid label fact")
        scoped = (label["digest"] == digest and label["version"] == document["version"]
                  and purpose in label["purposes"])
        return document, label["label"] if scoped else "UNKNOWN"
