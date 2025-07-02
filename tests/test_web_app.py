import importlib
import os
from fastapi.testclient import TestClient


def create_client(tmp_path):
    os.environ["DB_PATH"] = str(tmp_path / "app.db")
    module = importlib.import_module("web_app.main")
    importlib.reload(module)
    return TestClient(module.app)


def test_kroviniai_empty(tmp_path):
    client = create_client(tmp_path)
    resp = client.get("/api/kroviniai")
    assert resp.status_code == 200
    assert resp.json() == {"data": []}


def test_save_and_fetch(tmp_path):
    client = create_client(tmp_path)
    form = {
        "cid": "0",
        "klientas": "ACME",
        "uzsakymo_numeris": "123",
        "pakrovimo_data": "2023-01-01",
        "iskrovimo_data": "2023-01-02",
        "kilometrai": "10",
        "frachtas": "20",
        "busena": "Nesuplanuotas",
        "imone": "A",
    }
    resp = client.post("/kroviniai/save", data=form, allow_redirects=False)
    assert resp.status_code == 303
    resp = client.get("/api/kroviniai")
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["klientas"] == "ACME"


def test_vilkikai_basic(tmp_path):
    client = create_client(tmp_path)
    resp = client.get("/api/vilkikai")
    assert resp.status_code == 200
    assert resp.json() == {"data": []}
    form = {
        "vid": "0",
        "numeris": "AAA111",
        "marke": "MAN",
        "pagaminimo_metai": "2020",
        "tech_apziura": "2023-01-01",
        "vadybininkas": "John",
        "vairuotojai": "A B",
        "priekaba": "TR1",
        "imone": "A",
    }
    resp = client.post("/vilkikai/save", data=form, allow_redirects=False)
    assert resp.status_code == 303
    resp = client.get("/api/vilkikai")
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["numeris"] == "AAA111"


def test_vilkikai_form_shows_trailers(tmp_path):
    client = create_client(tmp_path)
    trailer_form = {
        "pid": "0",
        "priekabu_tipas": "Tipas",
        "numeris": "TR123",
        "marke": "X",
        "pagaminimo_metai": "2020",
        "tech_apziura": "2023-01-01",
        "draudimas": "2023-01-01",
        "imone": "A",
    }
    resp = client.post("/priekabos/save", data=trailer_form, allow_redirects=False)
    assert resp.status_code == 303

    resp = client.get("/vilkikai/add")
    assert resp.status_code == 200
    assert "<select" in resp.text
    assert '<option value="TR123"' in resp.text


def test_audit_log_records_actions(tmp_path):
    client = create_client(tmp_path)
    trailer_form = {
        "pid": "0",
        "priekabu_tipas": "Tipas",
        "numeris": "TR1",
        "marke": "X",
        "pagaminimo_metai": "2020",
        "tech_apziura": "2023-01-01",
        "draudimas": "2023-01-01",
        "imone": "A",
    }
    resp = client.post("/priekabos/save", data=trailer_form, allow_redirects=False)
    assert resp.status_code == 303
    resp = client.get("/api/audit")
    data = resp.json()["data"]
    assert len(data) == 1
    row = data[0]
    assert row["table_name"] == "priekabos"
    assert row["action"] == "insert"
    assert "details" in row


def test_audit_multiple_modules(tmp_path):
    client = create_client(tmp_path)

    load_form = {
        "cid": "0",
        "klientas": "ACME",
        "uzsakymo_numeris": "123",
        "pakrovimo_data": "2023-01-01",
        "iskrovimo_data": "2023-01-02",
        "kilometrai": "10",
        "frachtas": "20",
        "busena": "Nesuplanuotas",
        "imone": "A",
    }
    resp = client.post("/kroviniai/save", data=load_form, allow_redirects=False)
    assert resp.status_code == 303

    truck_form = {
        "vid": "0",
        "numeris": "AAA111",
        "marke": "MAN",
        "pagaminimo_metai": "2020",
        "tech_apziura": "2023-01-01",
        "vadybininkas": "John",
        "vairuotojai": "A B",
        "priekaba": "TR1",
        "imone": "A",
    }
    resp = client.post("/vilkikai/save", data=truck_form, allow_redirects=False)
    assert resp.status_code == 303

    resp = client.get("/api/audit")
    data = resp.json()["data"]
    tables = {row["table_name"] for row in data}
    assert {"kroviniai", "vilkikai"}.issubset(tables)
