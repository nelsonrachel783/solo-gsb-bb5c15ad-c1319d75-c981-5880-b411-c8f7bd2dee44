"""API 端到端测试（需要安装 fastapi / httpx，见 requirements-dev.txt）。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

URL = "/api/v1/dimension-chain/check"


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_feasible_returns_coordinates_with_datum_zero():
    payload = {
        "datum": "A",
        "points": ["A", "B", "C"],
        "constraints": [
            {"id": "c1", "start": "A", "end": "B", "lower": 10, "upper": 20},
            {"id": "c2", "start": "B", "end": "C", "lower": 5, "upper": 15},
        ],
    }
    resp = client.post(URL, json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["feasible"] is True
    assert body["cycle"] is None
    coords = body["coordinates"]
    assert coords["A"] == 0
    for c in payload["constraints"]:
        assert c["lower"] <= coords[c["end"]] - coords[c["start"]] <= c["upper"]


def test_infeasible_returns_conflict_cycle_ids():
    payload = {
        "datum": "A",
        "points": ["A", "B", "C"],
        "constraints": [
            {"id": "c1", "start": "A", "end": "B", "lower": 5, "upper": 10},
            {"id": "c2", "start": "B", "end": "C", "lower": 5, "upper": 10},
            {"id": "c3", "start": "C", "end": "A", "lower": 5, "upper": 10},
        ],
    }
    resp = client.post(URL, json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["feasible"] is False
    assert body["coordinates"] is None
    assert sorted(body["cycle"]) == ["c1", "c2", "c3"]


def test_unknown_point_rejected():
    payload = {
        "datum": "A",
        "points": ["A", "B"],
        "constraints": [
            {"id": "c1", "start": "A", "end": "D", "lower": 0, "upper": 10}
        ],
    }
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422
    assert "未知点" in resp.text


def test_reversed_interval_rejected():
    payload = {
        "datum": "A",
        "points": ["A", "B"],
        "constraints": [
            {"id": "c1", "start": "A", "end": "B", "lower": 10, "upper": 5}
        ],
    }
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422
    assert "区间反向" in resp.text


def test_unconnected_point_rejected():
    payload = {
        "datum": "A",
        "points": ["A", "B", "C"],
        "constraints": [
            {"id": "c1", "start": "A", "end": "B", "lower": 0, "upper": 10}
        ],
    }
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422
    assert "未通过任何约束与基准点" in resp.text


def test_datum_not_in_points_rejected():
    payload = {
        "datum": "Z",
        "points": ["A", "B"],
        "constraints": [
            {"id": "c1", "start": "A", "end": "B", "lower": 0, "upper": 10}
        ],
    }
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422
    assert "基准点" in resp.text


def test_non_integer_bound_rejected():
    payload = {
        "datum": "A",
        "points": ["A", "B"],
        "constraints": [
            {"id": "c1", "start": "A", "end": "B", "lower": 0.5, "upper": 10}
        ],
    }
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422
