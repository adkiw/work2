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

# ---- Trailer types ----


@router.get("/trailer-types", response_class=HTMLResponse)
def trailer_types_list(
    request: Request,
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    return templates.TemplateResponse("trailer_types_list.html", {"request": request})


@router.get("/trailer-types/add", response_class=HTMLResponse)
def trailer_types_add_form(
    request: Request,
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    return templates.TemplateResponse(
        "trailer_types_form.html", {"request": request, "data": {}}
    )


@router.get("/trailer-types/{tid}/edit", response_class=HTMLResponse)
def trailer_types_edit_form(
    tid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        row = cursor.execute(
            "SELECT id, reiksme FROM lookup WHERE kategorija='Priekabos tipas' AND id=?",
            (tid,),
        ).fetchone()
    else:
        imone = request.session.get("imone", "")
        row = cursor.execute(
            "SELECT id, reiksme FROM company_settings WHERE kategorija='Priekabos tipas' AND id=? AND imone=?",
            (tid, imone),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    data = {"id": row[0], "reiksme": row[1]}
    return templates.TemplateResponse(
        "trailer_types_form.html", {"request": request, "data": data}
    )


@router.post("/trailer-types/save")
def trailer_types_save(
    request: Request,
    tid: int = Form(0),
    reiksme: str = Form(...),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        table = "lookup"
        if tid:
            cursor.execute(
                "UPDATE lookup SET reiksme=? WHERE id=? AND kategorija='Priekabos tipas'",
                (reiksme, tid),
            )
            action = "update"
        else:
            cursor.execute(
                "INSERT INTO lookup (kategorija, reiksme) VALUES ('Priekabos tipas', ?)",
                (reiksme,),
            )
            tid = cursor.lastrowid
            action = "insert"
    else:
        table = "company_settings"
        imone = request.session.get("imone", "")
        if tid:
            cursor.execute(
                "UPDATE company_settings SET reiksme=? WHERE id=?",
                (reiksme, tid),
            )
            action = "update"
        else:
            cursor.execute(
                "INSERT INTO company_settings (imone, kategorija, reiksme) VALUES (?,?,?)",
                (imone, "Priekabos tipas", reiksme),
            )
            tid = cursor.lastrowid
            action = "insert"
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), action, table, tid)
    return RedirectResponse("/trailer-types", status_code=303)


@router.get("/trailer-types/{tid}/delete")
def trailer_types_delete(
    tid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    """Ištrina priekabos tipą."""
    conn, cursor = db
    is_admin = user_has_role(request, cursor, Role.ADMIN)
    if is_admin:
        cursor.execute(
            "DELETE FROM lookup WHERE id=? AND kategorija='Priekabos tipas'",
            (tid,),
        )
        table = "lookup"
    else:
        imone = request.session.get("imone", "")
        cursor.execute(
            "DELETE FROM company_settings WHERE id=? AND imone=? AND kategorija='Priekabos tipas'",
            (tid, imone),
        )
        table = "company_settings"
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found")
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), "delete", table, tid)
    return RedirectResponse("/trailer-types", status_code=303)


@router.get("/api/trailer-types")
def trailer_types_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute(
            "SELECT id, reiksme FROM lookup WHERE kategorija='Priekabos tipas'"
        )
    else:
        imone = request.session.get("imone", "")
        cursor.execute(
            "SELECT id, reiksme FROM company_settings WHERE imone=? AND kategorija='Priekabos tipas'",
            (imone,),
        )
    rows = cursor.fetchall()
    data = [{"id": r[0], "reiksme": r[1]} for r in rows]
    return {"data": data}


@router.get("/api/trailer-types.csv")
def trailer_types_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        return table_csv_response(cursor, "lookup", "trailer-types.csv")
    imone = request.session.get("imone", "")
    cursor.execute(
        "SELECT id, reiksme FROM company_settings WHERE imone=? AND kategorija='Priekabos tipas'",
        (imone,),
    )
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=["id", "reiksme"])
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=trailer-types.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


