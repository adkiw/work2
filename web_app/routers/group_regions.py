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

# ---- Grupiu regionai ----


@router.get("/group-regions", response_class=HTMLResponse)
def group_regions_page(request: Request):
    return templates.TemplateResponse("group_regions.html", {"request": request})


@router.post("/group-regions/add")
def group_regions_add(
    request: Request,
    grupe_id: int = Form(...),
    regionai: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    codes = [r.strip().upper() for r in regionai.split(";") if r.strip()]
    for code in codes:
        cursor.execute(
            "SELECT 1 FROM grupiu_regionai WHERE grupe_id=? AND regiono_kodas=?",
            (grupe_id, code),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            "INSERT INTO grupiu_regionai (grupe_id, regiono_kodas) VALUES (?,?)",
            (grupe_id, code),
        )
        conn.commit()
        log_action(
            conn,
            cursor,
            request.session.get("user_id"),
            "insert",
            "grupiu_regionai",
            cursor.lastrowid,
        )
    return RedirectResponse(f"/group-regions?gid={grupe_id}", status_code=303)


@router.get("/group-regions/{rid}/delete")
def group_regions_delete(
    rid: int,
    request: Request,
    gid: int = 0,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    cursor.execute("DELETE FROM grupiu_regionai WHERE id=?", (rid,))
    conn.commit()
    log_action(
        conn,
        cursor,
        request.session.get("user_id"),
        "delete",
        "grupiu_regionai",
        rid,
    )
    return RedirectResponse(f"/group-regions?gid={gid}", status_code=303)


@router.get("/api/group-regions")
def group_regions_api(
    gid: str | None = None,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    """Return regions for a group or an empty list if group is not specified."""
    if not gid:
        return {"data": []}
    gid_int = int(gid)

    conn, cursor = db
    cursor.execute(
        "SELECT id, regiono_kodas FROM grupiu_regionai WHERE grupe_id=? ORDER BY regiono_kodas",
        (gid_int,),
    )
    rows = cursor.fetchall()
    data = [{"id": r[0], "regiono_kodas": r[1]} for r in rows]
    return {"data": data}


@router.get("/api/group-regions.csv")
def group_regions_csv(
    gid: int, db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)
):
    conn, cursor = db
    cursor.execute(
        "SELECT id, regiono_kodas FROM grupiu_regionai WHERE grupe_id=? ORDER BY regiono_kodas",
        (gid,),
    )
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=["id", "regiono_kodas"])
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=group-regions.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


