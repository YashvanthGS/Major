import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setenv("DAIRY_DB", path)
    from app.main import app
    with TestClient(app) as c:
        yield c
    os.remove(path)


def _farmer(c, name="Ramesh"):
    return c.post("/api/farmers", json={"name": name, "village": "Hunsur"}).json()["id"]


def test_calculate_endpoint(client):
    r = client.post("/api/calculate", json={"litres": 10, "fat": 4.0, "snf": 8.5})
    assert r.status_code == 200 and r.json()["total"] == 360.5


def test_invalid_reading_returns_422(client):
    assert client.post("/api/calculate", json={"litres": 10, "fat": 40, "snf": 8.5}).status_code == 422


def test_entry_flow_and_duplicate_guard(client):
    fid = _farmer(client)
    body = {"farmer_id": fid, "entry_date": "2026-10-01", "session": "morning",
            "litres": 10, "fat": 4.0, "snf": 8.5}
    assert client.post("/api/entries", json=body).status_code == 201
    assert client.post("/api/entries", json=body).status_code == 409
    body["session"] = "evening"
    assert client.post("/api/entries", json=body).status_code == 201


def test_unknown_farmer(client):
    r = client.post("/api/entries", json={"farmer_id": 999, "entry_date": "2026-10-01",
                                          "session": "morning", "litres": 5, "fat": 4, "snf": 8.5})
    assert r.status_code == 404


def test_old_entries_keep_old_rates(client):
    fid = _farmer(client)
    body = {"farmer_id": fid, "entry_date": "2026-10-01", "session": "morning",
            "litres": 10, "fat": 4.0, "snf": 8.5}
    client.post("/api/entries", json=body)
    rc = client.get("/api/rate-card").json()
    rc["fat_rate"] = 900
    client.put("/api/rate-card", json=rc)
    rows = client.get("/api/entries").json()
    assert rows[0]["total"] == 360.5  # unchanged
    body["entry_date"] = "2026-10-02"
    assert client.post("/api/entries", json=body).json()["total"] > 360.5  # new rate


def test_monthly_summary_and_csv(client):
    fid = _farmer(client)
    for day, fat in [("2026-10-01", 4.0), ("2026-10-02", 5.0)]:
        client.post("/api/entries", json={"farmer_id": fid, "entry_date": day, "session": "morning",
                                          "litres": 10, "fat": fat, "snf": 8.5})
    s = client.get(f"/api/summary?farmer_id={fid}&month=2026-10").json()
    assert s["entries"] == 2 and s["total_litres"] == 20 and s["avg_fat"] == 4.5
    csv_text = client.get(f"/api/export.csv?farmer_id={fid}&month=2026-10").text
    assert csv_text.count("\n") == 3  # header + 2 rows


def test_homepage_served(client):
    assert client.get("/").status_code == 200
