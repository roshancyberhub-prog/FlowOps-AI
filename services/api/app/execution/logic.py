from app.workflows.schema import Graph


def compare(context: dict, field: str, operator: str, value: object) -> bool:
    current: object = context
    for part in field.split("."):
        current = current.get(part) if isinstance(current, dict) else None
    if operator == "exists":
        return current is not None
    if operator == "missing":
        return current is None
    if operator == "eq":
        return (
            type(current) is type(value)
            and current == value
            or (
                isinstance(current, (int, float))
                and not isinstance(current, bool)
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and current == value
            )
        )
    if operator == "contains":
        return isinstance(current, str) and isinstance(value, str) and value in current
    if not (
        isinstance(current, (int, float))
        and not isinstance(current, bool)
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
    ):
        return False
    return {
        "gt": current > value,
        "gte": current >= value,
        "lt": current < value,
        "lte": current <= value,
    }.get(operator, False)


def next_node(graph: Graph, node_id: str, handle: str = "default") -> str | None:
    return next(
        (
            edge.target
            for edge in graph.edges
            if edge.source == node_id and (edge.source_handle or "default") == handle
        ),
        None,
    )
