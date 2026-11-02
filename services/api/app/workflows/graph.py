import heapq

from pydantic import ValidationError

from app.workflows.registry import REGISTRY
from app.workflows.schema import Graph, Issue, ValidationResult


def validate_graph(data: dict | Graph, role: str) -> ValidationResult:
    issues: list[Issue] = []

    def issue(code: str, message: str, node: str | None = None) -> None:
        issues.append(Issue(code=code, message=message, node_id=node))

    try:
        graph = data if isinstance(data, Graph) else Graph.model_validate(data)
    except ValidationError as exc:
        return ValidationResult(
            valid=False,
            errors=[Issue(code="INVALID_SCHEMA", message=e["msg"]) for e in exc.errors()],
            order=[],
        )
    nodes = {node.id: node for node in graph.nodes}
    if len(nodes) != len(graph.nodes):
        return ValidationResult(
            valid=False,
            errors=[Issue(code="DUPLICATE_NODE", message="Each node must have a unique ID.")],
            order=[],
        )
    triggers = []
    for node in graph.nodes:
        spec = REGISTRY.get(node.type)
        if spec is None:
            issue("UNKNOWN_NODE", f"Unknown node type: {node.type}.", node.id)
            continue
        if spec.category == "trigger":
            triggers.append(node.id)
        if role not in spec.roles:
            issue("PERMISSION_DENIED", f"Your role cannot publish {spec.title}.", node.id)
        try:
            spec.config.model_validate(node.config)
        except ValidationError as exc:
            for error in exc.errors():
                issue(
                    "INVALID_CONFIG", f"{'.'.join(map(str, error['loc']))}: {error['msg']}", node.id
                )
    if len(triggers) != 1:
        issue("INVALID_TRIGGER", "A workflow requires exactly one trigger.")
    outgoing: dict[str, list[str]] = {key: [] for key in nodes}
    incoming: dict[str, list[str]] = {key: [] for key in nodes}
    handles: set[tuple[str, str]] = set()
    edge_ids = [edge.id for edge in graph.edges if edge.id is not None]
    if len(set(edge_ids)) != len(edge_ids):
        issue("DUPLICATE_EDGE", "Each connection must have a unique ID.")
    for edge in graph.edges:
        if edge.source not in nodes or edge.target not in nodes:
            issue("UNKNOWN_EDGE_NODE", "Connections must reference existing nodes.")
            continue
        spec = REGISTRY.get(nodes[edge.source].type)
        handle = edge.source_handle or "default"
        if spec and handle not in spec.outputs:
            issue(
                "INVALID_HANDLE", "Choose a valid output handle for this connection.", edge.source
            )
        if (edge.source, handle) in handles:
            issue(
                "DUPLICATE_OUTPUT", "Each output supports one connection in version 1.", edge.source
            )
        handles.add((edge.source, handle))
        outgoing[edge.source].append(edge.target)
        incoming[edge.target].append(edge.source)
    counts = {key: len(value) for key, value in incoming.items()}
    ready = [key for key, count in counts.items() if count == 0]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        current = heapq.heappop(ready)
        order.append(current)
        for target in sorted(outgoing[current]):
            counts[target] -= 1
            if counts[target] == 0:
                heapq.heappush(ready, target)
    if len(order) != len(nodes):
        issue("CYCLE", "Workflow loops are not supported.")
    ranks = {key: i for i, key in enumerate(order)}
    ancestors: dict[str, set[str]] = {}
    for key in order:
        ancestors[key] = set(incoming[key])
        for parent in incoming[key]:
            ancestors[key].update(ancestors.get(parent, set()))
        if key not in triggers and len(incoming[key]) != 1:
            issue(
                "DISCONNECTED_NODE",
                "Connect this node to exactly one parent. Joins are not supported.",
                key,
            )
        if key in triggers and incoming[key]:
            issue("INVALID_TRIGGER", "A trigger cannot have an incoming connection.", key)
        spec = REGISTRY.get(nodes[key].type)
        if spec and spec.category in {"trigger", "condition"} and not outgoing[key]:
            issue("MISSING_OUTPUT", "Connect this node to a following action.", key)
        types = {nodes[parent].type for parent in ancestors[key]}
        if (
            nodes[key].type == "action.request_approval"
            and nodes[key].config.get("kind", "email") == "email"
            and "action.generate_email_draft" not in types
        ):
            issue("DRAFT_REQUIRED", "Generate an outreach draft before requesting approval.", key)
        if nodes[key].type == "action.send_email":
            latest_draft = max(
                (
                    ranks[p]
                    for p in ancestors[key]
                    if nodes[p].type == "action.generate_email_draft"
                ),
                default=-1,
            )
            latest_approval = max(
                (
                    ranks[p]
                    for p in ancestors[key]
                    if nodes[p].type == "action.request_approval"
                    and nodes[p].config.get("kind", "email") == "email"
                ),
                default=-1,
            )
            if latest_approval <= latest_draft:
                issue(
                    "APPROVAL_REQUIRED", "Every email send must follow an approval checkpoint.", key
                )
            if "action.generate_email_draft" not in types:
                issue("DRAFT_REQUIRED", "Every email send must follow a validated draft.", key)
    return ValidationResult(valid=not issues, errors=issues, order=order if not issues else [])
