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

# ---- Settings ----


@router.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    return templates.TemplateResponse("settings.html", {"request": request})


@router.get("/api/default-trailer-types")
def default_trailer_types_api(
    imone: str = "",
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    conn, cursor = db
    cursor.execute(
        "SELECT reiksme FROM company_default_trailers WHERE imone=? ORDER BY priority",
        (imone,),
    )
    rows = cursor.fetchall()
    return {"data": [r[0] for r in rows]}


@router.get("/api/default-trailer-types.csv")
def default_trailer_types_csv(
    imone: str = "",
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    """Grąžina numatytuosius priekabų tipus CSV formatu."""
    conn, cursor = db
    cursor.execute(
        "SELECT reiksme FROM company_default_trailers WHERE imone=? ORDER BY priority",
        (imone,),
    )
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=["reiksme"])
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=default-trailer-types.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


@router.post("/settings/save")
async def settings_save(
    request: Request,
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    form = await request.form()
    values = form.getlist("values")
    conn, cursor = db
    cursor.execute("DELETE FROM company_default_trailers WHERE imone=?", (imone,))
    for pr, val in enumerate(values):
        cursor.execute(
            "INSERT INTO company_default_trailers (imone, reiksme, priority) VALUES (?,?,?)",
            (imone, val, pr),
        )
    conn.commit()
    log_action(
        conn,
        cursor,
        request.session.get("user_id"),
        "update",
        "company_default_trailers",
        0,
    )
    return RedirectResponse("/settings", status_code=303)


