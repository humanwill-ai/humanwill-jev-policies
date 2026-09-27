"""Synthetic operator-owned approval fixtures, not a production target resolver.

Targets are independently annotated in fixtures, never inferred from gold labels
or trusted from request metadata. Real connectors must resolve every governed
target/operation and bind that evidence to the exact event before using this rule.
"""

CODING_ROUTE = "company-approved-coding-model"
APPROVED_OPERATIONS = frozenset(
    {
        ("https://git.example.test/company/project", "push"),
        ("company-coding-session", "respond"),
    }
)


def disclosure_facts(context):
    if not isinstance(context, dict) or set(context) != {
        "coding_route",
        "lookup_complete",
        "targets",
    }:
        raise ValueError("Invalid synthetic disclosure context")
    if context["coding_route"] != CODING_ROUTE:
        raise ValueError("This suite requires the configured approved coding route")
    if type(context["lookup_complete"]) is not bool or not isinstance(context["targets"], list):
        raise ValueError("Invalid synthetic destination lookup")
    operations = []
    for target in context["targets"]:
        if not isinstance(target, dict) or set(target) != {"destination", "operation"}:
            raise ValueError("Invalid synthetic target")
        if not all(isinstance(value, str) and value for value in target.values()):
            raise ValueError("Invalid synthetic target value")
        operations.append((target["destination"], target["operation"]))
    facts = {"destination.coding_route_approved": True}
    if context["lookup_complete"]:
        # No target/approval is false, never an all([]) authorization shortcut.
        # A scope judgment still distinguishes review-only from onward sharing.
        facts["destination.onward_approved"] = bool(operations) and all(
            operation in APPROVED_OPERATIONS for operation in operations
        )
    # Resolver failures deliberately leave evidence missing, not fake a lookup.
    return facts
