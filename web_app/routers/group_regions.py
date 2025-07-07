from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

import sqlite3
from db import init_db
from modules.audit import log_action, fetch_logs
from modules.login import assign_role
from modules.roles import Role
import re
from modules.constants import EU_COUNTRIES, EMPLOYEE_ROLES, DRIVER_NATIONALITIES
from ..utils import (
    ensure_columns,
    compute_limits,
    compute_busena,
    table_csv_response,
    get_db,
)
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
    regionai: str | list[str] = Form(""),
    vadybininkas_id: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if isinstance(regionai, list):
        region_str = ";".join(regionai)
    else:
        region_str = regionai
    sep_codes = re.split(r"[;,\s]+", region_str)
    raw_codes = [r.strip().upper() for r in sep_codes if r.strip()]
    valid_re = re.compile(r"^[A-Z]{2}\d{2}$")
    codes = [c for c in raw_codes if valid_re.match(c)]
    vid = int(vadybininkas_id) if str(vadybininkas_id).strip() else None
    for code in codes:
        cursor.execute(
            "SELECT 1 FROM grupiu_regionai WHERE grupe_id=? AND regiono_kodas=?",
            (grupe_id, code),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            "INSERT INTO grupiu_regionai (grupe_id, regiono_kodas, vadybininkas_id) VALUES (?,?,?)",
            (grupe_id, code, vid),
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
        "SELECT id, regiono_kodas, vadybininkas_id FROM grupiu_regionai WHERE grupe_id=? ORDER BY regiono_kodas",
        (gid_int,),
    )
    rows = cursor.fetchall()
    data = []
    for rid, code, vid in rows:
        cursor.execute(
            "SELECT g.numeris FROM grupiu_regionai gr JOIN grupes g ON gr.grupe_id=g.id WHERE gr.regiono_kodas=? AND gr.grupe_id!=?",
            (code, gid_int),
        )
        others = "; ".join([r[0] for r in cursor.fetchall()])
        cursor.execute("SELECT vardas, pavarde FROM darbuotojai WHERE id=?", (vid,))
        row = cursor.fetchone()
        vname = f"{row[0]} {row[1]}" if row else ""
        data.append(
            {
                "id": rid,
                "regiono_kodas": code,
                "kitos_grupes": others,
                "vadybininkas_id": vid,
                "vadybininkas": vname,
            }
        )
    return {"data": data}


@router.get("/api/group-regions.csv")
def group_regions_csv(
    gid: int, db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)
):
    conn, cursor = db
    cursor.execute(
        "SELECT id, regiono_kodas, vadybininkas_id FROM grupiu_regionai WHERE grupe_id=? ORDER BY regiono_kodas",
        (gid,),
    )
    rows = cursor.fetchall()
    data = []
    for rid, code, vid in rows:
        cursor.execute(
            "SELECT g.numeris FROM grupiu_regionai gr JOIN grupes g ON gr.grupe_id=g.id WHERE gr.regiono_kodas=? AND gr.grupe_id!=?",
            (code, gid),
        )
        others = "; ".join([r[0] for r in cursor.fetchall()])
        data.append((rid, code, vid, others))
    df = pd.DataFrame(
        data, columns=["id", "regiono_kodas", "vadybininkas_id", "kitos_grupes"]
    )
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=group-regions.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)
