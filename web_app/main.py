from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import sqlite3
from typing import Generator
from db import init_db
from modules.audit import log_action

app = FastAPI()

app.mount("/static", StaticFiles(directory="web_app/static"), name="static")
templates = Jinja2Templates(directory="web_app/templates")


EXPECTED_KROVINIAI_COLUMNS = {
    "klientas": "TEXT",
    "uzsakymo_numeris": "TEXT",
    "pakrovimo_data": "TEXT",
    "iskrovimo_data": "TEXT",
    "kilometrai": "INTEGER",
    "frachtas": "REAL",
    "busena": "TEXT",
    "imone": "TEXT",
}

EXPECTED_VILKIKAI_COLUMNS = {
    "numeris": "TEXT",
    "marke": "TEXT",
    "pagaminimo_metai": "INTEGER",
    "tech_apziura": "TEXT",
    "vadybininkas": "TEXT",
    "vairuotojai": "TEXT",
    "priekaba": "TEXT",
    "imone": "TEXT",
}

EXPECTED_PRIEKABOS_COLUMNS = {
    "priekabu_tipas": "TEXT",
    "numeris": "TEXT",
    "marke": "TEXT",
    "pagaminimo_metai": "TEXT",
    "tech_apziura": "TEXT",
    "draudimas": "TEXT",
    "imone": "TEXT",
}

EXPECTED_DARBUOTOJAI_COLUMNS = {
    "vardas": "TEXT",
    "pavarde": "TEXT",
    "pareigybe": "TEXT",
    "el_pastas": "TEXT",
    "telefonas": "TEXT",
    "grupe": "TEXT",
    "imone": "TEXT",
    "aktyvus": "INTEGER",
}

EXPECTED_GRUPES_COLUMNS = {
    "numeris": "TEXT",
    "pavadinimas": "TEXT",
    "aprasymas": "TEXT",
    "imone": "TEXT",
}

EXPECTED_KLIENTAI_COLUMNS = {
    "pavadinimas": "TEXT",
    "vat_numeris": "TEXT",
    "kontaktinis_asmuo": "TEXT",
    "kontaktinis_el_pastas": "TEXT",
    "kontaktinis_tel": "TEXT",
    "salis": "TEXT",
    "regionas": "TEXT",
    "miestas": "TEXT",
    "adresas": "TEXT",
    "saskaitos_asmuo": "TEXT",
    "saskaitos_el_pastas": "TEXT",
    "saskaitos_tel": "TEXT",
    "coface_limitas": "REAL",
    "musu_limitas": "REAL",
    "likes_limitas": "REAL",
    "imone": "TEXT",
}


def ensure_columns(conn: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
    """Ensure required columns exist for tables used by the web app."""
    tables = {
        "kroviniai": EXPECTED_KROVINIAI_COLUMNS,
        "vilkikai": EXPECTED_VILKIKAI_COLUMNS,
        "priekabos": EXPECTED_PRIEKABOS_COLUMNS,
        "darbuotojai": EXPECTED_DARBUOTOJAI_COLUMNS,
        "grupes": EXPECTED_GRUPES_COLUMNS,
        "klientai": EXPECTED_KLIENTAI_COLUMNS,
    }
    for table, cols in tables.items():
        cursor.execute(f"PRAGMA table_info({table})")
        existing = {r[1] for r in cursor.fetchall()}
        for col, typ in cols.items():
            if col not in existing:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
    conn.commit()


def get_db() -> Generator[tuple[sqlite3.Connection, sqlite3.Cursor], None, None]:
    conn, cursor = init_db()
    ensure_columns(conn, cursor)
    try:
        yield conn, cursor
    finally:
        conn.close()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/kroviniai", response_class=HTMLResponse)
def kroviniai_list(request: Request):
    return templates.TemplateResponse("kroviniai_list.html", {"request": request})


@app.get("/kroviniai/add", response_class=HTMLResponse)
def kroviniai_add_form(request: Request):
    return templates.TemplateResponse(
        "kroviniai_form.html", {"request": request, "data": {}}
    )


@app.get("/kroviniai/{cid}/edit", response_class=HTMLResponse)
def kroviniai_edit_form(
    cid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM kroviniai WHERE id=?", (cid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(kroviniai)")]
    data = dict(zip(columns, row))
    return templates.TemplateResponse(
        "kroviniai_form.html", {"request": request, "data": data}
    )


