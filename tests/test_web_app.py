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


def test_klientai_basic(tmp_path):
    client = create_client(tmp_path)
    resp = client.get("/api/klientai")
    assert resp.status_code == 200
    assert resp.json() == {"data": []}
    form = {
        "id": "0",
        "pavadinimas": "Acme",
        "kontaktai": "John",
        "salis": "LT",
        "miestas": "Vilnius",
        "regionas": "",
        "vat_numeris": "123",
        "imone": "A",
    }
    resp = client.post("/klientai/save", data=form, allow_redirects=False)
    assert resp.status_code == 303
    resp = client.get("/api/klientai")
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["pavadinimas"] == "Acme"


def test_priekabos_basic(tmp_path):
    client = create_client(tmp_path)
    resp = client.get("/api/priekabos")
    assert resp.status_code == 200
    assert resp.json() == {"data": []}
    form = {
        "id": "0",
        "priekabu_tipas": "Tent",
        "numeris": "TR2",
        "marke": "Krone",
        "pagaminimo_metai": "2019",
        "tech_apziura": "2023-01-01",
        "priskirtas_vilkikas": "",
        "draudimas": "2023-01-01",
        "imone": "A",
    }
    resp = client.post("/priekabos/save", data=form, allow_redirects=False)
    assert resp.status_code == 303
    resp = client.get("/api/priekabos")
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["numeris"] == "TR2"
