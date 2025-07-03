from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

import sqlite3
from db import init_db
from modules.audit import log_action, fetch_logs
from modules.login import assign_role
from modules.roles import Role
from modules.constants import EU_COUNTRIES, EMPLOYEE_ROLES, DRIVER_NATIONALITIES
from ..utils import ensure_columns, compute_limits, compute_busena, table_csv_response, get_db
from ..auth import user_has_role, require_roles
import datetime
from datetime import date
import pandas as pd

router = APIRouter()
templates = Jinja2Templates(directory="web_app/templates")

# ---- Priekabos ----


@router.get("/priekabos", response_class=HTMLResponse)
def priekabos_list(request: Request):
    return templates.TemplateResponse("priekabos_list.html", {"request": request})


@router.get("/priekabos/add", response_class=HTMLResponse)
def priekabos_add_form(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    imone = request.session.get("imone", "")
    cursor.execute(
        "SELECT reiksme FROM company_settings WHERE imone=? AND kategorija='Priekabos tipas' ORDER BY reiksme",
        (imone,),
    )
    rows = cursor.fetchall()
    if rows:
        tipai = [r[0] for r in rows]
    else:
        cursor.execute(
            "SELECT reiksme FROM lookup WHERE kategorija='Priekabos tipas' ORDER BY reiksme"
        )
        tipai = [r[0] for r in cursor.fetchall()]
    markes = [
        r[0]
        for r in cursor.execute(
            "SELECT reiksme FROM lookup WHERE kategorija='Markė'"
        ).fetchall()
    ]
    return templates.TemplateResponse(
        "priekabos_form.html",
        {"request": request, "data": {}, "tipai": tipai, "markes": markes},
    )


@router.get("/priekabos/{pid}/edit", response_class=HTMLResponse)
def priekabos_edit_form(
    pid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM priekabos WHERE id=?", (pid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(priekabos)")]
    data = dict(zip(columns, row))
    imone = request.session.get("imone", "")
    cursor.execute(
        "SELECT reiksme FROM company_settings WHERE imone=? AND kategorija='Priekabos tipas' ORDER BY reiksme",
        (imone,),
    )
    rows = cursor.fetchall()
    if rows:
        tipai = [r[0] for r in rows]
    else:
        cursor.execute(
            "SELECT reiksme FROM lookup WHERE kategorija='Priekabos tipas' ORDER BY reiksme"
        )
        tipai = [r[0] for r in cursor.fetchall()]
    markes = [
        r[0]
        for r in cursor.execute(
            "SELECT reiksme FROM lookup WHERE kategorija='Markė'"
        ).fetchall()
    ]
    return templates.TemplateResponse(
        "priekabos_form.html",
        {
            "request": request,
            "data": data,
            "tipai": tipai,
            "markes": markes,
        },
    )


@router.post("/priekabos/save")
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
            (
                priekabu_tipas,
                numeris,
                marke,
                pagaminimo_metai,
                tech_apziura,
                draudimas,
                imone,
                pid,
            ),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO priekabos (priekabu_tipas, numeris, marke, pagaminimo_metai, tech_apziura, draudimas, imone) VALUES (?,?,?,?,?,?,?)",
            (
                priekabu_tipas,
                numeris,
                marke,
                pagaminimo_metai,
                tech_apziura,
                draudimas,
                imone,
            ),
        )
        pid = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), action, "priekabos", pid)
    return RedirectResponse("/priekabos", status_code=303)


@router.get("/api/priekabos")
def priekabos_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM priekabos")
    else:
        cursor.execute(
            "SELECT * FROM priekabos WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(priekabos)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@router.get("/api/priekabos.csv")
def priekabos_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM priekabos")
    else:
        cursor.execute(
            "SELECT * FROM priekabos WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(priekabos)")]
    df = pd.DataFrame(rows, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=priekabos.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


