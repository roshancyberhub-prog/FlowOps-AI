from app.workflows.schema import Graph


def basic_graph() -> Graph:
    return make_graph(["trigger.manual", "action.record_result"])


def make_graph(types: list[str]) -> Graph:
    return Graph.model_validate(
        {
            "schema_version": 1,
            "nodes": [
                {
                    "id": f"node_{i}",
                    "type": node_type,
                    "config": {},
                    "position": {"x": i * 230, "y": 160},
                }
                for i, node_type in enumerate(types)
            ],
            "edges": [
                {
                    "id": f"edge_{i}",
                    "source": f"node_{i}",
                    "target": f"node_{i + 1}",
                    "sourceHandle": "true" if types[i].startswith("condition.") else "default",
                }
                for i in range(len(types) - 1)
            ],
        }
    )


def templates() -> list[dict]:
    return [
        {
            "id": "basic",
            "name": "Start from a basic workflow",
            "graph": basic_graph().model_dump(by_alias=True),
        },
        {
            "id": "qualification",
            "name": "Qualify a new lead",
            "graph": make_graph(
                [
                    "trigger.lead_created",
                    "action.validate_lead",
                    "action.detect_duplicate",
                    "action.score_lead",
                    "action.record_result",
                ]
            ).model_dump(by_alias=True),
        },
        {
            "id": "outreach",
            "name": "Draft, review and send",
            "graph": make_graph(
                [
                    "trigger.lead_created",
                    "action.validate_lead",
                    "action.detect_duplicate",
                    "action.score_lead",
                    "condition.score_threshold",
                    "action.generate_email_draft",
                    "action.request_approval",
                    "action.send_email",
                    "action.record_result",
                ]
            ).model_dump(by_alias=True),
        },
    ]
