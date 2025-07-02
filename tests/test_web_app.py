import importlib
import os
import sqlite3
import datetime
from fastapi.testclient import TestClient
from modules import login, auth_utils
from modules.roles import Role


def login_default(client: TestClient):
    resp = client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        allow_redirects=False,
    )
    assert resp.status_code == 303
    return client


def create_client(tmp_path, do_login=True):
    os.environ["DB_PATH"] = str(tmp_path / "app.db")
    module = importlib.import_module("web_app.main")
    importlib.reload(module)
    client = TestClient(module.app)
    if do_login:
        login_default(client)
    return client


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


def test_kroviniai_csv(tmp_path):
    client = create_client(tmp_path)
    form = {
        "cid": "0",
        "klientas": "ACME",
        "uzsakymo_numeris": "1",
        "pakrovimo_data": "2023-01-01",
        "iskrovimo_data": "2023-01-02",
        "kilometrai": "10",
        "frachtas": "20",
        "busena": "Nesuplanuotas",
        "imone": "A",
    }
    client.post("/kroviniai/save", data=form, allow_redirects=False)
    resp = client.get("/api/kroviniai.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "uzsakymo_numeris" in resp.text.splitlines()[0]


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


def test_vilkikai_csv(tmp_path):
    client = create_client(tmp_path)
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
    client.post("/vilkikai/save", data=form, allow_redirects=False)
    resp = client.get("/api/vilkikai.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "numeris" in resp.text.splitlines()[0]


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


def test_priekabos_csv(tmp_path):
    client = create_client(tmp_path)
    form = {
        "pid": "0",
        "priekabu_tipas": "Tipas",
        "numeris": "TR1",
        "marke": "X",
        "pagaminimo_metai": "2020",
        "tech_apziura": "2023-01-01",
        "draudimas": "2023-01-01",
        "imone": "A",
    }
    client.post("/priekabos/save", data=form, allow_redirects=False)
    resp = client.get("/api/priekabos.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "numeris" in resp.text.splitlines()[0]


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

    resp = client.get("/api/audit.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "table_name" in resp.text.splitlines()[0]


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


def test_vairuotojai_basic(tmp_path):
    client = create_client(tmp_path)
    resp = client.get("/api/vairuotojai")
    assert resp.status_code == 200
    assert resp.json() == {"data": []}
    form = {
        "did": "0",
        "vardas": "Jonas",
        "pavarde": "Jonaitis",
        "gimimo_metai": "1980-01-01",
        "tautybe": "LT",
        "kadencijos_pabaiga": "",
        "atostogu_pabaiga": "",
        "imone": "A",
    }
    resp = client.post("/vairuotojai/save", data=form, allow_redirects=False)
    assert resp.status_code == 303
    resp = client.get("/api/vairuotojai")
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["vardas"] == "Jonas"


def test_planavimas_basic(tmp_path):
    client = create_client(tmp_path)
    today = datetime.date.today().isoformat()
    truck_form = {
        "vid": "0",
        "numeris": "AAA111",
        "marke": "MAN",
        "pagaminimo_metai": "2020",
        "tech_apziura": "2023-01-01",
        "vadybininkas": "John",
        "vairuotojai": "",
        "priekaba": "TR1",
        "imone": "A",
    }
    client.post("/vilkikai/save", data=truck_form, allow_redirects=False)
    load_form = {
        "cid": "0",
        "klientas": "ACME",
        "uzsakymo_numeris": "1",
        "pakrovimo_data": today,
        "iskrovimo_data": today,
        "kilometrai": "10",
        "frachtas": "1",
        "busena": "Nesuplanuotas",
        "imone": "A",
        "vilkikas": "AAA111",
    }
    client.post("/kroviniai/save", data=load_form, allow_redirects=False)
    db_path = tmp_path / "app.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        "INSERT INTO vilkiku_darbo_laikai (vilkiko_numeris, data, iskrovimo_laikas, darbo_laikas, likes_laikas, sa) VALUES (?,?,?,?,?,?)",
        ("AAA111", today, "10:00", 8, 4, "SA"),
    )
    conn.commit()
    conn.close()
    resp = client.get("/api/planavimas")
    assert resp.status_code == 200
    data = resp.json()
    assert "columns" in data and "data" in data
    assert any(row[data["columns"][0]].startswith("AAA111") for row in data["data"])
    assert today in data["columns"]


def test_settings_defaults(tmp_path):
    client = create_client(tmp_path)
    form = {
        "imone": "A",
        "values": ["Van", "Box"],
    }
    resp = client.post("/settings/save", data=form, allow_redirects=False)
    assert resp.status_code == 303
    resp = client.get("/api/default-trailer-types?imone=A")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data == ["Van", "Box"]


def test_access_restrictions(tmp_path):
    client = create_client(tmp_path, do_login=False)
    db_path = tmp_path / "app.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    pw = auth_utils.hash_password("pass")
    c.execute(
        "INSERT INTO users (username, password_hash, imone, aktyvus) VALUES (?,?,?,1)",
        ("user@a.com", pw, "A"),
    )
    uid = c.lastrowid
    login.assign_role(conn, c, uid, Role.USER)
    conn.commit()
    conn.close()

    resp = client.post(
        "/login",
        data={"username": "user@a.com", "password": "pass"},
        allow_redirects=False,
    )
    assert resp.status_code == 303

    assert client.get("/settings").status_code == 403
    assert client.get("/trailer-specs").status_code == 403
    assert client.get("/trailer-types").status_code == 403


def test_login_and_register(tmp_path):
    client = create_client(tmp_path, do_login=False)
    reg_form = {
        "username": "new@a.com",
        "password": "pass",
        "vardas": "A",
        "pavarde": "B",
        "pareigybe": "Mgr",
        "imone": "A",
    }
    resp = client.post("/register", data=reg_form)
    assert resp.status_code == 200
    assert "Paraiška pateikta" in resp.text

    resp = client.post("/login", data={"username": "new@a.com", "password": "pass"})
    assert "Neteisingi" in resp.text

    db_path = tmp_path / "app.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("UPDATE users SET aktyvus=1 WHERE username=?", ("new@a.com",))
    conn.commit()
    conn.close()

    resp = client.post(
        "/login",
        data={"username": "new@a.com", "password": "pass"},
        allow_redirects=False,
    )
    assert resp.status_code == 303


def test_trailer_specs_basic(tmp_path):
    client = create_client(tmp_path)
    resp = client.get("/api/trailer-specs")
    assert resp.status_code == 200
    assert resp.json() == {"data": []}

    form = {
        "sid": "0",
        "tipas": "Mega",
        "ilgis": "13.6",
        "plotis": "2.5",
        "aukstis": "3",
        "keliamoji_galia": "24000",
        "talpa": "90",
    }
    resp = client.post("/trailer-specs/save", data=form, allow_redirects=False)
    assert resp.status_code == 303
    resp = client.get("/api/trailer-specs")
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["tipas"] == "Mega"


def test_user_admin_approve(tmp_path):
    client = create_client(tmp_path)
    db_path = tmp_path / "app.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (username, password_hash, imone, vardas, pavarde, pareigybe, aktyvus) VALUES (?,?,?,?,?,?,0)",
        ("u@a.com", "x", "A", "User", "Test", "Mgr"),
    )
    uid = c.lastrowid
    conn.commit()
    conn.close()

    resp = client.get("/api/registracijos")
    data = resp.json()["data"]
    assert len(data) == 1 and data[0]["username"] == "u@a.com"

    resp = client.get(f"/registracijos/{uid}/approve", allow_redirects=False)
    assert resp.status_code == 303

    resp = client.get("/api/registracijos")
    assert resp.json() == {"data": []}

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    row = c.execute("SELECT aktyvus FROM users WHERE id=?", (uid,)).fetchone()
    assert row[0] == 1
    row = c.execute(
        "SELECT COUNT(*) FROM darbuotojai WHERE el_pastas=?", ("u@a.com",)
    ).fetchone()
    assert row[0] == 1
    conn.close()

    resp = client.get("/api/aktyvus")
    data = resp.json()["data"]
    assert any(r["username"] == "u@a.com" for r in data)


def test_updates_basic(tmp_path):
    client = create_client(tmp_path)
    resp = client.get("/api/updates")
    assert resp.status_code == 200
    assert resp.json() == {"data": []}

    form = {
        "uid": "0",
        "vilkiko_numeris": "AAA111",
        "data": "2023-01-01",
        "darbo_laikas": "8",
        "likes_laikas": "4",
        "sa": "SA",
        "pakrovimo_statusas": "Pakrauta",
        "pakrovimo_laikas": "10:00",
        "pakrovimo_data": "2023-01-01",
        "iskrovimo_statusas": "",
        "iskrovimo_laikas": "",
        "iskrovimo_data": "",
        "komentaras": "t",
    }
    resp = client.post("/updates/save", data=form, allow_redirects=False)
    assert resp.status_code == 303

    resp = client.get("/api/updates")
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["vilkiko_numeris"] == "AAA111"
    assert data[0]["sa"] == "SA"

    resp = client.get("/api/updates.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "vilkiko_numeris" in resp.text.splitlines()[0]


def test_klientai_limits(tmp_path):
    client = create_client(tmp_path)
    form = {
        "cid": "0",
        "pavadinimas": "ACME",
        "vat_numeris": "LT123",
        "kontaktinis_asmuo": "Jonas",
        "kontaktinis_el_pastas": "j@a.com",
        "kontaktinis_tel": "123",
        "coface_limitas": "900",
        "imone": "A",
    }
    resp = client.post("/klientai/save", data=form, allow_redirects=False)
    assert resp.status_code == 303
    resp = client.get("/api/klientai")
    data = resp.json()["data"]
    assert len(data) == 1
    row = data[0]
    assert row["musu_limitas"] == 300
    assert row["likes_limitas"] == 300
