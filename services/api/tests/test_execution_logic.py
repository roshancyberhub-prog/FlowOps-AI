from app.execution.logic import compare, next_node
from app.workflows.graph import validate_graph
from app.workflows.templates import make_graph


def test_conditions_handle_missing_values_and_strict_numeric_comparison():
    assert compare({"lead": {"score": 80}}, "lead.score", "gte", 70)
    assert not compare({"lead": {"score": "80"}}, "lead.score", "gte", 70)
    assert not compare({"lead": {"score": True}}, "lead.score", "gt", 0)
    assert compare({}, "lead.email", "missing", None)
    assert not compare({}, "lead.email", "eq", "")
    assert compare({"lead": {"company": "Acme Tools"}}, "lead.company", "contains", "Tools")


def test_branch_selection_does_not_execute_the_other_branch():
    graph = make_graph(["trigger.manual", "condition.score_threshold", "action.record_result"])
    assert next_node(graph, "node_1", "true") == "node_2"
    assert next_node(graph, "node_1", "false") is None


def test_generic_approval_cannot_authorize_email():
    graph = make_graph(["trigger.manual", "action.request_approval", "action.record_result"])
    graph.nodes[1].config = {"kind": "continue", "message": "Review before continuing."}
    assert validate_graph(graph, "owner").valid
    graph = make_graph(
        [
            "trigger.manual",
            "action.generate_email_draft",
            "action.request_approval",
            "action.send_email",
        ]
    )
    graph.nodes[2].config = {"kind": "continue"}
    assert "APPROVAL_REQUIRED" in {x.code for x in validate_graph(graph, "owner").errors}
