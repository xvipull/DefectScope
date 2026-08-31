import io

from fastapi.testclient import TestClient
from PIL import Image

from service.main import app


client = TestClient(app)


def image_bytes() -> bytes:
    image = Image.new("RGB", (120, 90), "#86918b")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_inspect_returns_reviewable_defects():
    response = client.post("/inspect", content=image_bytes(), headers={"content-type": "image/png"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "review_required"
    assert len(payload["defects"]) == 3
    assert payload["defects"][0]["box"]["width"] > 0


def test_inspect_rejects_non_images():
    response = client.post("/inspect", content=b"not an image", headers={"content-type": "text/plain"})
    assert response.status_code == 415
