from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import sqlite3
from typing import Generator
from db import init_db

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


def ensure_columns(conn: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
    """Ensure required columns exist for tables used by the web app."""
    tables = {
        "kroviniai": EXPECTED_KROVINIAI_COLUMNS,
        "vilkikai": EXPECTED_VILKIKAI_COLUMNS,
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
    conn.commit()
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
def vilkikai_add_form(request: Request):
    return templates.TemplateResponse(
        "vilkikai_form.html", {"request": request, "data": {}}
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
    return templates.TemplateResponse(
        "vilkikai_form.html", {"request": request, "data": data}
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
    conn.commit()
    return RedirectResponse(f"/vilkikai", status_code=303)


@app.get("/api/vilkikai")
def vilkikai_api(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM vilkikai")
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(vilkikai)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}
