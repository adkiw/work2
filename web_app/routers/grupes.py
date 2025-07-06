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

# ---- Grupes ----


@router.get("/grupes", response_class=HTMLResponse)
def grupes_list(request: Request):
    return templates.TemplateResponse("grupes_list.html", {"request": request})


@router.get("/grupes/add", response_class=HTMLResponse)
def grupes_add_form(request: Request):
    imone = request.session.get("imone", "")
    return templates.TemplateResponse(
        "grupes_form.html", {"request": request, "data": {"imone": imone}}
    )


@router.get("/grupes/{gid}/edit", response_class=HTMLResponse)
def grupes_edit_form(
    gid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if not user_has_role(request, cursor, Role.ADMIN):
        imone = request.session.get("imone")
    row = cursor.execute("SELECT * FROM grupes WHERE id=?", (gid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(grupes)")]
    data = dict(zip(columns, row))
    return templates.TemplateResponse(
        "grupes_form.html", {"request": request, "data": data}
    )


@router.post("/grupes/save")
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
    if not user_has_role(request, cursor, Role.ADMIN):
        imone = request.session.get("imone")
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
    log_action(conn, cursor, request.session.get("user_id"), action, "grupes", gid)
    return RedirectResponse("/grupes", status_code=303)


@router.get("/api/grupes")
def grupes_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM grupes")
    else:
        cursor.execute(
            "SELECT * FROM grupes WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(grupes)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@router.get("/api/grupes.csv")
def grupes_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM grupes")
    else:
        cursor.execute(
            "SELECT * FROM grupes WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(grupes)")]
    df = pd.DataFrame(rows, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=grupes.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


@router.get("/grupes/{gid}/delete")
def grupes_delete(
    gid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    cursor.execute("DELETE FROM grupiu_regionai WHERE grupe_id=?", (gid,))
    cursor.execute("DELETE FROM grupes WHERE id=?", (gid,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found")
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), "delete", "grupes", gid)
    return RedirectResponse("/grupes", status_code=303)


