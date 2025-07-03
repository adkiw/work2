from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

import sqlite3
from typing import Generator
from db import init_db
from modules.audit import log_action, fetch_logs
from modules.login import assign_role
from modules.roles import Role
from modules.constants import EU_COUNTRIES, EMPLOYEE_ROLES, DRIVER_NATIONALITIES
from ..utils import (
    ensure_columns,
    compute_limits,
    compute_busena,
    table_csv_response,
    get_db,
)
from ..auth import user_has_role, require_roles

router = APIRouter()
templates = Jinja2Templates(directory="web_app/templates")
import datetime
from datetime import date
import pandas as pd

@router.get("/api/eu-countries")
def eu_countries():
    """Grąžina Europos šalių sąrašą."""
    return {
        "data": [{"name": name, "code": code} for name, code in EU_COUNTRIES if name]
    }


@router.get("/api/eu-countries.csv")
def eu_countries_csv():
    """Grąžina Europos šalis CSV formatu."""
    df = pd.DataFrame([
        {"name": name, "code": code}
        for name, code in EU_COUNTRIES
        if name
    ])
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=eu-countries.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)
@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/kroviniai", response_class=HTMLResponse)
def kroviniai_list(request: Request):
    return templates.TemplateResponse("kroviniai_list.html", {"request": request})


@router.get("/kroviniai/add", response_class=HTMLResponse)
def kroviniai_add_form(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        klientai = [
            r[0] for r in cursor.execute("SELECT pavadinimas FROM klientai").fetchall()
        ]
        vilkikai = [
            r[0] for r in cursor.execute("SELECT numeris FROM vilkikai").fetchall()
        ]
        eksped_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=?",
            ("Ekspedicijos vadybininkas",),
        ).fetchall()
    else:
        imone = request.session.get("imone", "")
        klientai = [
            r[0]
            for r in cursor.execute(
                "SELECT pavadinimas FROM klientai WHERE imone=?",
                (imone,),
            ).fetchall()
        ]
        vilkikai = [
            r[0]
            for r in cursor.execute(
                "SELECT numeris FROM vilkikai WHERE imone=?",
                (imone,),
            ).fetchall()
        ]
        eksped_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=? AND imone=?",
            ("Ekspedicijos vadybininkas", imone),
        ).fetchall()
    eksped = [f"{r[0]} {r[1]}" for r in eksped_rows]
    context = {
        "request": request,
        "data": {},
        "klientai": klientai,
        "vilkikai": vilkikai,
        "eksped_vadybininkai": eksped,
        "salys": EU_COUNTRIES,
        "imone": request.session.get("imone"),
    }
    return templates.TemplateResponse("kroviniai_form.html", context)


@router.get("/kroviniai/{cid}/edit", response_class=HTMLResponse)
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
    if user_has_role(request, cursor, Role.ADMIN):
        klientai = [
            r[0] for r in cursor.execute("SELECT pavadinimas FROM klientai").fetchall()
        ]
        vilkikai = [
            r[0] for r in cursor.execute("SELECT numeris FROM vilkikai").fetchall()
        ]
        eksped_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=?",
            ("Ekspedicijos vadybininkas",),
        ).fetchall()
    else:
        imone = request.session.get("imone", "")
        klientai = [
            r[0]
            for r in cursor.execute(
                "SELECT pavadinimas FROM klientai WHERE imone=?",
                (imone,),
            ).fetchall()
        ]
        vilkikai = [
            r[0]
            for r in cursor.execute(
                "SELECT numeris FROM vilkikai WHERE imone=?",
                (imone,),
            ).fetchall()
        ]
        eksped_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=? AND imone=?",
            ("Ekspedicijos vadybininkas", imone),
        ).fetchall()
    eksped = [f"{r[0]} {r[1]}" for r in eksped_rows]
    context = {
        "request": request,
        "data": data,
        "klientai": klientai,
        "vilkikai": vilkikai,
        "eksped_vadybininkai": eksped,
        "salys": EU_COUNTRIES,
        "imone": request.session.get("imone"),
    }
    return templates.TemplateResponse("kroviniai_form.html", context)


