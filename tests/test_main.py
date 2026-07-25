from fastapi.testclient import TestClient

from app.llm.client import AIError
from app.main import app
from app.scraper.fetch import FetchError

client = TestClient(app)


def test_index_serves_the_web_ui():
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_audit_returns_the_assembled_output_on_success(monkeypatch, make_output):
    output = make_output()

    async def fake_audit_website(url):
        assert url == "https://example.com/page"
        return output

    monkeypatch.setattr("app.main.audit_website", fake_audit_website)

    response = client.post("/audit", json={"url": "https://example.com/page"})

    assert response.status_code == 200
    body = response.json()
    assert body["factual_metrics"]["total_word_count"] == output.factual_metrics.total_word_count
    assert len(body["recommendations"]["recommendation"]) == 3


def test_audit_maps_fetch_error_to_422(monkeypatch):
    async def fake_audit_website(url):
        raise FetchError(f"{url} returned status 404")

    monkeypatch.setattr("app.main.audit_website", fake_audit_website)

    response = client.post("/audit", json={"url": "https://example.com/missing"})

    assert response.status_code == 422
    assert "returned status 404" in response.json()["detail"]


def test_audit_maps_ai_error_to_502(monkeypatch):
    async def fake_audit_website(url):
        raise AIError("Gemini call failed after 3 attempt(s): boom")

    monkeypatch.setattr("app.main.audit_website", fake_audit_website)

    response = client.post("/audit", json={"url": "https://example.com/page"})

    assert response.status_code == 502
    assert "AI provider error" in response.json()["detail"]
