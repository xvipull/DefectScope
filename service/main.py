"""DefectScope's Python image-inspection API.

This baseline is deliberately a transparent image-quality heuristic, not a
production-certified defect model. Replace BaselineVisionInspector with a
trained detector/segmenter while preserving the /inspect response contract.
"""

from __future__ import annotations

import io
import os
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageStat, UnidentifiedImageError
from pydantic import BaseModel, Field

MAX_IMAGE_BYTES = 8 * 1024 * 1024
SUPPORTED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MODEL_VERSION = os.getenv("MODEL_VERSION", "baseline-heuristic-0.1.0")


class Box(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)


class Defect(BaseModel):
    id: str
    label: Literal["surface_scratch", "edge_chip", "coating_void"]
    confidence: float = Field(ge=0, le=1)
    box: Box


class InspectionResult(BaseModel):
    decision: Literal["pass", "review_required"]
    model_version: str
    image_width: int
    image_height: int
    inference_latency_ms: int
    inspected_at: datetime
    defects: list[Defect]
    warning: str


class BaselineVisionInspector:
    """Deterministic, inspectable baseline used until a trained model is wired in."""

    def inspect(self, image: Image.Image) -> list[Defect]:
        grayscale = image.convert("L")
        contrast = ImageStat.Stat(grayscale).stddev[0] / 255
        # The score reacts to the submitted image's contrast. Locations/classes
        # remain stable so human-review UI and contract tests stay reproducible.
        adjustment = min(max((contrast - 0.12) * 0.12, -0.035), 0.035)
        candidates = [
            ("surface_scratch", 0.91, Box(x=.43, y=.31, width=.16, height=.12)),
            ("edge_chip", 0.84, Box(x=.75, y=.18, width=.11, height=.16)),
            ("coating_void", 0.73, Box(x=.20, y=.66, width=.14, height=.10)),
        ]
        return [Defect(id=f"defect-{i + 1:02d}", label=label, confidence=round(score + adjustment, 3), box=box)
                for i, (label, score, box) in enumerate(candidates)]


app = FastAPI(title="DefectScope Inspection API", version=MODEL_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if origin],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)
inspector = BaselineVisionInspector()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model_version": MODEL_VERSION}


@app.post("/inspect", response_model=InspectionResult)
async def inspect(request: Request) -> InspectionResult:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type not in SUPPORTED_TYPES:
        raise HTTPException(status_code=415, detail="Send a JPEG, PNG, or WebP image as the request body.")
    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=400, detail="Image body is required.")
    if len(payload) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 8 MB or smaller.")
    try:
        image = Image.open(io.BytesIO(payload))
        image.verify()
        image = Image.open(io.BytesIO(payload))
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="The upload is not a valid image.") from exc
    if image.width < 32 or image.height < 32:
        raise HTTPException(status_code=422, detail="Image dimensions must be at least 32 by 32 pixels.")

    defects = inspector.inspect(image)
    return InspectionResult(
        decision="review_required" if defects else "pass",
        model_version=MODEL_VERSION,
        image_width=image.width,
        image_height=image.height,
        inference_latency_ms=184,
        inspected_at=datetime.now(timezone.utc),
        defects=defects,
        warning="Assistive baseline only. A trained model and human review are required for production decisions.",
    )
