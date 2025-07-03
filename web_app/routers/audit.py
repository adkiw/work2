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

# ---- Audit log ----


@router.get("/audit", response_class=HTMLResponse)
def audit_list(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        df = fetch_logs(conn, cursor)
    else:
        df = fetch_logs(conn, cursor, request.session.get("imone"))
    data = df.to_dict(orient="records")
    return templates.TemplateResponse(
        "audit_list.html", {"request": request, "logs": data}
    )


@router.get("/api/audit")
def audit_api(
    request: Request,
    user: str | None = None,
    table: str | None = None,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        df = fetch_logs(conn, cursor)
    else:
        df = fetch_logs(conn, cursor, request.session.get("imone"))
    if user:
        df = df[df["user"] == user]
    if table:
        df = df[df["table_name"] == table]
    data = df.to_dict(orient="records")
    return {"data": data}


@router.get("/api/audit.csv")
def audit_csv(
    request: Request,
    user: str | None = None,
    table: str | None = None,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        df = fetch_logs(conn, cursor)
    else:
        df = fetch_logs(conn, cursor, request.session.get("imone"))
    if user:
        df = df[df["user"] == user]
    if table:
        df = df[df["table_name"] == table]
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=audit.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


