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

# ---- Klientai ----


@router.get("/klientai", response_class=HTMLResponse)
def klientai_list(request: Request):
    return templates.TemplateResponse("klientai_list.html", {"request": request})


@router.get("/klientai/add", response_class=HTMLResponse)
def klientai_add_form(request: Request):
    data = {"imone": request.session.get("imone", "")}
    return templates.TemplateResponse(
        "klientai_form.html",
        {"request": request, "data": data, "salys": EU_COUNTRIES},
    )


@router.get("/klientai/{cid}/edit", response_class=HTMLResponse)
def klientai_edit_form(
    cid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM klientai WHERE id=?", (cid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(klientai)")]
    data = dict(zip(columns, row))
    return templates.TemplateResponse(
        "klientai_form.html",
        {"request": request, "data": data, "salys": EU_COUNTRIES},
    )


@router.post("/klientai/save")
def klientai_save(
    cid: int = Form(0),
    pavadinimas: str = Form(""),
    vat_numeris: str = Form(""),
    kontaktinis_asmuo: str = Form(""),
    kontaktinis_el_pastas: str = Form(""),
    kontaktinis_tel: str = Form(""),
    salis: str = Form(""),
    regionas: str = Form(""),
    miestas: str = Form(""),
    adresas: str = Form(""),
    saskaitos_asmuo: str = Form(""),
    saskaitos_el_pastas: str = Form(""),
    saskaitos_tel: str = Form(""),
    coface_limitas: float = Form(0.0),
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    musu, liks = compute_limits(cursor, vat_numeris, coface_limitas)
    if cid:
        cursor.execute(
            "UPDATE klientai SET pavadinimas=?, vat_numeris=?, kontaktinis_asmuo=?, kontaktinis_el_pastas=?, kontaktinis_tel=?, salis=?, regionas=?, miestas=?, adresas=?, saskaitos_asmuo=?, saskaitos_el_pastas=?, saskaitos_tel=?, coface_limitas=?, musu_limitas=?, likes_limitas=?, imone=? WHERE id=?",
            (
                pavadinimas,
                vat_numeris,
                kontaktinis_asmuo,
                kontaktinis_el_pastas,
                kontaktinis_tel,
                salis,
                regionas,
                miestas,
                adresas,
                saskaitos_asmuo,
                saskaitos_el_pastas,
                saskaitos_tel,
                coface_limitas,
                musu,
                liks,
                imone,
                cid,
            ),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO klientai (pavadinimas, vat_numeris, kontaktinis_asmuo, kontaktinis_el_pastas, kontaktinis_tel, salis, regionas, miestas, adresas, saskaitos_asmuo, saskaitos_el_pastas, saskaitos_tel, coface_limitas, musu_limitas, likes_limitas, imone) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                pavadinimas,
                vat_numeris,
                kontaktinis_asmuo,
                kontaktinis_el_pastas,
                kontaktinis_tel,
                salis,
                regionas,
                miestas,
                adresas,
                saskaitos_asmuo,
                saskaitos_el_pastas,
                saskaitos_tel,
                coface_limitas,
                musu,
                liks,
                imone,
            ),
        )
        cid = cursor.lastrowid
        action = "insert"
    conn.commit()
    cursor.execute(
        "UPDATE klientai SET coface_limitas=?, musu_limitas=?, likes_limitas=? WHERE vat_numeris=?",
        (coface_limitas, musu, liks, vat_numeris),
    )
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), action, "klientai", cid)
    return RedirectResponse("/klientai", status_code=303)


@router.get("/api/klientai")
def klientai_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM klientai")
    else:
        cursor.execute(
            "SELECT * FROM klientai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(klientai)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@router.get("/api/klientai.csv")
def klientai_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM klientai")
    else:
        cursor.execute(
            "SELECT * FROM klientai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(klientai)")]
    df = pd.DataFrame(rows, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=klientai.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


