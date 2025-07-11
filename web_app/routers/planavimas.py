from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

import sqlite3
from db import init_db
from modules.audit import log_action, fetch_logs
from modules.login import assign_role
from modules.roles import Role
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

# ---- Planavimas ----


def _compute_planavimas(cursor, request: Request, grupe: str | None):
    """Sukuria pivot lentelę planavimui."""
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=1)
    end_date = today + datetime.timedelta(days=14)
    date_list = [start_date + datetime.timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    date_strs = [d.isoformat() for d in date_list]

    is_admin = user_has_role(request, cursor, Role.ADMIN)
    if is_admin:
        cursor.execute("SELECT numeris, priekaba, vadybininkas FROM vilkikai")
    else:
        cursor.execute(
            "SELECT numeris, priekaba, vadybininkas FROM vilkikai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    priekaba_map = {r[0]: (r[1] or "") for r in rows}
    vadybininkas_map = {r[0]: (r[2] or "") for r in rows}

    query = (
        "SELECT vilkikas, iskrovimo_salis AS salis, iskrovimo_regionas AS regionas, "
        "date(iskrovimo_data) AS data, date(pakrovimo_data) AS pak_data "
        "FROM kroviniai WHERE date(iskrovimo_data) BETWEEN ? AND ? "
        "AND iskrovimo_data IS NOT NULL"
    )
    params = [start_date.isoformat(), end_date.isoformat()]
    if not is_admin:
        query += " AND imone=?"
        params.append(request.session.get("imone"))
    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = ["vilkikas", "salis", "regionas", "data", "pak_data"]
    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        empty = pd.DataFrame([], columns=["Vilkikas"] + date_strs)
        return empty, date_strs

    df["salis"] = df["salis"].fillna("").astype(str)
    df["regionas"] = df["regionas"].fillna("").astype(str)
    df["data"] = pd.to_datetime(df["data"]).dt.date.astype(str)
    df["pak_data"] = pd.to_datetime(df["pak_data"]).dt.date.astype(str)
    df["vietos_kodas"] = df["salis"] + df["regionas"]

    if grupe:
        cursor.execute("SELECT id FROM grupes WHERE numeris=?", (grupe,))
        r = cursor.fetchone()
        if r:
            gid = r[0]
            cursor.execute(
                "SELECT regiono_kodas FROM grupiu_regionai WHERE grupe_id=?",
                (gid,),
            )
            regionai = [row[0] for row in cursor.fetchall()]
            if regionai:
                df = df[df["vietos_kodas"].apply(lambda x: any(x.startswith(r) for r in regionai))]

    if df.empty:
        empty = pd.DataFrame([], columns=["Vilkikas"] + date_strs)
        return empty, date_strs

    df_last = df.loc[df.groupby("vilkikas")["data"].idxmax()].copy()

    papildomi_map = {}
    for _, row in df_last.iterrows():
        v = row["vilkikas"]
        pak_d = row["pak_data"]
        rc = cursor.execute(
            "SELECT iskrovimo_laikas, darbo_laikas, likes_laikas FROM vilkiku_darbo_laikai "
            "WHERE vilkiko_numeris=? AND data=? ORDER BY id DESC LIMIT 1",
            (v, pak_d),
        ).fetchone()
        if rc:
            ikr_laikas, bdl, ldl = rc
        else:
            ikr_laikas = bdl = ldl = None
        ikr_laikas = "" if ikr_laikas is None else str(ikr_laikas)
        bdl = "" if bdl is None else str(bdl)
        ldl = "" if ldl is None else str(ldl)
        papildomi_map[(v, row["data"])] = {
            "ikr_laikas": ikr_laikas,
            "bdl": bdl,
            "ldl": ldl,
        }

    def make_cell(vilk, iskr_data, vieta):
        if not vieta:
            return ""
        info = papildomi_map.get((vilk, iskr_data), {})
        parts = [
            vieta,
            info.get("ikr_laikas", "--") or "--",
            info.get("bdl", "--") or "--",
            info.get("ldl", "--") or "--",
        ]
        return " ".join(parts)

    df_last["cell_val"] = df_last.apply(lambda r: make_cell(r["vilkikas"], r["data"], r["vietos_kodas"]), axis=1)
    pivot_df = df_last.pivot(index="vilkikas", columns="data", values="cell_val")
    pivot_df = pivot_df.reindex(columns=date_strs, fill_value="")
    pivot_df = pivot_df.reindex(index=df_last["vilkikas"].unique(), fill_value="")

    sa_map = {}
    for v in pivot_df.index:
        pak_d = df_last.loc[df_last["vilkikas"] == v, "pak_data"].values[0]
        row = cursor.execute(
            "SELECT sa FROM vilkiku_darbo_laikai WHERE vilkiko_numeris=? AND data=? ORDER BY id DESC LIMIT 1",
            (v, pak_d),
        ).fetchone()
        sa_map[v] = row[0] if row and row[0] is not None else ""

    combined_index = []
    for v in pivot_df.index:
        priek = priekaba_map.get(v, "")
        vad = vadybininkas_map.get(v, "")
        sa = sa_map.get(v, "")
        label = v
        if priek:
            label += f"/{priek}"
        if vad:
            label += f" {vad}"
        if sa:
            label += f" {sa}"
        combined_index.append(label)

    pivot_df.index = combined_index
    pivot_df.index.name = "Vilkikas"
    pivot_df = pivot_df.fillna("")
    return pivot_df, date_strs


@router.get("/planavimas", response_class=HTMLResponse)
def planavimas_page(request: Request):
    return templates.TemplateResponse("planavimas.html", {"request": request})


@router.get("/api/planavimas")
def planavimas_api(
    request: Request,
    grupe: str | None = None,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    pivot_df, date_strs = _compute_planavimas(cursor, request, grupe)
    result = pivot_df.reset_index().to_dict(orient="records")
    return {"columns": ["Vilkikas"] + date_strs, "data": result}


@router.get("/api/planavimas.csv")
def planavimas_csv(
    request: Request,
    grupe: str | None = None,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    pivot_df, date_strs = _compute_planavimas(cursor, request, grupe)
    csv_data = pivot_df.reset_index().to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=planavimas.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)

