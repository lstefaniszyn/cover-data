"""Local, offline OCR model configuration.

Model weights are pre-placed under `models/` (git-ignored, provisioning
documented in CLAUDE.md) and pinned here by explicit directory, so the
engine never attempts network I/O at inference — required by the
PII-stays-on-device invariant and by this network's TLS-inspecting proxy,
which breaks first-run downloads.

Directory names match the official PaddleOCR PP-OCRv5 inference-model
archives, unpacked as-is.
"""

from __future__ import annotations

from pathlib import Path

LANG = "pl"

MODEL_ROOT = Path(__file__).resolve().parents[3] / "models"

TEXT_DETECTION_MODEL_DIR = MODEL_ROOT / "PP-OCRv5_server_det_infer"
TEXT_RECOGNITION_MODEL_DIR = MODEL_ROOT / "latin_PP-OCRv5_mobile_rec_infer"
DOC_ORIENTATION_MODEL_DIR = MODEL_ROOT / "PP-LCNet_x1_0_doc_ori_infer"
DOC_UNWARPING_MODEL_DIR = MODEL_ROOT / "UVDoc_infer"
TEXTLINE_ORIENTATION_MODEL_DIR = MODEL_ROOT / "PP-LCNet_x1_0_textline_ori_infer"
