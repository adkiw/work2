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

# ---- Updates ----


@router.get("/updates", response_class=HTMLResponse)
def updates_list(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    """Rodo krovinius pagal pasirinktą transporto vadybininką."""
    conn, cursor = db
    cursor.execute(
        "SELECT DISTINCT vadybininkas FROM vilkikai "
        "WHERE vadybininkas IS NOT NULL AND vadybininkas != ''"
    )
    managers = [r[0] for r in cursor.fetchall()]
    return templates.TemplateResponse(
        "updates_list.html", {"request": request, "managers": managers}
    )


@router.get("/updates/add", response_class=HTMLResponse)
def updates_add_form(request: Request):
    return templates.TemplateResponse(
        "updates_form.html", {"request": request, "data": {}}
    )


@router.get("/api/shipments")
def shipments_by_manager(
    manager: str,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    """Grąžina krovinius pasirinktam transporto vadybininkui."""
    conn, cursor = db
    today = date.today().isoformat()
    rows = cursor.execute(
        """
        SELECT id, vilkikas, pakrovimo_data, iskrovimo_data
        FROM kroviniai
        WHERE transporto_vadybininkas=? AND date(pakrovimo_data) >= ?
        ORDER BY pakrovimo_data
        """,
        (manager, today),
    ).fetchall()

    data = []
    for sid, vilk, pkd, ikd in rows:
        upd = cursor.execute(
            """
            SELECT id, sa, darbo_laikas, likes_laikas, pakrovimo_statusas,
                   pakrovimo_laikas, pakrovimo_data, iskrovimo_statusas,
                   iskrovimo_laikas, iskrovimo_data, komentaras, created_at
            FROM vilkiku_darbo_laikai
            WHERE vilkiko_numeris=? AND data=?
            ORDER BY id DESC LIMIT 1
            """,
            (vilk, pkd),
        ).fetchone()
        if upd:
            (
                upd_id,
                sa,
                dl,
                ll,
                pk_st,
                pk_laik,
                pk_dat,
                ik_st,
                ik_laik,
                ik_dat,
                kom,
                created,
            ) = upd
        else:
            upd_id = 0
            sa = dl = ll = pk_st = pk_laik = pk_dat = ""
            ik_st = ik_laik = ik_dat = kom = ""
            created = None
        data.append(
            {
                "id": sid,
                "vilkikas": vilk,
                "pakrovimo_data": pkd,
                "iskrovimo_data": ikd,
                "update_id": upd_id,
                "sa": sa,
                "darbo_laikas": dl,
                "likes_laikas": ll,
                "pakrovimo_statusas": pk_st,
                "pakrovimo_laikas": pk_laik,
                "pakrovimo_data_plan": pk_dat,
                "iskrovimo_statusas": ik_st,
                "iskrovimo_laikas": ik_laik,
                "iskrovimo_data_plan": ik_dat,
                "komentaras": kom,
                "created_at": created,
            }
        )

    return {"data": data}


@router.get("/updates/{uid}/edit", response_class=HTMLResponse)
def updates_edit_form(
    uid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    row = cursor.execute(
        "SELECT * FROM vilkiku_darbo_laikai WHERE id=?", (uid,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [
        col[1] for col in cursor.execute("PRAGMA table_info(vilkiku_darbo_laikai)")
    ]
    data = dict(zip(columns, row))
    return templates.TemplateResponse(
        "updates_form.html", {"request": request, "data": data}
    )


@router.get("/updates/ship/{sid}", response_class=HTMLResponse)
def updates_edit_shipment(
    sid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    """Atnaujinimo forma konkrečiam krovinio įrašui."""
    conn, cursor = db
    ship_row = cursor.execute(
        "SELECT * FROM kroviniai WHERE id=?",
        (sid,),
    ).fetchone()
    if not ship_row:
        raise HTTPException(status_code=404, detail="Not found")

    ship_cols = [col[1] for col in cursor.execute("PRAGMA table_info(kroviniai)")]
    shipment = dict(zip(ship_cols, ship_row))

    upd_row = cursor.execute(
        """
        SELECT * FROM vilkiku_darbo_laikai
        WHERE vilkiko_numeris=? AND data=?
        ORDER BY id DESC LIMIT 1
        """,
        (shipment["vilkikas"], shipment["pakrovimo_data"]),
    ).fetchone()

    if upd_row:
        upd_cols = [
            col[1] for col in cursor.execute("PRAGMA table_info(vilkiku_darbo_laikai)")
        ]
        data = dict(zip(upd_cols, upd_row))
    else:
        data = {
            "vilkiko_numeris": shipment["vilkikas"],
            "data": shipment["pakrovimo_data"],
        }

    return templates.TemplateResponse(
        "updates_form.html",
        {"request": request, "data": data, "shipment": shipment},
    )


@router.post("/updates/save")
def updates_save(
    request: Request,
    uid: int = Form(0),
    vilkiko_numeris: str = Form(...),
    data: str = Form(...),
    darbo_laikas: int = Form(0),
    likes_laikas: int = Form(0),
    sa: str = Form(""),
    pakrovimo_statusas: str = Form(""),
    pakrovimo_laikas: str = Form(""),
    pakrovimo_data: str = Form(""),
    iskrovimo_statusas: str = Form(""),
    iskrovimo_laikas: str = Form(""),
    iskrovimo_data: str = Form(""),
    komentaras: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    now_str = (
        datetime.datetime.now()
        .replace(second=0, microsecond=0)
        .isoformat(timespec="minutes")
    )
    if uid:
        cursor.execute(
            "UPDATE vilkiku_darbo_laikai SET vilkiko_numeris=?, data=?, sa=?, darbo_laikas=?, likes_laikas=?, pakrovimo_statusas=?, pakrovimo_laikas=?, pakrovimo_data=?, iskrovimo_statusas=?, iskrovimo_laikas=?, iskrovimo_data=?, komentaras=?, created_at=? WHERE id=?",
            (
                vilkiko_numeris,
                data,
                sa,
                darbo_laikas,
                likes_laikas,
                pakrovimo_statusas,
                pakrovimo_laikas,
                pakrovimo_data,
                iskrovimo_statusas,
                iskrovimo_laikas,
                iskrovimo_data,
                komentaras,
                now_str,
                uid,
            ),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO vilkiku_darbo_laikai (vilkiko_numeris, data, sa, darbo_laikas, likes_laikas, pakrovimo_statusas, pakrovimo_laikas, pakrovimo_data, iskrovimo_statusas, iskrovimo_laikas, iskrovimo_data, komentaras, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                vilkiko_numeris,
                data,
                sa,
                darbo_laikas,
                likes_laikas,
                pakrovimo_statusas,
                pakrovimo_laikas,
                pakrovimo_data,
                iskrovimo_statusas,
                iskrovimo_laikas,
                iskrovimo_data,
                komentaras,
                now_str,
            ),
        )
        uid = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(
        conn,
        cursor,
        request.session.get("user_id"),
        action,
        "vilkiku_darbo_laikai",
        uid,
    )
    return RedirectResponse("/updates", status_code=303)


@router.get("/api/updates")
def updates_api(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM vilkiku_darbo_laikai")
    rows = cursor.fetchall()
    columns = [
        col[1] for col in cursor.execute("PRAGMA table_info(vilkiku_darbo_laikai)")
    ]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@router.get("/api/updates.csv")
def updates_csv(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM vilkiku_darbo_laikai")
    rows = cursor.fetchall()
    columns = [
        col[1] for col in cursor.execute("PRAGMA table_info(vilkiku_darbo_laikai)")
    ]
    df = pd.DataFrame(rows, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=updates.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


@router.get("/api/updates-range")
def updates_range(
    start: str,
    end: str,
    vilkikas: str | None = None,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    """Grąžina darbo laiko įrašus pasirinktam intervalui."""
    conn, cursor = db
    query = "SELECT * FROM vilkiku_darbo_laikai WHERE date(data) BETWEEN ? AND ?"
    params: list[str] = [start, end]
    if vilkikas:
        query += " AND vilkiko_numeris=?"
        params.append(vilkikas)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(vilkiku_darbo_laikai)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@router.get("/api/updates-range.csv")
def updates_range_csv(
    start: str,
    end: str,
    vilkikas: str | None = None,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    """Grąžina darbo laiko įrašus intervalui CSV formatu."""
    conn, cursor = db
    query = "SELECT * FROM vilkiku_darbo_laikai WHERE date(data) BETWEEN ? AND ?"
    params: list[str] = [start, end]
    if vilkikas:
        query += " AND vilkiko_numeris=?"
        params.append(vilkikas)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [
        col[1] for col in cursor.execute("PRAGMA table_info(vilkiku_darbo_laikai)")
    ]
    df = pd.DataFrame(rows, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=updates-range.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


