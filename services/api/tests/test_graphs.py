import pytest

from app.workflows.graph import validate_graph


def graph(types):
    return {
        "schema_version": 1,
        "nodes": [{"id": str(i), "type": t, "config": {}} for i, t in enumerate(types)],
        "edges": [{"source": str(i), "target": str(i + 1)} for i in range(len(types) - 1)],
    }


def test_simple_graph_produces_deterministic_plan():
    result = validate_graph(
        graph(["trigger.manual", "action.validate_lead", "action.record_result"]), "owner"
    )
    assert result.valid
    assert result.order == ["0", "1", "2"]


@pytest.mark.parametrize(
    "change,code",
    [
        (lambda g: g["nodes"].append(g["nodes"][0]), "DUPLICATE_NODE"),
        (lambda g: g["nodes"][1].update(type="action.arbitrary_code"), "UNKNOWN_NODE"),
        (lambda g: g["edges"].append({"source": "missing", "target": "1"}), "UNKNOWN_EDGE_NODE"),
        (lambda g: g["edges"].append({"source": "1", "target": "0"}), "CYCLE"),
        (lambda g: g["edges"].clear(), "DISCONNECTED_NODE"),
    ],
)
def test_invalid_topologies_are_rejected(change, code):
    data = graph(["trigger.manual", "action.record_result"])
    change(data)
    result = validate_graph(data, "owner")
    assert not result.valid
    assert code in {issue.code for issue in result.errors}


def test_email_cannot_skip_approval():
    result = validate_graph(graph(["trigger.manual", "action.send_email"]), "owner")
    assert not result.valid
    assert "APPROVAL_REQUIRED" in {issue.code for issue in result.errors}


def test_approval_must_follow_a_draft():
    result = validate_graph(
        graph(["trigger.manual", "action.request_approval", "action.send_email"]), "owner"
    )
    assert not result.valid
    assert "DRAFT_REQUIRED" in {issue.code for issue in result.errors}


def test_email_path_with_draft_and_approval_is_valid_for_owner():
    data = graph(
        [
            "trigger.manual",
            "action.generate_email_draft",
            "action.request_approval",
            "action.send_email",
        ]
    )
    assert validate_graph(data, "owner").valid
    assert not validate_graph(data, "member").valid


def test_condition_requires_valid_branch_handle_and_configuration():
    data = graph(["trigger.manual", "condition.score_threshold", "action.record_result"])
    data["nodes"][1]["config"] = {"value": 70}
    assert not validate_graph(data, "owner").valid
    data["edges"][1]["sourceHandle"] = "true"
    assert validate_graph(data, "owner").valid
    data["nodes"][1]["config"]["value"] = 101
    assert not validate_graph(data, "owner").valid


def test_sending_a_new_draft_requires_a_fresh_approval():
    data = graph(
        [
            "trigger.manual",
            "action.generate_email_draft",
            "action.request_approval",
            "action.generate_email_draft",
            "action.send_email",
        ]
    )
    assert not validate_graph(data, "owner").valid


def test_trigger_must_connect_to_an_action():
    assert not validate_graph(graph(["trigger.manual"]), "owner").valid


def test_numeric_condition_rejects_a_text_comparison_value():
    data = graph(["trigger.manual", "condition.field", "action.record_result"])
    data["edges"][1]["sourceHandle"] = "true"
    data["nodes"][1]["config"] = {"field": "lead.score", "operator": "gte", "value": "wrong"}
    assert not validate_graph(data, "owner").valid
