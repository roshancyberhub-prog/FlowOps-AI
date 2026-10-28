import pytest
from pydantic import ValidationError

from app.models import Membership
from app.schemas.leads import LeadCreate, LeadPatch
from app.security.auth import UserCreate
from app.security.permissions import WRITE_ROLES, require_role


def test_normalizes_lead_email_without_merging_distinct_addresses():
    assert LeadCreate(name=" A buyer ", email=" Buyer@Example.COM ").email == "buyer@example.com"
    assert (
        LeadCreate(name="Buyer", email="buyer+sales@example.com").email == "buyer+sales@example.com"
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "email": "buyer@example.com"},
        {"name": "Buyer", "email": "invalid"},
        {"name": "Buyer", "email": "buyer@example.com", "score": 100},
        {"name": "Buyer", "email": "buyer@example.com", "website": "javascript:alert(1)"},
    ],
)
def test_invalid_lead_fields_are_rejected(payload):
    with pytest.raises(ValidationError):
        LeadCreate.model_validate(payload)


@pytest.mark.parametrize("field", ["name", "email", "status"])
def test_required_lead_fields_cannot_be_cleared(field):
    with pytest.raises(ValidationError):
        LeadPatch.model_validate({field: None})


def test_viewer_cannot_write():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        require_role(Membership(role="viewer"), WRITE_ROLES)
    assert error.value.status_code == 403


def test_registration_rejects_non_string_email_with_validation_error():
    with pytest.raises(ValidationError):
        UserCreate.model_validate(
            {"email": 123, "password": "Fictional-password-42", "display_name": "Test"}
        )


def test_lead_website_must_fit_database_column():
    with pytest.raises(ValidationError):
        LeadCreate(
            name="Buyer", email="buyer@example.com", website="https://example.com/" + "a" * 2035
        )
