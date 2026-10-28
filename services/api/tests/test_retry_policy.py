from app.execution.errors import NodeFailure, classify_error, retry_delay, should_retry


def test_transient_failures_retry_with_a_bound():
    failure = classify_error(NodeFailure("TEMPORARY", "Try later.", transient=True), "none")
    assert should_retry(failure, 1)
    assert not should_retry(failure, 3)
    assert 2 <= retry_delay(1) <= 3
    assert 4 <= retry_delay(2) <= 5
    assert retry_delay(100) <= 60


def test_uncertain_external_effects_are_not_retried():
    failure = classify_error(TimeoutError(), "external")
    assert failure.uncertain
    assert not should_retry(failure, 1)


def test_permanent_errors_do_not_retry_and_unknown_errors_are_sanitized():
    failure = classify_error(NodeFailure("INVALID", "Check the lead."), "none")
    assert not should_retry(failure, 1)
    unknown = classify_error(RuntimeError("private@example.com token=do-not-leak"), "none")
    assert "private@example.com" not in unknown.summary
    assert "do-not-leak" not in unknown.summary
