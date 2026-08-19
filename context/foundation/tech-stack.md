---
starter_id: fastapi
package_manager: uv
project_name: cover-data
hints:
  language_family: python
  team_size: solo
  deployment_target: self-host
  ci_provider: github-actions
  ci_default_flow: manual-promotion
  bootstrapper_confidence: first-class
  path_taken: custom
  quality_override: false
  self_check_answers:
    typed: true
    from_official_starter: true
    conventions: true
    docs_current: true
    can_judge_agent: true
  has_auth: false
  has_payments: false
  has_realtime: false
  has_ai: false
  has_background_jobs: false
---

## Why this stack

A solo developer shipping a 3-week after-hours redaction CLI whose hard parts are
OCR with per-fragment confidence, table-row reconstruction on distorted scans, and
pixel-permanent redaction into a PDF. Python wins on ecosystem for all three; the
registry carries no Python CLI card, so the `fastapi` card is used as the Python
vehicle — it is the only Python entry clearing all four agent-friendly gates
(`django` fails on explicit types) and it prescribes `uv`, which is the part that
actually matters for scaffolding. Its FastAPI and uvicorn dependencies are surplus
here and should be dropped for a CLI framework, since match confirmation and row
preview happen in the terminal plus an OS image viewer rather than a web UI.
Deployment is `self-host` because the tool runs on one caseworker's device and the
debtor PII it processes must not leave it; that same constraint rules out hosted
OCR APIs, so OCR stays local. CI runs lint and tests with manual promotion — there
is no server to deploy to.
