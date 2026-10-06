"""Validate exact model context using the Authority's existing snapshot reader."""
import json
from atomicroot.framework.labels import LabelManager
from atomicroot.authority.policy_engine import valid_identity


def validate_model_context(reader, document, request):
    context = json.loads(document["content"])
    if type(context) is not dict or set(context) != {"messages", "sources", "provider", "model", "prompt_version"}:
        raise ValueError("invalid server model context")
    if context["provider"] != request["recipient"] or not isinstance(context["model"], str):
        raise ValueError("model provider binding mismatch")
    if type(context["messages"]) is not list or type(context["sources"]) is not list:
        raise ValueError("invalid model messages/sources")
    for message in context["messages"]:
        if type(message) is not dict or set(message) != {"role", "content"} or message["role"] not in {"system", "user"} or type(message["content"]) is not str:
            raise ValueError("invalid model message")
    bindings = []
    for source in context["sources"]:
        if type(source) is not dict or set(source) != {"resource", "digest"}: raise ValueError("invalid source binding")
        valid_identity(source["resource"])
        _, label = LabelManager.resolve(reader, source["resource"], source["digest"], request["purpose"])
        bindings.append({"resource": source["resource"], "label": label})
    # Derive concrete facts only. Permission predicates are encoded in the same
    # trusted AST as every other policy and evaluated by Z3, not this reader.
    return bindings
