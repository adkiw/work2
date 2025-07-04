from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
import sqlite3
import pandas as pd

from ..utils import get_db
from ..auth import require_roles
from modules.roles import Role

router = APIRouter()
templates = Jinja2Templates(directory="web_app/templates")

@router.get("/roles", response_class=HTMLResponse)
def roles_list(request: Request, auth: None = Depends(require_roles(Role.ADMIN))):
    """Rolių sąrašo puslapis."""
    return templates.TemplateResponse("roles_list.html", {"request": request})


@router.get("/api/roles-full")
def roles_api(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    """Grąžina rolių sąrašą JSON formatu."""
    conn, cursor = db
    rows = cursor.execute("SELECT id, name FROM roles ORDER BY id").fetchall()
    return {"data": [{"id": r[0], "name": r[1]} for r in rows]}


@router.get("/api/roles.csv")
def roles_csv(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    """Rolių sąrašas CSV formatu."""
    conn, cursor = db
    rows = cursor.execute("SELECT id, name FROM roles ORDER BY id").fetchall()
    df = pd.DataFrame(rows, columns=["id", "name"])
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=roles.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)