@app.post("/kroviniai/save")
def kroviniai_save(
    request: Request,
    cid: int = Form(0),
    klientas: str = Form(...),
    uzsakymo_numeris: str = Form(...),
    pakrovimo_data: str = Form(...),
    iskrovimo_data: str = Form(...),
    kilometrai: int = Form(0),
    frachtas: float = Form(0.0),
    busena: str = Form("Nesuplanuotas"),
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if cid:
        cursor.execute(
            "UPDATE kroviniai SET klientas=?, uzsakymo_numeris=?, pakrovimo_data=?, iskrovimo_data=?, kilometrai=?, frachtas=?, busena=?, imone=? WHERE id=?",
            (
                klientas,
                uzsakymo_numeris,
                pakrovimo_data,
                iskrovimo_data,
                kilometrai,
                frachtas,
                busena,
                imone,
                cid,
            ),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO kroviniai (klientas, uzsakymo_numeris, pakrovimo_data, iskrovimo_data, kilometrai, frachtas, busena, imone) VALUES (?,?,?,?,?,?,?,?)",
            (
                klientas,
                uzsakymo_numeris,
                pakrovimo_data,
                iskrovimo_data,
                kilometrai,
                frachtas,
                busena,
                imone,
            ),
        )
        cid = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, None, action, "kroviniai", cid)
    return RedirectResponse(f"/kroviniai", status_code=303)


