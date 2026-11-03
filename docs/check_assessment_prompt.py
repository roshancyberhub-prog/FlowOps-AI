import json
from pathlib import Path

from app.ai.schemas import DraftContent
from pydantic import ValidationError

text = Path(__file__).with_name("ASSESSMENT.md").read_text()
baseline = text.split("```text\n", 1)[1].split("\n```", 1)[0]
revised = text.split("```json\n", 1)[1].split("\n```", 1)[0]

def expect_rejection(payload, code):
    try:
        DraftContent.model_validate_json(payload)
    except ValidationError as exc:
        assert exc.errors()[0]["type"] == code, exc
    else:
        raise AssertionError(f"Expected {code}")

expect_rejection(baseline, "json_invalid")
draft = DraftContent.model_validate_json(revised)
assert len(draft.body.split()) <= 90
assert draft.body.count("?") == 1
expect_rejection(json.dumps({**draft.model_dump(), "send": True}), "extra_forbidden")
print("PASS: baseline rejected, revision accepted, send field rejected")
