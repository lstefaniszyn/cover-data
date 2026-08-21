"""The PaddleOCR adapter: the only module in this codebase that imports
`paddleocr` or knows its result field names (`ocr.engine.OcrEngine` is the
seam everything else depends on instead, per `tech-stack.md`'s develop-on
-Paddle/ship-on-ONNX plan).

Two construction quirks, both required on this machine (not optional) --
see the `paddleocr-cpu-windows-gotchas` note this was built from:

1. `device="cpu"` and `enable_mkldnn=False` are required. With MKL-DNN left
   at its default, `.predict()` crashes during text detection with a Paddle
   PIR-executor/oneDNN incompatibility on this build.
2. `lang`/`ocr_version` are silently ignored once any `*_model_dir` is set,
   and the pipeline falls back to resolving the *default* pipeline
   version's model names (PP-OCRv6 on 3.7.0) unless every `*_model_dir` is
   paired with its matching `*_model_name` -- required to actually get the
   PP-OCRv5 models `tech-stack.md` pins for Polish/Latin recognition
   quality.

`use_doc_unwarping=False` is deliberate, not a default left untouched -- see
`geometry.transform` for why: UVDoc has no invertible coordinate contract,
so it is not applied to the call whose fragment coordinates this codebase
trusts. `use_doc_orientation_classify=True` must be passed explicitly
alongside it: empirically, passing `use_doc_unwarping=False` without also
setting `use_doc_orientation_classify` disables the *entire* doc-preprocessor
sub-pipeline (confirmed by the orientation model never being constructed and
`doc_preprocessor_res` losing its `"angle"` key), not just unwarping.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from paddleocr import PaddleOCR
from PIL import Image

from cover_data.domain import OcrFragment, Point
from cover_data.geometry.transform import OrientationTransform
from cover_data.ocr import config
from cover_data.ocr.engine import DEFAULT_MIN_CONFIDENCE


class PaddleOcrEngine:
    """Implements `ocr.engine.OcrEngine`. Constructs the pipeline once, at
    `__init__`, since model loading (not inference) dominates cost."""

    def __init__(self) -> None:
        self._pipeline = PaddleOCR(
            text_detection_model_dir=str(config.TEXT_DETECTION_MODEL_DIR),
            text_detection_model_name="PP-OCRv5_server_det",
            text_recognition_model_dir=str(config.TEXT_RECOGNITION_MODEL_DIR),
            text_recognition_model_name="latin_PP-OCRv5_mobile_rec",
            doc_orientation_classify_model_dir=str(config.DOC_ORIENTATION_MODEL_DIR),
            doc_orientation_classify_model_name="PP-LCNet_x1_0_doc_ori",
            doc_unwarping_model_dir=str(config.DOC_UNWARPING_MODEL_DIR),
            doc_unwarping_model_name="UVDoc",
            textline_orientation_model_dir=str(config.TEXTLINE_ORIENTATION_MODEL_DIR),
            textline_orientation_model_name="PP-LCNet_x1_0_textline_ori",
            lang=config.LANG,
            device="cpu",
            enable_mkldnn=False,
            use_doc_orientation_classify=True,
            use_doc_unwarping=False,
        )

    def recognize(self, image_path: Path) -> tuple[OcrFragment, ...]:
        source_width, source_height = Image.open(image_path).size
        results = self._pipeline.predict(str(image_path))
        if not results:
            return ()
        result = cast(dict[str, Any], results[0])

        angle = int(result["doc_preprocessor_res"]["angle"])
        transform = OrientationTransform(
            angle=angle, source_width=source_width, source_height=source_height
        )

        fragments = []
        for text, score, poly in zip(
            result["rec_texts"], result["rec_scores"], result["rec_polys"], strict=True
        ):
            rotated_points = [Point(float(px), float(py)) for px, py in poly]
            if len(rotated_points) != 4:
                raise ValueError(
                    f"expected a 4-point polygon from PaddleOCR, got "
                    f"{len(rotated_points)} points for text {text!r}"
                )
            p0, p1, p2, p3 = (transform.inverse(p) for p in rotated_points)
            confidence = float(score)
            fragments.append(
                OcrFragment(
                    text=str(text),
                    polygon=(p0, p1, p2, p3),
                    confidence=confidence,
                    low_confidence=confidence < DEFAULT_MIN_CONFIDENCE,
                )
            )
        return tuple(fragments)