@app.get("/api/kroviniai")
def kroviniai_api(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM kroviniai")
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(kroviniai)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@app.get("/vilkikai", response_class=HTMLResponse)
def vilkikai_list(request: Request):
    return templates.TemplateResponse("vilkikai_list.html", {"request": request})


@app.get("/vilkikai/add", response_class=HTMLResponse)
def vilkikai_add_form(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    trailers = [r[0] for r in cursor.execute("SELECT numeris FROM priekabos").fetchall()]
    return templates.TemplateResponse(
        "vilkikai_form.html", {"request": request, "data": {}, "trailers": trailers}
    )


@app.get("/vilkikai/{vid}/edit", response_class=HTMLResponse)
def vilkikai_edit_form(
    vid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM vilkikai WHERE id=?", (vid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(vilkikai)")]
    data = dict(zip(columns, row))
    trailers = [r[0] for r in cursor.execute("SELECT numeris FROM priekabos").fetchall()]
    return templates.TemplateResponse(
        "vilkikai_form.html", {"request": request, "data": data, "trailers": trailers}
    )


@app.post("/vilkikai/save")
def vilkikai_save(
    request: Request,
    vid: int = Form(0),
    numeris: str = Form(...),
    marke: str = Form(""),
    pagaminimo_metai: int = Form(0),
    tech_apziura: str = Form(""),
    vadybininkas: str = Form(""),
    vairuotojai: str = Form(""),
    priekaba: str = Form(""),
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if vid:
        cursor.execute(
            "UPDATE vilkikai SET numeris=?, marke=?, pagaminimo_metai=?, tech_apziura=?, vadybininkas=?, vairuotojai=?, priekaba=?, imone=? WHERE id=?",
            (
                numeris,
                marke,
                pagaminimo_metai,
                tech_apziura,
                vadybininkas,
                vairuotojai,
                priekaba,
                imone,
                vid,
            ),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO vilkikai (numeris, marke, pagaminimo_metai, tech_apziura, vadybininkas, vairuotojai, priekaba, imone) VALUES (?,?,?,?,?,?,?,?)",
            (
                numeris,
                marke,
                pagaminimo_metai,
                tech_apziura,
                vadybininkas,
                vairuotojai,
                priekaba,
                imone,
            ),
        )
        vid = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, None, action, "vilkikai", vid)
    return RedirectResponse(f"/vilkikai", status_code=303)


@app.get("/api/vilkikai")
def vilkikai_api(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM vilkikai")
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(vilkikai)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


# ---- Priekabos ----

@app.get("/priekabos", response_class=HTMLResponse)
def priekabos_list(request: Request):
    return templates.TemplateResponse("priekabos_list.html", {"request": request})


@app.get("/priekabos/add", response_class=HTMLResponse)
def priekabos_add_form(request: Request):
    return templates.TemplateResponse("priekabos_form.html", {"request": request, "data": {}})


@app.get("/priekabos/{pid}/edit", response_class=HTMLResponse)
def priekabos_edit_form(pid: int, request: Request, db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM priekabos WHERE id=?", (pid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(priekabos)")]
    data = dict(zip(columns, row))
    return templates.TemplateResponse("priekabos_form.html", {"request": request, "data": data})


@app.post("/priekabos/save")
def priekabos_save(
    request: Request,
    pid: int = Form(0),
    priekabu_tipas: str = Form(""),
    numeris: str = Form(...),
    marke: str = Form(""),
    pagaminimo_metai: str = Form(""),
    tech_apziura: str = Form(""),
    draudimas: str = Form(""),
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if pid:
        cursor.execute(
            "UPDATE priekabos SET priekabu_tipas=?, numeris=?, marke=?, pagaminimo_metai=?, tech_apziura=?, draudimas=?, imone=? WHERE id=?",
            (priekabu_tipas, numeris, marke, pagaminimo_metai, tech_apziura, draudimas, imone, pid),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO priekabos (priekabu_tipas, numeris, marke, pagaminimo_metai, tech_apziura, draudimas, imone) VALUES (?,?,?,?,?,?,?)",
            (priekabu_tipas, numeris, marke, pagaminimo_metai, tech_apziura, draudimas, imone),
        )
        pid = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, None, action, "priekabos", pid)
    return RedirectResponse("/priekabos", status_code=303)


@app.get("/api/priekabos")
def priekabos_api(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM priekabos")
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(priekabos)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


# ---- Darbuotojai ----

@app.get("/darbuotojai", response_class=HTMLResponse)
def darbuotojai_list(request: Request):
    return templates.TemplateResponse("darbuotojai_list.html", {"request": request})


@app.get("/darbuotojai/add", response_class=HTMLResponse)
def darbuotojai_add_form(request: Request):
    return templates.TemplateResponse("darbuotojai_form.html", {"request": request, "data": {}})


@app.get("/darbuotojai/{did}/edit", response_class=HTMLResponse)
def darbuotojai_edit_form(did: int, request: Request, db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM darbuotojai WHERE id=?", (did,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(darbuotojai)")]
    data = dict(zip(columns, row))
    return templates.TemplateResponse("darbuotojai_form.html", {"request": request, "data": data})


@app.post("/darbuotojai/save")
def darbuotojai_save(
    request: Request,
    did: int = Form(0),
    vardas: str = Form(...),
    pavarde: str = Form(""),
    pareigybe: str = Form(""),
    el_pastas: str = Form(""),
    telefonas: str = Form(""),
    grupe: str = Form(""),
    imone: str = Form(""),
    aktyvus: str = Form(None),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    akt = 1 if aktyvus else 0
    if did:
        cursor.execute(
            "UPDATE darbuotojai SET vardas=?, pavarde=?, pareigybe=?, el_pastas=?, telefonas=?, grupe=?, imone=?, aktyvus=? WHERE id=?",
            (vardas, pavarde, pareigybe, el_pastas, telefonas, grupe, imone, akt, did),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO darbuotojai (vardas, pavarde, pareigybe, el_pastas, telefonas, grupe, imone, aktyvus) VALUES (?,?,?,?,?,?,?,?)",
            (vardas, pavarde, pareigybe, el_pastas, telefonas, grupe, imone, akt),
        )
        did = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, None, action, "darbuotojai", did)
    return RedirectResponse("/darbuotojai", status_code=303)


@app.get("/api/darbuotojai")
def darbuotojai_api(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM darbuotojai")
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(darbuotojai)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}

# ---- Grupes ----

@app.get("/grupes", response_class=HTMLResponse)
def grupes_list(request: Request):
    return templates.TemplateResponse("grupes_list.html", {"request": request})


@app.get("/grupes/add", response_class=HTMLResponse)
def grupes_add_form(request: Request):
    return templates.TemplateResponse("grupes_form.html", {"request": request, "data": {}})


@app.get("/grupes/{gid}/edit", response_class=HTMLResponse)
def grupes_edit_form(
    gid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM grupes WHERE id=?", (gid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(grupes)")]
    data = dict(zip(columns, row))
    return templates.TemplateResponse("grupes_form.html", {"request": request, "data": data})


