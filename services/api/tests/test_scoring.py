import pytest
from pydantic import ValidationError

from app.leads.scoring import ScoringConfig, calculate_score

FIT = {
    "name": "Fictional Buyer",
    "email": "buyer@example.com",
    "company": "Example Co",
    "job_title": "Co-Founder and CTO",
    "industry": "Software",
    "company_size": "11-50",
    "website": "https://example.com",
}


def test_baseline_score_is_reproducible_and_explains_each_rule():
    first = calculate_score(FIT, ScoringConfig())
    assert first.score == 80
    assert len(first.reasons) == 6
    assert sum(reason["points"] for reason in first.reasons) == 80
    assert first == calculate_score(dict(reversed(list(FIT.items()))), ScoringConfig())


def test_personal_email_is_only_a_heuristic_and_missing_fields_reduce_score():
    personal = calculate_score({**FIT, "email": "buyer@gmail.com"}, ScoringConfig())
    assert personal.score == 70
    empty = calculate_score(
        {"name": "Fictional Buyer", "email": "buyer@gmail.com"}, ScoringConfig()
    )
    assert empty.score == 0
    assert any(reason["points"] == -10 for reason in empty.reasons)
    assert "company" in empty.missing_fields


def test_title_matching_respects_word_boundaries_and_scores_are_clamped():
    assert calculate_score({**FIT, "job_title": "viceo"}, ScoringConfig()).score == 55
    config = ScoringConfig(
        title_weight=100,
        industry_weight=100,
        size_weight=100,
        business_email_weight=100,
        website_weight=100,
    )
    assert calculate_score(FIT, config).score == 100


def test_profile_validation_rejects_unbounded_or_invalid_weights():
    with pytest.raises(ValidationError):
        ScoringConfig(title_weight=101)
    with pytest.raises(ValidationError):
        ScoringConfig(title_weight=True)
    with pytest.raises(ValidationError):
        ScoringConfig(missing_penalty=10)
