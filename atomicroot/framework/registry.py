"""Immutable trusted fact/tool definitions. No generic public mutation API."""
from dataclasses import dataclass, asdict
from types import MappingProxyType

from atomicroot.authority.policy_engine import FactSource, money_integer, finite_strings


@dataclass(frozen=True)
class FactDefinition:
    fact_id: str
    type: str
    scope: str
    source: str
    prefix: str
    updater: str
    transitions: tuple[str, ...]
    approval: str
    field: str | None = None

    def source_descriptor(self):
        def decode(raw):
            value = raw[self.field] if self.field else raw
            if self.type == "int": return money_integer(value)
            if self.type == "set": return finite_strings(value)
            return value
        return FactSource(self.prefix, self.scope, self.type, decode)


def fact(name, kind, prefix, source, updater, transitions, approval="none", field=None, scope="task"):
    return FactDefinition(name, kind, scope, source, prefix, updater, tuple(transitions), approval, field)


FACT_REGISTRY = MappingProxyType({f.fact_id: f for f in (
    fact("budget_limit", "int", "contract3", "approved contract", "ContractService", ["activate revision"], "exact proposal", "budget_limit"),
    fact("allowed_recipients", "set", "contract3", "approved contract", "ContractService", ["activate revision"], "exact proposal", "allowed_recipients"),
    fact("allowed_tools", "set", "contract3", "approved contract", "ContractService", ["activate revision"], "exact proposal", "allowed_tools"),
    fact("allowed_resources", "set", "contract3", "approved contract", "ContractService", ["activate revision"], "exact proposal", "allowed_resources"),
    fact("allowed_agents", "set", "contract3", "approved delegation", "ContractService", ["activate revision"], "exact proposal", "allowed_agents"),
    fact("purpose", "str", "contract3", "approved contract", "ContractService", ["activate revision"], "exact proposal", "purpose"),
    fact("unknown_release", "str", "contract3", "approved contract", "ContractService", ["DENY", "ESCALATE"], "exact proposal", "unknown_release"),
    fact("budget_used", "int", "budget", "receiver settlement ledger", "Dispatcher", ["settle reservation"]),
    fact("budget_reserved", "int", "reserved", "accepted intent ledger", "Gateway/Dispatcher", ["reserve", "settle", "definite failure release"]),
    fact("exposure", "set", "exposure", "committed read events", "Gateway", ["monotone union"]),
    fact("document_version", "int", "document", "storage content digest", "StorageService", ["ingest new version"], field="version", scope="document"),
    fact("document_digest", "str", "document", "storage content digest", "StorageService", ["ingest new version"], field="digest", scope="document"),
    fact("label", "str", "label", "owner attestation of digest/purpose", "LabelManager", ["set for current digest", "invalidate on content change"], "owner authentication", "label", "document"),
    fact("approval", "str", "consent", "review record", "ApprovalBroker/Gateway", ["NONE -> APPROVED -> CONSUMED", "REJECTED"], "operation review", "status", "operation"),
    fact("operation_committed", "bool", "operation", "committed intent", "Gateway", ["false -> true"], scope="operation"),
)})
SOURCES = MappingProxyType({name: f.source_descriptor() for name, f in FACT_REGISTRY.items()})


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    effect_class: str
    external: bool
    spending: bool
    resource: bool
    required: frozenset[str]
    writes: tuple[str, ...] = ()
    updater: str = "Gateway"

    def write_set(self, task, operation, grant):
        return ([f"operation:{task}:{operation}"] + [f"{prefix}:{task}" for prefix in self.writes]
                + ([f"consent:{task}:{operation}"] if grant else []))

    @property
    def read_facts(self):
        common = ("budget_limit", "budget_used", "budget_reserved", "allowed_tools", "allowed_agents", "purpose", "exposure", "unknown_release", "operation_committed", "approval")
        return (common + (("allowed_recipients",) if self.external else ())
                + (("document_version", "document_digest", "label", "allowed_resources") if self.resource else ()))


TOOLS = MappingProxyType({t.name: t for t in (
    ToolDefinition("read_document", "read", False, False, True, frozenset({"resource", "digest"}), ("exposure",)),
    ToolDefinition("send_email", "send", True, False, False, frozenset({"to", "body"})),
    ToolDefinition("transfer_funds", "transfer", True, True, False, frozenset({"to", "amount"}), ("reserved",)),
    ToolDefinition("deploy", "deploy", True, False, True, frozenset({"resource", "digest", "to"})),
)})


def registry_preview():
    return [asdict(f) for f in FACT_REGISTRY.values()]
