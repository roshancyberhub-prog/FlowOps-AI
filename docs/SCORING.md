# Reproducible lead scoring

Scoring is deterministic and configurable per organization. A profile is an immutable version stored in PostgreSQL. Owners/admins create a new version in **Scoring profiles**. Members can calculate a lead's score; viewers can inspect it. New workspaces receive the example baseline, and migration 0005 seeds existing workspaces.

The baseline adds 25 for a target job-title phrase, 20 for an exact target industry, 15 for an exact company-size label, 10 for an email outside the personal-domain list and 10 for a website. Missing any configured required fields applies one -10 penalty. Scores are clamped to 0–100; the baseline maximum is 80. These weights are examples, not validated benchmarks or predictions. Email-domain classification is a heuristic and does not verify ownership or deliverability.

Matching ignores case and surrounding whitespace. Titles use phrase/word boundaries; industries and size labels match exactly. Weights are integers, each positive signal 0–100 and the missing-field penalty -100–0. Target lists contain at most 20 entries each; the personal-domain list at most 100. Each entry is 1–100 characters.

A score stores six rule reasons, the profile UUID/version and timestamp. Editing a scoring input clears the current result. Historical workflow steps preserve the earlier snapshot. Live workflow scoring rejects a lead whose scoring inputs changed after the run started. Test runs record computed scores in execution context without changing the stored lead.

Publishing a workflow resolves `scoring_profile: default` to the current immutable profile UUID. Later profile changes cannot alter that published definition. Pre-scoring published definitions which still contain `default` retain baseline version 1 for compatibility.

API routes under `/api/v1`:

- `GET /scoring-profiles/current`: current organization profile.
- `GET /scoring-profiles?page=1`: version history, 25 per page.
- `POST /scoring-profiles`: new immutable profile, owner/admin only.
- `POST /leads/{id}/score`: calculate with optional `profile_id`; otherwise current profile.

The workflow score node uses the pinned profile. Cross-organization profile and lead references are rejected. Database triggers prohibit updating/deleting profile versions. CSV imports and AI-assisted qualification are separate work in Milestone 4 and are not implemented by this scoring slice.