@router.post("/kroviniai/save")
def kroviniai_save(
    request: Request,
    cid: int = Form(0),
    klientas: str = Form(...),
    vilkikas: str = Form(""),
    priekaba: str = Form(""),
    uzsakymo_numeris: str = Form(...),
    saskaitos_busena: str = Form("Neapmokėta"),
    pakrovimo_data: str = Form(...),
    iskrovimo_data: str = Form(...),
    pakrovimo_salis: str = Form(""),
    iskrovimo_salis: str = Form(""),
    pakrovimo_regionas: str = Form(""),
    iskrovimo_regionas: str = Form(""),
    pakrovimo_miestas: str = Form(""),
    iskrovimo_miestas: str = Form(""),
    pakrovimo_adresas: str = Form(""),
    iskrovimo_adresas: str = Form(""),
    pakrovimo_laikas_nuo: str = Form(""),
    pakrovimo_laikas_iki: str = Form(""),
    iskrovimo_laikas_nuo: str = Form(""),
    iskrovimo_laikas_iki: str = Form(""),
    kilometrai: int = Form(0),
    frachtas: float = Form(0.0),
    svoris: int = Form(0),
    paleciu_skaicius: int = Form(0),
    ekspedicijos_vadybininkas: str = Form(""),
    busena: str = Form("Nesuplanuotas"),
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if not imone:
        imone = request.session.get("imone")
    cols = [
        "klientas",
        "vilkikas",
        "priekaba",
        "uzsakymo_numeris",
        "saskaitos_busena",
        "pakrovimo_data",
        "iskrovimo_data",
        "pakrovimo_salis",
        "iskrovimo_salis",
        "pakrovimo_regionas",
        "iskrovimo_regionas",
        "pakrovimo_miestas",
        "iskrovimo_miestas",
        "pakrovimo_adresas",
        "iskrovimo_adresas",
        "pakrovimo_laikas_nuo",
        "pakrovimo_laikas_iki",
        "iskrovimo_laikas_nuo",
        "iskrovimo_laikas_iki",
        "kilometrai",
        "frachtas",
        "svoris",
        "paleciu_skaicius",
        "ekspedicijos_vadybininkas",
        "busena",
        "imone",
    ]
    vals = [
        klientas,
        vilkikas,
        priekaba,
        uzsakymo_numeris,
        saskaitos_busena,
        pakrovimo_data,
        iskrovimo_data,
        pakrovimo_salis,
        iskrovimo_salis,
        pakrovimo_regionas,
        iskrovimo_regionas,
        pakrovimo_miestas,
        iskrovimo_miestas,
        pakrovimo_adresas,
        iskrovimo_adresas,
        pakrovimo_laikas_nuo,
        pakrovimo_laikas_iki,
        iskrovimo_laikas_nuo,
        iskrovimo_laikas_iki,
        kilometrai,
        frachtas,
        svoris,
        paleciu_skaicius,
        ekspedicijos_vadybininkas,
        busena,
        imone,
    ]
    if cid:
        set_clause = ",".join([f"{c}=?" for c in cols])
        cursor.execute(
            f"UPDATE kroviniai SET {set_clause} WHERE id=?",
            vals + [cid],
        )
        action = "update"
    else:
        placeholders = ",".join(["?"] * len(cols))
        col_str = ",".join(cols)
        cursor.execute(
            f"INSERT INTO kroviniai ({col_str}) VALUES ({placeholders})",
            vals,
        )
        cid = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), action, "kroviniai", cid)
    return RedirectResponse(f"/kroviniai", status_code=303)


@router.get("/api/kroviniai")
def kroviniai_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM kroviniai")
    else:
        cursor.execute(
            "SELECT * FROM kroviniai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(kroviniai)")]
    data = [dict(zip(columns, row)) for row in rows]
    for d in data:
        d["busena"] = compute_busena(cursor, d)
    return {"data": data}


@router.get("/api/kroviniai.csv")
def kroviniai_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM kroviniai")
    else:
        cursor.execute(
            "SELECT * FROM kroviniai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(kroviniai)")]
    data = [dict(zip(columns, row)) for row in rows]
    for d in data:
        d["busena"] = compute_busena(cursor, d)
    df = pd.DataFrame(data, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=kroviniai.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


