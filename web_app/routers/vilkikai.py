from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

import sqlite3
from ..utils import get_db
from modules.roles import Role
from modules.audit import log_action
from ..auth import user_has_role
import pandas as pd

router = APIRouter()
templates = Jinja2Templates(directory="web_app/templates")

@router.get("/vilkikai", response_class=HTMLResponse)
def vilkikai_list(request: Request):
    return templates.TemplateResponse("vilkikai_list.html", {"request": request})


@router.get("/vilkikai/add", response_class=HTMLResponse)
def vilkikai_add_form(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        trailers = [r[0] for r in cursor.execute("SELECT numeris FROM priekabos").fetchall()]
        vair_rows = cursor.execute("SELECT id, vardas, pavarde FROM vairuotojai").fetchall()
        vadyb_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=?",
            ("Transporto vadybininkas",),
        ).fetchall()
    else:
        imone = request.session.get("imone", "")
        trailers = [r[0] for r in cursor.execute(
            "SELECT numeris FROM priekabos WHERE imone=?", (imone,)
        ).fetchall()]
        vair_rows = cursor.execute(
            "SELECT id, vardas, pavarde FROM vairuotojai WHERE imone=?",
            (imone,),
        ).fetchall()
        vadyb_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=? AND imone=?",
            ("Transporto vadybininkas", imone),
        ).fetchall()
    markes = [r[0] for r in cursor.execute("SELECT reiksme FROM lookup WHERE kategorija='Markė'").fetchall()]
    vairuotojai = [f"{r[1]} {r[2]}" for r in vair_rows]
    vadybininkai = [f"{r[0]} {r[1]}" for r in vadyb_rows]
    context = {
        "request": request,
        "data": {},
        "trailers": trailers,
        "markes": markes,
        "vairuotojai": vairuotojai,
        "vadybininkai": vadybininkai,
        "drv1": "",
        "drv2": "",
        "transporto_grupe": "",
    }
    return templates.TemplateResponse("vilkikai_form.html", context)


@router.get("/vilkikai/{vid}/edit", response_class=HTMLResponse)
def vilkikai_edit_form(
    vid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM vilkikai WHERE id=?", (vid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(vilkikai)")]
    data = dict(zip(columns, row))
    if user_has_role(request, cursor, Role.ADMIN):
        trailers = [r[0] for r in cursor.execute("SELECT numeris FROM priekabos").fetchall()]
        vair_rows = cursor.execute("SELECT id, vardas, pavarde FROM vairuotojai").fetchall()
        vadyb_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=?",
            ("Transporto vadybininkas",),
        ).fetchall()
    else:
        imone = request.session.get("imone", "")
        trailers = [r[0] for r in cursor.execute(
            "SELECT numeris FROM priekabos WHERE imone=?", (imone,)
        ).fetchall()]
        vair_rows = cursor.execute(
            "SELECT id, vardas, pavarde FROM vairuotojai WHERE imone=?",
            (imone,),
        ).fetchall()
        vadyb_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=? AND imone=?",
            ("Transporto vadybininkas", imone),
        ).fetchall()
    markes = [r[0] for r in cursor.execute("SELECT reiksme FROM lookup WHERE kategorija='Markė'").fetchall()]
    vairuotojai = [f"{r[1]} {r[2]}" for r in vair_rows]
    vadybininkai = [f"{r[0]} {r[1]}" for r in vadyb_rows]
    drv1 = ""
    drv2 = ""
    if data.get("vairuotojai"):
        parts = [p.strip() for p in data["vairuotojai"].split(",") if p.strip()]
        if parts:
            drv1 = parts[0]
        if len(parts) > 1:
            drv2 = parts[1]
    grp = ""
    if data.get("vadybininkas"):
        v_parts = data["vadybininkas"].split(" ", 1)
        row_g = cursor.execute(
            "SELECT grupe FROM darbuotojai WHERE vardas=? AND pavarde=?",
            (v_parts[0], v_parts[1] if len(v_parts) > 1 else ""),
        ).fetchone()
        grp = row_g[0] if row_g else ""
    context = {
        "request": request,
        "data": data,
        "trailers": trailers,
        "markes": markes,
        "vairuotojai": vairuotojai,
        "vadybininkai": vadybininkai,
        "drv1": drv1,
        "drv2": drv2,
        "transporto_grupe": grp,
    }
    return templates.TemplateResponse("vilkikai_form.html", context)


@router.post("/vilkikai/save")
def vilkikai_save(
    request: Request,
    vid: int = Form(0),
    numeris: str = Form(...),
    marke: str = Form(""),
    pagaminimo_metai: str = Form(""),
    tech_apziura: str = Form(""),
    draudimas: str = Form(""),
    vadybininkas: str = Form(""),
    vairuotojas1: str = Form(""),
    vairuotojas2: str = Form(""),
    priekaba: str = Form(""),
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    drivers = ", ".join(filter(None, [vairuotojas1, vairuotojas2]))
    if vid:
        cursor.execute(
            "UPDATE vilkikai SET numeris=?, marke=?, pagaminimo_metai=?, tech_apziura=?, draudimas=?, vadybininkas=?, vairuotojai=?, priekaba=?, imone=? WHERE id=?",
            (
                numeris,
                marke,
                pagaminimo_metai,
                tech_apziura,
                draudimas,
                vadybininkas,
                drivers,
                priekaba,
                imone,
                vid,
            ),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO vilkikai (numeris, marke, pagaminimo_metai, tech_apziura, draudimas, vadybininkas, vairuotojai, priekaba, imone) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                numeris,
                marke,
                pagaminimo_metai,
                tech_apziura,
                draudimas,
                vadybininkas,
                drivers,
                priekaba,
                imone,
            ),
        )
        vid = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), action, "vilkikai", vid)
    return RedirectResponse(f"/vilkikai", status_code=303)


@router.get("/api/vilkikai")
def vilkikai_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM vilkikai")
    else:
        cursor.execute(
            "SELECT * FROM vilkikai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(vilkikai)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@router.get("/api/vilkikai.csv")
def vilkikai_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM vilkikai")
    else:
        cursor.execute(
            "SELECT * FROM vilkikai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(vilkikai)")]
    df = pd.DataFrame(rows, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=vilkikai.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)

