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

# ---- Registracijos ----


@router.get("/registracijos", response_class=HTMLResponse)
def registracijos_list(
    request: Request,
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    return templates.TemplateResponse("registracijos_list.html", {"request": request})


@router.get("/api/registracijos")
def registracijos_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        rows = cursor.execute(
            "SELECT id, username, imone, vardas, pavarde, pareigybe, grupe FROM users WHERE aktyvus=0"
        ).fetchall()
    else:
        rows = cursor.execute(
            "SELECT id, username, imone, vardas, pavarde, pareigybe, grupe FROM users WHERE aktyvus=0 AND imone=?",
            (request.session.get("imone"),),
        ).fetchall()
    data = [
        {
            "id": r[0],
            "username": r[1],
            "imone": r[2],
            "vardas": r[3],
            "pavarde": r[4],
            "pareigybe": r[5],
            "grupe": r[6],
        }
        for r in rows
    ]
    return {"data": data}


@router.get("/api/registracijos.csv")
def registracijos_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    """Laukiančių registracijų sąrašas CSV formatu."""
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        rows = cursor.execute(
            "SELECT id, username, imone, vardas, pavarde, pareigybe, grupe FROM users WHERE aktyvus=0"
        ).fetchall()
    else:
        rows = cursor.execute(
            "SELECT id, username, imone, vardas, pavarde, pareigybe, grupe FROM users WHERE aktyvus=0 AND imone=?",
            (request.session.get("imone"),),
        ).fetchall()
    df = pd.DataFrame(
        rows,
        columns=["id", "username", "imone", "vardas", "pavarde", "pareigybe", "grupe"],
    )
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=registracijos.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


@router.get("/api/aktyvus")
def aktyvus_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        rows = cursor.execute(
            """
            SELECT u.username, u.imone, u.pareigybe, u.grupe, r.name, u.last_login
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.aktyvus=1
            ORDER BY u.imone, u.username
            """
        ).fetchall()
    else:
        rows = cursor.execute(
            """
            SELECT u.username, u.imone, u.pareigybe, u.grupe, r.name, u.last_login
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.aktyvus=1 AND u.imone=?
            ORDER BY u.username
            """,
            (request.session.get("imone"),),
        ).fetchall()
    data = [
        {
            "username": r[0],
            "imone": r[1],
            "pareigybe": r[2],
            "grupe": r[3],
            "role": r[4],
            "last_login": r[5] or "",
        }
        for r in rows
    ]
    return {"data": data}


@router.get("/api/aktyvus.csv")
def aktyvus_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    """Aktyvių naudotojų sąrašas CSV formatu."""
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        rows = cursor.execute(
            """
            SELECT u.username, u.imone, u.pareigybe, u.grupe, r.name, u.last_login
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.aktyvus=1
            ORDER BY u.imone, u.username
            """
        ).fetchall()
    else:
        rows = cursor.execute(
            """
            SELECT u.username, u.imone, u.pareigybe, u.grupe, r.name, u.last_login
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.aktyvus=1 AND u.imone=?
            ORDER BY u.username
            """,
            (request.session.get("imone"),),
        ).fetchall()
    df = pd.DataFrame(
        rows,
        columns=["username", "imone", "pareigybe", "grupe", "role", "last_login"],
    )
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=aktyvus.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


@router.get("/api/roles")
def roles_api(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    """Grąžina galimų rolių sąrašą."""
    conn, cursor = db
    cursor.execute("SELECT name FROM roles ORDER BY name")
    return {"data": [r[0] for r in cursor.fetchall()]}


@router.get("/api/roles.csv")
def roles_csv(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    """Rolių sąrašas CSV formatu."""
    conn, cursor = db
    cursor.execute("SELECT name FROM roles ORDER BY name")
    df = pd.DataFrame(cursor.fetchall(), columns=["name"])
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=roles.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


@router.get("/registracijos/{uid}/approve")
def registracijos_approve(
    uid: int,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    row = cursor.execute(
        "SELECT id, username, imone, vardas, pavarde, pareigybe, grupe FROM users WHERE id=? AND aktyvus=0",
        (uid,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    cursor.execute("UPDATE users SET aktyvus=1 WHERE id=?", (uid,))
    assign_role(conn, cursor, uid, Role.USER)
    cursor.execute(
        "INSERT INTO darbuotojai (vardas, pavarde, pareigybe, el_pastas, grupe, imone, aktyvus) VALUES (?,?,?,?,?,?,1)",
        (row[3], row[4], row[5], row[1], row[6], row[2]),
    )
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), "approve", "users", uid)
    log_action(
        conn,
        cursor,
        request.session.get("user_id"),
        "create",
        "darbuotojai",
        cursor.lastrowid,
    )
    return RedirectResponse("/registracijos", status_code=303)


@router.get("/registracijos/{uid}/approve-admin")
def registracijos_approve_admin(
    uid: int,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    row = cursor.execute(
        "SELECT id, username, imone, vardas, pavarde, pareigybe, grupe FROM users WHERE id=? AND aktyvus=0",
        (uid,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    cursor.execute("UPDATE users SET aktyvus=1 WHERE id=?", (uid,))
    assign_role(conn, cursor, uid, Role.COMPANY_ADMIN)
    cursor.execute(
        "INSERT INTO darbuotojai (vardas, pavarde, pareigybe, el_pastas, grupe, imone, aktyvus) VALUES (?,?,?,?,?,?,1)",
        (row[3], row[4], row[5], row[1], row[6], row[2]),
    )
    conn.commit()
    log_action(
        conn, cursor, request.session.get("user_id"), "approve_admin", "users", uid
    )
    log_action(
        conn,
        cursor,
        request.session.get("user_id"),
        "create_admin",
        "darbuotojai",
        cursor.lastrowid,
    )
    return RedirectResponse("/registracijos", status_code=303)


@router.get("/registracijos/{uid}/delete")
def registracijos_delete(
    uid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    cursor.execute("DELETE FROM users WHERE id=? AND aktyvus=0", (uid,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found")
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), "delete", "users", uid)
    return RedirectResponse("/registracijos", status_code=303)