@app.post("/grupes/save")
def grupes_save(
    request: Request,
    gid: int = Form(0),
    numeris: str = Form(...),
    pavadinimas: str = Form(""),
    aprasymas: str = Form(""),
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if gid:
        cursor.execute(
            "UPDATE grupes SET numeris=?, pavadinimas=?, aprasymas=?, imone=? WHERE id=?",
            (numeris, pavadinimas, aprasymas, imone, gid),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO grupes (numeris, pavadinimas, aprasymas, imone) VALUES (?,?,?,?)",
            (numeris, pavadinimas, aprasymas, imone),
        )
        gid = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, None, action, "grupes", gid)
    return RedirectResponse("/grupes", status_code=303)


@app.get("/api/grupes")
def grupes_api(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM grupes")
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(grupes)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


# ---- Klientai ----

@app.get("/klientai", response_class=HTMLResponse)
def klientai_list(request: Request):
    return templates.TemplateResponse("klientai_list.html", {"request": request})


@app.get("/klientai/add", response_class=HTMLResponse)
def klientai_add_form(request: Request):
    return templates.TemplateResponse("klientai_form.html", {"request": request, "data": {}})


@app.get("/klientai/{cid}/edit", response_class=HTMLResponse)
def klientai_edit_form(
    cid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM klientai WHERE id=?", (cid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(klientai)")]
    data = dict(zip(columns, row))
    return templates.TemplateResponse("klientai_form.html", {"request": request, "data": data})


@app.post("/klientai/save")
def klientai_save(
    cid: int = Form(0),
    pavadinimas: str = Form(""),
    vat_numeris: str = Form(""),
    kontaktinis_asmuo: str = Form(""),
    kontaktinis_el_pastas: str = Form(""),
    kontaktinis_tel: str = Form(""),
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if cid:
        cursor.execute(
            "UPDATE klientai SET pavadinimas=?, vat_numeris=?, kontaktinis_asmuo=?, kontaktinis_el_pastas=?, kontaktinis_tel=?, imone=? WHERE id=?",
            (
                pavadinimas,
                vat_numeris,
                kontaktinis_asmuo,
                kontaktinis_el_pastas,
                kontaktinis_tel,
                imone,
                cid,
            ),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO klientai (pavadinimas, vat_numeris, kontaktinis_asmuo, kontaktinis_el_pastas, kontaktinis_tel, imone) VALUES (?,?,?,?,?,?)",
            (
                pavadinimas,
                vat_numeris,
                kontaktinis_asmuo,
                kontaktinis_el_pastas,
                kontaktinis_tel,
                imone,
            ),
        )
        cid = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, None, action, "klientai", cid)
    return RedirectResponse("/klientai", status_code=303)


@app.get("/api/klientai")
def klientai_api(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM klientai")
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(klientai)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


# ---- Audit log ----

@app.get("/audit", response_class=HTMLResponse)
def audit_list(request: Request):
    return templates.TemplateResponse("audit_list.html", {"request": request})


@app.get("/api/audit")
def audit_api(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    conn, cursor = db
    cursor.execute(
        """SELECT al.id, u.username as user, al.action, al.table_name, al.record_id, al.timestamp, al.details
           FROM audit_log al LEFT JOIN users u ON al.user_id = u.id
           ORDER BY al.timestamp DESC"""
    )
    rows = cursor.fetchall()
    columns = [d[0] for d in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}
