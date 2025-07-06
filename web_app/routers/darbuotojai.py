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

# ---- Darbuotojai ----


@router.get("/darbuotojai", response_class=HTMLResponse)
def darbuotojai_list(request: Request):
    return templates.TemplateResponse("darbuotojai_list.html", {"request": request})


@router.get("/darbuotojai/add", response_class=HTMLResponse)
def darbuotojai_add_form(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    grupes = [r[0] for r in cursor.execute("SELECT numeris FROM grupes").fetchall()]
    data = {"imone": request.session.get("imone", "")}
    return templates.TemplateResponse(
        "darbuotojai_form.html",
        {
            "request": request,
            "data": data,
            "roles": EMPLOYEE_ROLES,
            "grupes": grupes,
        },
    )


@router.get("/darbuotojai/{did}/edit", response_class=HTMLResponse)
def darbuotojai_edit_form(
    did: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM darbuotojai WHERE id=?", (did,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(darbuotojai)")]
    data = dict(zip(columns, row))
    grupes = [r[0] for r in cursor.execute("SELECT numeris FROM grupes").fetchall()]

    group = None
    group_regions: list[dict] = []
    if data.get("grupe"):
        group_row = cursor.execute(
            "SELECT id, numeris, pavadinimas FROM grupes WHERE numeris=?",
            (data["grupe"],),
        ).fetchone()
        if group_row:
            gid, numeris, pavadinimas = group_row
            group = {"id": gid, "numeris": numeris, "pavadinimas": pavadinimas}
            cursor.execute(
                "SELECT id, regiono_kodas, vadybininkas_id FROM grupiu_regionai WHERE grupe_id=?",
                (gid,),
            )
            group_regions = [
                {"id": r[0], "regiono_kodas": r[1], "checked": r[2] == did}
                for r in cursor.fetchall()
            ]

    return templates.TemplateResponse(
        "darbuotojai_form.html",
        {
            "request": request,
            "data": data,
            "roles": EMPLOYEE_ROLES,
            "grupes": grupes,
            "group": group,
            "group_regions": group_regions,
        },
    )


@router.post("/darbuotojai/save")
def darbuotojai_save(
    request: Request,
    did: int = Form(0),
    vardas: str = Form(...),
    pavarde: str = Form(""),
    pareigybe: str = Form(""),
    el_pastas: str = Form(""),
    telefonas: str = Form(""),
    grupe: str = Form(""),
    imone: str = Form(""),
    aktyvus: str = Form(None),
    region_ids: list[int] = Form([]),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if not user_has_role(request, cursor, Role.ADMIN):
        imone = request.session.get("imone")
    akt = 1 if aktyvus else 0
    if did:
        cursor.execute(
            "UPDATE darbuotojai SET vardas=?, pavarde=?, pareigybe=?, el_pastas=?, telefonas=?, grupe=?, imone=?, aktyvus=? WHERE id=?",
            (vardas, pavarde, pareigybe, el_pastas, telefonas, grupe, imone, akt, did),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO darbuotojai (vardas, pavarde, pareigybe, el_pastas, telefonas, grupe, imone, aktyvus) VALUES (?,?,?,?,?,?,?,?)",
            (vardas, pavarde, pareigybe, el_pastas, telefonas, grupe, imone, akt),
        )
        did = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), action, "darbuotojai", did)

    # update region assignments
    cursor.execute(
        "UPDATE grupiu_regionai SET vadybininkas_id=NULL WHERE vadybininkas_id=?",
        (did,),
    )
    for rid in region_ids:
        cursor.execute(
            "UPDATE grupiu_regionai SET vadybininkas_id=? WHERE id=?",
            (did, rid),
        )
    conn.commit()

    return RedirectResponse("/darbuotojai", status_code=303)


@router.get("/api/darbuotojai")
def darbuotojai_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM darbuotojai")
    else:
        cursor.execute(
            "SELECT * FROM darbuotojai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(darbuotojai)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@router.get("/api/darbuotojai.csv")
def darbuotojai_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM darbuotojai")
    else:
        cursor.execute(
            "SELECT * FROM darbuotojai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(darbuotojai)")]
    df = pd.DataFrame(rows, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=darbuotojai.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


