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

# ---- Priekabų priskyrimas ----


@router.get("/trailer-swap", response_class=HTMLResponse)
def trailer_swap_form(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    is_admin = user_has_role(request, cursor, Role.ADMIN)
    if is_admin:
        cursor.execute("SELECT numeris, priekaba FROM vilkikai ORDER BY numeris")
    else:
        cursor.execute(
            "SELECT numeris, priekaba FROM vilkikai WHERE imone=? ORDER BY numeris",
            (request.session.get("imone"),),
        )
    trucks = cursor.fetchall()
    if is_admin:
        cursor.execute("SELECT numeris FROM priekabos ORDER BY numeris")
    else:
        cursor.execute(
            "SELECT numeris FROM priekabos WHERE imone=? ORDER BY numeris",
            (request.session.get("imone"),),
        )
    trailers = [r[0] for r in cursor.fetchall()]
    trailer_info: list[tuple[str, str | None]] = []
    for num in trailers:
        if is_admin:
            cursor.execute(
                "SELECT numeris FROM vilkikai WHERE priekaba=?",
                (num,),
            )
        else:
            cursor.execute(
                "SELECT numeris FROM vilkikai WHERE priekaba=? AND imone=?",
                (num, request.session.get("imone")),
            )
        row = cursor.fetchone()
        assigned = row[0] if row and row[0] else None
        trailer_info.append((num, assigned))
    context = {
        "request": request,
        "trucks": trucks,
        "trailers": trailer_info,
    }
    return templates.TemplateResponse("trailer_swap.html", context)


@router.post("/trailer-swap")
def trailer_swap(
    request: Request,
    vilkikas: str = Form(...),
    priekaba: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    is_admin = user_has_role(request, cursor, Role.ADMIN)
    params = (vilkikas,) if is_admin else (vilkikas, request.session.get("imone"))
    cursor.execute(
        "SELECT id, priekaba FROM vilkikai WHERE numeris=?"
        + ("" if is_admin else " AND imone=?"),
        params,
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Vilkikas nerastas")
    vid, cur_trailer = row[0], row[1] or ""
    if priekaba:
        params2 = (priekaba,) if is_admin else (priekaba, request.session.get("imone"))
        cursor.execute(
            "SELECT id, numeris FROM vilkikai WHERE priekaba=?"
            + ("" if is_admin else " AND imone=?"),
            params2,
        )
        other = cursor.fetchone()
        other_id = other[0] if other else None
        other_num = other[1] if other else None
    else:
        other_id = None
        other_num = None

    if other_id and other_num != vilkikas:
        params3 = (
            (cur_trailer or "", other_num)
            if is_admin
            else (cur_trailer or "", other_num, request.session.get("imone"))
        )
        cursor.execute(
            "UPDATE vilkikai SET priekaba=? WHERE numeris=?"
            + ("" if is_admin else " AND imone=?"),
            params3,
        )
        log_action(
            conn, cursor, request.session.get("user_id"), "update", "vilkikai", other_id
        )

    params4 = (
        (priekaba or "", vilkikas)
        if is_admin
        else (priekaba or "", vilkikas, request.session.get("imone"))
    )
    cursor.execute(
        "UPDATE vilkikai SET priekaba=? WHERE numeris=?"
        + ("" if is_admin else " AND imone=?"),
        params4,
    )
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), "update", "vilkikai", vid)
    return RedirectResponse("/trailer-swap", status_code=303)


