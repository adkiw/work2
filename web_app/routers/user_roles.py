from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from ..utils import get_db
from ..auth import require_roles
from modules.roles import Role
from modules.login import assign_role, get_user_roles

router = APIRouter()
templates = Jinja2Templates(directory="web_app/templates")


@router.get("/user-roles", response_class=HTMLResponse)
def user_roles_page(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    rows = cursor.execute("SELECT id, username FROM users ORDER BY username").fetchall()
    users = []
    for uid, username in rows:
        roles = get_user_roles(cursor, uid)
        users.append({"id": uid, "username": username, "roles": roles})
    return templates.TemplateResponse("user_roles.html", {"request": request, "users": users})


@router.get("/api/user-roles/{uid}")
def user_roles_get(
    uid: int,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    row = cursor.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    roles = get_user_roles(cursor, uid)
    return {"roles": roles}


@router.post("/api/user-roles/{uid}")
async def user_roles_post(
    request: Request,
    uid: int,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    row = cursor.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    data = await request.json()
    roles = data.get("roles", []) if isinstance(data, dict) else []
    cursor.execute("DELETE FROM user_roles WHERE user_id=?", (uid,))
    for r in roles:
        if r in Role._value2member_map_:
            assign_role(conn, cursor, uid, Role(r))
    conn.commit()
    return {"status": "ok"}
