# DefectScope

Human-in-the-loop visual inspection console with a TypeScript review UI and a Python/FastAPI inspection service.

## Run the Python service

```bash
python3 -m uvicorn service.main:app --reload --port 8000
```

Send a PNG, JPEG, or WebP body to `POST /inspect`. The service validates type, size, image decoding, and dimensions before returning normalized defect boxes, confidence, decision, latency, and model version.

The included model is a deterministic, transparent baseline so the API and review UI can be developed without claiming real-world defect detection. Replace `BaselineVisionInspector` with a trained CV model before production use, record dataset provenance and evaluation metrics, and retain human review.

## Test

```bash
python3 -m pytest tests
```
