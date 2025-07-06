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

# ---- Vairuotojai ----


@router.get("/vairuotojai", response_class=HTMLResponse)
def vairuotojai_list(request: Request):
    return templates.TemplateResponse("vairuotojai_list.html", {"request": request})


@router.get("/vairuotojai/add", response_class=HTMLResponse)
def vairuotojai_add_form(request: Request):
    imone = request.session.get("imone", "")
    return templates.TemplateResponse(
        "vairuotojai_form.html",
        {
            "request": request,
            "data": {"imone": imone},
            "tautybes": DRIVER_NATIONALITIES,
        },
    )


@router.get("/vairuotojai/{did}/edit", response_class=HTMLResponse)
def vairuotojai_edit_form(
    did: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM vairuotojai WHERE id=?", (did,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(vairuotojai)")]
    data = dict(zip(columns, row))
    return templates.TemplateResponse(
        "vairuotojai_form.html",
        {
            "request": request,
            "data": data,
            "tautybes": DRIVER_NATIONALITIES,
        },
    )


@router.post("/vairuotojai/save")
def vairuotojai_save(
    request: Request,
    did: int = Form(0),
    vardas: str = Form(...),
    pavarde: str = Form(""),
    gimimo_metai: str = Form(""),
    tautybe: str = Form(""),
    kadencijos_pabaiga: str = Form(""),
    atostogu_pabaiga: str = Form(""),
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if not user_has_role(request, cursor, Role.ADMIN):
        imone = request.session.get("imone")
    if did:
        cursor.execute(
            "UPDATE vairuotojai SET vardas=?, pavarde=?, gimimo_metai=?, tautybe=?, kadencijos_pabaiga=?, atostogu_pabaiga=?, imone=? WHERE id=?",
            (
                vardas,
                pavarde,
                gimimo_metai,
                tautybe,
                kadencijos_pabaiga,
                atostogu_pabaiga,
                imone,
                did,
            ),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO vairuotojai (vardas, pavarde, gimimo_metai, tautybe, kadencijos_pabaiga, atostogu_pabaiga, imone) VALUES (?,?,?,?,?,?,?)",
            (
                vardas,
                pavarde,
                gimimo_metai,
                tautybe,
                kadencijos_pabaiga,
                atostogu_pabaiga,
                imone,
            ),
        )
        did = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), action, "vairuotojai", did)
    return RedirectResponse("/vairuotojai", status_code=303)


@router.get("/api/vairuotojai")
def vairuotojai_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM vairuotojai")
    else:
        cursor.execute(
            "SELECT * FROM vairuotojai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(vairuotojai)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@router.get("/api/vairuotojai.csv")
def vairuotojai_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM vairuotojai")
    else:
        cursor.execute(
            "SELECT * FROM vairuotojai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(vairuotojai)")]
    df = pd.DataFrame(rows, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=vairuotojai.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


