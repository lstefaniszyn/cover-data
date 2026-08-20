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
actually matters for scaffolding. Its FastAPI and uvicorn dependencies were surplus
here and have since been dropped in favour of Typer, since match confirmation and
row preview happen in the terminal plus an OS image viewer rather than a web UI.
Deployment is `self-host` because the tool runs on one caseworker's device and the
debtor PII it processes must not leave it; that same constraint rules out hosted
OCR APIs, so OCR stays local. CI runs lint and tests with manual promotion — there
is no server to deploy to.

## OCR engine and Python version

Decided 2026-08-20 while researching roadmap slice S-01 (`scan-row-reconstruction`).
Full evidence, the alternatives weighed, and the resolution runs behind each claim
are in `context/changes/scan-row-reconstruction/research.md`.

**OCR is PaddleOCR, running locally.** It is adopted for text detection and
recognition quality plus its document-preprocessing models — in particular UVDoc
text-image unwarping (~30 MB, ~870 ms CPU), which targets the wavy-scan distortion
that is this project's central technical risk, and document orientation
classification. Polish is a first-class supported language (`lang="pl"`, served by
`latin_PP-OCRv5_mobile_rec`), which closes what was otherwise the highest-severity
unknown in the OCR choice.

**Python moves from 3.14 to 3.13.** PaddleOCR's official models ship only in
PaddlePaddle static-graph format, and the `paddle2onnx` conversion path needs the
`paddlepaddle` framework, whose wheels stop at `cp313`. The `paddleocr` package
itself resolves fine on 3.14 — it is the engine underneath that does not. The
downgrade is close to free: the codebase uses no 3.14-only feature. This decision
supersedes the `requires-python = ">=3.14"` pin recorded at bootstrap; the pin,
`.python-version`, the CI matrix, and `CLAUDE.md` are updated as part of S-01.

**Packaging: develop on Paddle, ship on ONNX.** `paddlepaddle` is a heavy runtime
dependency and is materially harder to freeze with PyInstaller than ONNX Runtime,
which is the one genuine regression this choice carries — and it lands on the
`release.yml` `.exe` build, not on development. Because the 3.13 environment can
run `paddle2onnx`, the mitigation is a build-time export: validate against the full
first-party pipeline, then convert only the models actually used and ship a lean
`onnxruntime` runtime. The OCR engine therefore sits behind a small `Protocol`
yielding a typed OCR-fragment model, so Paddle, ONNX, and Tesseract stay swappable
and this is not a one-way door.

Two constraints that fall out of this and bind implementation:

- **PP-Structure is not the source of row geometry.** Its table models self-report
  59.5–69.7% on their own hard-table set, the upstream docs state that SLANeXt cell
  predictions can be invalid, and every pretrained table model in this family is
  trained on born-digital renders rather than distorted scans. Row reconstruction
  stays a deterministic geometric pipeline; PP-Structure output is usable only as a
  disagreement signal feeding the FR-006 confirmation gate.
- **Model weights are pre-placed, never fetched at inference time.** Model
  directories are pinned explicitly. Weights are not PII, so downloading them on a
  developer machine is fine, but the shipped tool must not attempt network I/O —
  both for the PII-stays-on-device invariant and because the TLS-inspecting proxy
  on this network breaks first-run downloads.

Generative VLM-based OCR (dots.ocr, DeepSeek-OCR, olmOCR, PaddleOCR-VL and similar)
is explicitly rejected despite topping document-understanding leaderboards: those
benchmarks measure document-to-Markdown transcription, whereas this project needs a
pixel region to destroy. Such models hallucinate, expose no calibrated per-fragment
confidence (which FR-002 requires), and are not viable on a caseworker's CPU-only
machine. A VLM remains defensible only as an optional second-opinion transcription
used to cross-check the deterministic pipeline and raise ambiguity for confirmation
— never as the source of redaction geometry.
