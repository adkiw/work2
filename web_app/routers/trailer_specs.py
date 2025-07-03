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

# ---- Trailer specs ----


@router.get("/trailer-specs", response_class=HTMLResponse)
def trailer_specs_list(
    request: Request,
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    return templates.TemplateResponse("trailer_specs_list.html", {"request": request})


@router.get("/trailer-specs/add", response_class=HTMLResponse)
def trailer_specs_add_form(
    request: Request,
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    return templates.TemplateResponse(
        "trailer_specs_form.html", {"request": request, "data": {}}
    )


@router.get("/trailer-specs/{sid}/edit", response_class=HTMLResponse)
def trailer_specs_edit_form(
    sid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM trailer_specs WHERE id=?", (sid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(trailer_specs)")]
    data = dict(zip(columns, row))
    return templates.TemplateResponse(
        "trailer_specs_form.html", {"request": request, "data": data}
    )


@router.post("/trailer-specs/save")
def trailer_specs_save(
    request: Request,
    sid: int = Form(0),
    tipas: str = Form(...),
    ilgis: float = Form(0.0),
    plotis: float = Form(0.0),
    aukstis: float = Form(0.0),
    keliamoji_galia: float = Form(0.0),
    talpa: float = Form(0.0),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    conn, cursor = db
    if sid:
        cursor.execute(
            "UPDATE trailer_specs SET tipas=?, ilgis=?, plotis=?, aukstis=?, keliamoji_galia=?, talpa=? WHERE id=?",
            (tipas, ilgis, plotis, aukstis, keliamoji_galia, talpa, sid),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO trailer_specs (tipas, ilgis, plotis, aukstis, keliamoji_galia, talpa) VALUES (?,?,?,?,?,?)",
            (tipas, ilgis, plotis, aukstis, keliamoji_galia, talpa),
        )
        sid = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(
        conn, cursor, request.session.get("user_id"), action, "trailer_specs", sid
    )
    return RedirectResponse("/trailer-specs", status_code=303)


@router.get("/api/trailer-specs")
def trailer_specs_api(
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    conn, cursor = db
    cursor.execute("SELECT * FROM trailer_specs")
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(trailer_specs)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@router.get("/api/trailer-specs.csv")
def trailer_specs_csv(
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    conn, cursor = db
    return table_csv_response(cursor, "trailer_specs", "trailer-specs.csv")


