from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

import os

import sqlite3
from typing import Generator
from db import init_db
from modules.audit import log_action, fetch_logs
from modules.login import assign_role, verify_user
from modules.auth_utils import hash_password
from modules.roles import Role
from modules.constants import EU_COUNTRIES

import datetime
from datetime import date
import pandas as pd

# Available employee roles for form select boxes
EMPLOYEE_ROLES = [
    "Ekspedicijos vadybininkas",
    "Transporto vadybininkas",
]

# Nationality options for driver forms
DRIVER_NATIONALITIES = ["LT", "BY", "UA", "UZ", "IN", "NG", "PL"]

app = FastAPI()


class AuthMiddleware(BaseHTTPMiddleware):
    """Redirect anonymous users to the login page."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/static") or path in {"/login", "/register", "/health"}:
            return await call_next(request)
        if not ensure_logged_in(request):
            return RedirectResponse("/login")
        return await call_next(request)


app.add_middleware(AuthMiddleware)

app.add_middleware(
    SessionMiddleware, secret_key=os.getenv("WEBAPP_SECRET", "devsecret")
)


def ensure_logged_in(request: Request) -> bool:
    """Return True if the current session is authenticated."""
    return bool(request.session.get("user_id"))


app.mount("/static", StaticFiles(directory="web_app/static"), name="static")
templates = Jinja2Templates(directory="web_app/templates")


@app.get("/api/eu-countries")
def eu_countries():
    """Grąžina Europos šalių sąrašą."""
    return {
        "data": [{"name": name, "code": code} for name, code in EU_COUNTRIES if name]
    }


@app.get("/api/eu-countries.csv")
def eu_countries_csv():
    """Grąžina Europos šalis CSV formatu."""
    df = pd.DataFrame([
        {"name": name, "code": code}
        for name, code in EU_COUNTRIES
        if name
    ])
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=eu-countries.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


def table_csv_response(cursor: sqlite3.Cursor, table: str, filename: str) -> Response:
    """Sukurti CSV atsakymą visos lentelės duomenims."""
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute(f"PRAGMA table_info({table})")]
    df = pd.DataFrame(rows, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


EXPECTED_KROVINIAI_COLUMNS = {
    "klientas": "TEXT",
    "uzsakymo_numeris": "TEXT",
    "pakrovimo_salis": "TEXT",
    "pakrovimo_regionas": "TEXT",
    "pakrovimo_miestas": "TEXT",
    "pakrovimo_adresas": "TEXT",
    "pakrovimo_data": "TEXT",
    "pakrovimo_laikas_nuo": "TEXT",
    "pakrovimo_laikas_iki": "TEXT",
    "iskrovimo_salis": "TEXT",
    "iskrovimo_regionas": "TEXT",
    "iskrovimo_miestas": "TEXT",
    "iskrovimo_adresas": "TEXT",
    "iskrovimo_data": "TEXT",
    "iskrovimo_laikas_nuo": "TEXT",
    "iskrovimo_laikas_iki": "TEXT",
    "vilkikas": "TEXT",
    "priekaba": "TEXT",
    "atsakingas_vadybininkas": "TEXT",
    "ekspedicijos_vadybininkas": "TEXT",
    "transporto_vadybininkas": "TEXT",
    "kilometrai": "INTEGER",
    "frachtas": "REAL",
    "svoris": "INTEGER",
    "paleciu_skaicius": "INTEGER",
    "saskaitos_busena": "TEXT",
    "busena": "TEXT",
    "imone": "TEXT",
}

EXPECTED_VILKIKAI_COLUMNS = {
    "numeris": "TEXT",
    "marke": "TEXT",
    "pagaminimo_metai": "INTEGER",
    "tech_apziura": "TEXT",
    "draudimas": "TEXT",
    "vadybininkas": "TEXT",
    "vairuotojai": "TEXT",
    "priekaba": "TEXT",
    "imone": "TEXT",
}

EXPECTED_PRIEKABOS_COLUMNS = {
    "priekabu_tipas": "TEXT",
    "numeris": "TEXT",
    "marke": "TEXT",
    "pagaminimo_metai": "TEXT",
    "tech_apziura": "TEXT",
    "draudimas": "TEXT",
    "imone": "TEXT",
}

EXPECTED_TRAILER_SPECS_COLUMNS = {
    "tipas": "TEXT",
    "ilgis": "REAL",
    "plotis": "REAL",
    "aukstis": "REAL",
    "keliamoji_galia": "REAL",
    "talpa": "REAL",
}

EXPECTED_VAIRUOTOJAI_COLUMNS = {
    "vardas": "TEXT",
    "pavarde": "TEXT",
    "gimimo_metai": "TEXT",
    "tautybe": "TEXT",
    "kadencijos_pabaiga": "TEXT",
    "atostogu_pabaiga": "TEXT",
    "imone": "TEXT",
}

EXPECTED_DARBUOTOJAI_COLUMNS = {
    "vardas": "TEXT",
    "pavarde": "TEXT",
    "pareigybe": "TEXT",
    "el_pastas": "TEXT",
    "telefonas": "TEXT",
    "grupe": "TEXT",
    "imone": "TEXT",
    "aktyvus": "INTEGER",
}

EXPECTED_GRUPES_COLUMNS = {
    "numeris": "TEXT",
    "pavadinimas": "TEXT",
    "aprasymas": "TEXT",
    "imone": "TEXT",
}

EXPECTED_GRUPIU_REGIONAI_COLUMNS = {
    "grupe_id": "INTEGER",
    "regiono_kodas": "TEXT",
}

EXPECTED_VILKIKU_DARBOLAikai_COLUMNS = {
    "vilkiko_numeris": "TEXT",
    "data": "TEXT",
    "darbo_laikas": "INTEGER",
    "likes_laikas": "INTEGER",
    "pakrovimo_statusas": "TEXT",
    "pakrovimo_laikas": "TEXT",
    "pakrovimo_data": "TEXT",
    "iskrovimo_statusas": "TEXT",
    "iskrovimo_laikas": "TEXT",
    "iskrovimo_data": "TEXT",
    "komentaras": "TEXT",
    "sa": "TEXT",
    "created_at": "TEXT",
    "ats_transporto_vadybininkas": "TEXT",
    "ats_ekspedicijos_vadybininkas": "TEXT",
    "trans_grupe": "TEXT",
    "eksp_grupe": "TEXT",
}

EXPECTED_KLIENTAI_COLUMNS = {
    "pavadinimas": "TEXT",
    "vat_numeris": "TEXT",
    "kontaktinis_asmuo": "TEXT",
    "kontaktinis_el_pastas": "TEXT",
    "kontaktinis_tel": "TEXT",
    "salis": "TEXT",
    "regionas": "TEXT",
    "miestas": "TEXT",
    "adresas": "TEXT",
    "saskaitos_asmuo": "TEXT",
    "saskaitos_el_pastas": "TEXT",
    "saskaitos_tel": "TEXT",
    "coface_limitas": "REAL",
    "musu_limitas": "REAL",
    "likes_limitas": "REAL",
    "imone": "TEXT",
}


def ensure_columns(conn: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
    """Ensure required columns exist for tables used by the web app."""
    tables = {
        "kroviniai": EXPECTED_KROVINIAI_COLUMNS,
        "vilkikai": EXPECTED_VILKIKAI_COLUMNS,
        "priekabos": EXPECTED_PRIEKABOS_COLUMNS,
        "trailer_specs": EXPECTED_TRAILER_SPECS_COLUMNS,
        "vairuotojai": EXPECTED_VAIRUOTOJAI_COLUMNS,
        "darbuotojai": EXPECTED_DARBUOTOJAI_COLUMNS,
        "grupes": EXPECTED_GRUPES_COLUMNS,
        "grupiu_regionai": EXPECTED_GRUPIU_REGIONAI_COLUMNS,
        "klientai": EXPECTED_KLIENTAI_COLUMNS,
        "vilkiku_darbo_laikai": EXPECTED_VILKIKU_DARBOLAikai_COLUMNS,
    }
    for table, cols in tables.items():
        cursor.execute(f"PRAGMA table_info({table})")
        existing = {r[1] for r in cursor.fetchall()}
        for col, typ in cols.items():
            if col not in existing:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
    conn.commit()


def compute_limits(
    cursor: sqlite3.Cursor, vat: str, coface: float
) -> tuple[float, float]:
    """Return (musu_limitas, likes_limitas) for given VAT."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='kroviniai'"
    )
    if cursor.fetchone():
        r = cursor.execute(
            """
            SELECT SUM(k.frachtas)
            FROM kroviniai AS k
            JOIN klientai AS cl ON k.klientas = cl.pavadinimas
            WHERE cl.vat_numeris = ? AND k.saskaitos_busena != 'Apmokėta'
            """,
            (vat,),
        ).fetchone()
        unpaid = r[0] if r and r[0] is not None else 0.0
    else:
        unpaid = 0.0
    musu = round(coface / 3.0, 2)
    liks = round(max(musu - unpaid, 0.0), 2)
    return musu, liks


def compute_busena(cursor: sqlite3.Cursor, row: dict) -> str:
    """Apskaičiuoti krovinio būseną pagal darbo laiko įrašus."""
    if not row.get("vilkikas"):
        return "Nesuplanuotas"
    query = (
        "SELECT pakrovimo_statusas, iskrovimo_statusas "
        "FROM vilkiku_darbo_laikai WHERE vilkiko_numeris=? AND data=? "
        "ORDER BY id DESC LIMIT 1"
    )
    r = cursor.execute(query, (row["vilkikas"], row["pakrovimo_data"])).fetchone()
    if not r:
        return "Suplanuotas"
    pk_status, ik_status = r
    if ik_status == "Iškrauta":
        return "Iškrauta"
    if ik_status == "Atvyko":
        return "Atvyko į iškrovimą"
    if ik_status == "Kita" and pk_status != "Pakrauta":
        return "Kita (iškrovimas)"
    if pk_status == "Pakrauta":
        return "Pakrauta"
    if pk_status == "Atvyko":
        return "Atvyko į pakrovimą"
    if pk_status == "Kita":
        return "Kita (pakrovimas)"
    return "Suplanuotas"


def user_has_role(request: Request, cursor: sqlite3.Cursor, role: Role) -> bool:
    """Check if current session user has the given role."""
    user_id = request.session.get("user_id")
    if not user_id:
        return False
    cursor.execute(
        """
        SELECT 1 FROM user_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.user_id = ? AND r.name = ?
        """,
        (user_id, role.value),
    )
    return cursor.fetchone() is not None


def require_roles(*roles: Role):
    """Dependency ensuring the current user has any of the given roles."""

    def wrapper(
        request: Request,
        db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    ) -> None:
        _, cursor = db
        if not any(user_has_role(request, cursor, role) for role in roles):
            raise HTTPException(status_code=403, detail="Forbidden")

    return wrapper


def get_db() -> Generator[tuple[sqlite3.Connection, sqlite3.Cursor], None, None]:
    conn, cursor = init_db()
    ensure_columns(conn, cursor)
    try:
        yield conn, cursor
    finally:
        conn.close()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/kroviniai", response_class=HTMLResponse)
def kroviniai_list(request: Request):
    return templates.TemplateResponse("kroviniai_list.html", {"request": request})


@app.get("/kroviniai/add", response_class=HTMLResponse)
def kroviniai_add_form(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        klientai = [
            r[0] for r in cursor.execute("SELECT pavadinimas FROM klientai").fetchall()
        ]
        vilkikai = [
            r[0] for r in cursor.execute("SELECT numeris FROM vilkikai").fetchall()
        ]
        eksped_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=?",
            ("Ekspedicijos vadybininkas",),
        ).fetchall()
    else:
        imone = request.session.get("imone", "")
        klientai = [
            r[0]
            for r in cursor.execute(
                "SELECT pavadinimas FROM klientai WHERE imone=?",
                (imone,),
            ).fetchall()
        ]
        vilkikai = [
            r[0]
            for r in cursor.execute(
                "SELECT numeris FROM vilkikai WHERE imone=?",
                (imone,),
            ).fetchall()
        ]
        eksped_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=? AND imone=?",
            ("Ekspedicijos vadybininkas", imone),
        ).fetchall()
    eksped = [f"{r[0]} {r[1]}" for r in eksped_rows]
    context = {
        "request": request,
        "data": {},
        "klientai": klientai,
        "vilkikai": vilkikai,
        "eksped_vadybininkai": eksped,
        "salys": EU_COUNTRIES,
        "imone": request.session.get("imone"),
    }
    return templates.TemplateResponse("kroviniai_form.html", context)


@app.get("/kroviniai/{cid}/edit", response_class=HTMLResponse)
def kroviniai_edit_form(
    cid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db

    row = cursor.execute("SELECT * FROM kroviniai WHERE id=?", (cid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(kroviniai)")]
    data = dict(zip(columns, row))
    if user_has_role(request, cursor, Role.ADMIN):
        klientai = [
            r[0] for r in cursor.execute("SELECT pavadinimas FROM klientai").fetchall()
        ]
        vilkikai = [
            r[0] for r in cursor.execute("SELECT numeris FROM vilkikai").fetchall()
        ]
        eksped_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=?",
            ("Ekspedicijos vadybininkas",),
        ).fetchall()
    else:
        imone = request.session.get("imone", "")
        klientai = [
            r[0]
            for r in cursor.execute(
                "SELECT pavadinimas FROM klientai WHERE imone=?",
                (imone,),
            ).fetchall()
        ]
        vilkikai = [
            r[0]
            for r in cursor.execute(
                "SELECT numeris FROM vilkikai WHERE imone=?",
                (imone,),
            ).fetchall()
        ]
        eksped_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=? AND imone=?",
            ("Ekspedicijos vadybininkas", imone),
        ).fetchall()
    eksped = [f"{r[0]} {r[1]}" for r in eksped_rows]
    context = {
        "request": request,
        "data": data,
        "klientai": klientai,
        "vilkikai": vilkikai,
        "eksped_vadybininkai": eksped,
        "salys": EU_COUNTRIES,
        "imone": request.session.get("imone"),
    }
    return templates.TemplateResponse("kroviniai_form.html", context)


@app.post("/kroviniai/save")
def kroviniai_save(
    request: Request,
    cid: int = Form(0),
    klientas: str = Form(...),
    vilkikas: str = Form(""),
    priekaba: str = Form(""),
    uzsakymo_numeris: str = Form(...),
    saskaitos_busena: str = Form("Neapmokėta"),
    pakrovimo_data: str = Form(...),
    iskrovimo_data: str = Form(...),
    pakrovimo_salis: str = Form(""),
    iskrovimo_salis: str = Form(""),
    pakrovimo_regionas: str = Form(""),
    iskrovimo_regionas: str = Form(""),
    pakrovimo_miestas: str = Form(""),
    iskrovimo_miestas: str = Form(""),
    pakrovimo_adresas: str = Form(""),
    iskrovimo_adresas: str = Form(""),
    pakrovimo_laikas_nuo: str = Form(""),
    pakrovimo_laikas_iki: str = Form(""),
    iskrovimo_laikas_nuo: str = Form(""),
    iskrovimo_laikas_iki: str = Form(""),
    kilometrai: int = Form(0),
    frachtas: float = Form(0.0),
    svoris: int = Form(0),
    paleciu_skaicius: int = Form(0),
    ekspedicijos_vadybininkas: str = Form(""),
    busena: str = Form("Nesuplanuotas"),
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if not imone:
        imone = request.session.get("imone")
    cols = [
        "klientas",
        "vilkikas",
        "priekaba",
        "uzsakymo_numeris",
        "saskaitos_busena",
        "pakrovimo_data",
        "iskrovimo_data",
        "pakrovimo_salis",
        "iskrovimo_salis",
        "pakrovimo_regionas",
        "iskrovimo_regionas",
        "pakrovimo_miestas",
        "iskrovimo_miestas",
        "pakrovimo_adresas",
        "iskrovimo_adresas",
        "pakrovimo_laikas_nuo",
        "pakrovimo_laikas_iki",
        "iskrovimo_laikas_nuo",
        "iskrovimo_laikas_iki",
        "kilometrai",
        "frachtas",
        "svoris",
        "paleciu_skaicius",
        "ekspedicijos_vadybininkas",
        "busena",
        "imone",
    ]
    vals = [
        klientas,
        vilkikas,
        priekaba,
        uzsakymo_numeris,
        saskaitos_busena,
        pakrovimo_data,
        iskrovimo_data,
        pakrovimo_salis,
        iskrovimo_salis,
        pakrovimo_regionas,
        iskrovimo_regionas,
        pakrovimo_miestas,
        iskrovimo_miestas,
        pakrovimo_adresas,
        iskrovimo_adresas,
        pakrovimo_laikas_nuo,
        pakrovimo_laikas_iki,
        iskrovimo_laikas_nuo,
        iskrovimo_laikas_iki,
        kilometrai,
        frachtas,
        svoris,
        paleciu_skaicius,
        ekspedicijos_vadybininkas,
        busena,
        imone,
    ]
    if cid:
        set_clause = ",".join([f"{c}=?" for c in cols])
        cursor.execute(
            f"UPDATE kroviniai SET {set_clause} WHERE id=?",
            vals + [cid],
        )
        action = "update"
    else:
        placeholders = ",".join(["?"] * len(cols))
        col_str = ",".join(cols)
        cursor.execute(
            f"INSERT INTO kroviniai ({col_str}) VALUES ({placeholders})",
            vals,
        )
        cid = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), action, "kroviniai", cid)
    return RedirectResponse(f"/kroviniai", status_code=303)


@app.get("/api/kroviniai")
def kroviniai_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM kroviniai")
    else:
        cursor.execute(
            "SELECT * FROM kroviniai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(kroviniai)")]
    data = [dict(zip(columns, row)) for row in rows]
    for d in data:
        d["busena"] = compute_busena(cursor, d)
    return {"data": data}


@app.get("/api/kroviniai.csv")
def kroviniai_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM kroviniai")
    else:
        cursor.execute(
            "SELECT * FROM kroviniai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(kroviniai)")]
    data = [dict(zip(columns, row)) for row in rows]
    for d in data:
        d["busena"] = compute_busena(cursor, d)
    df = pd.DataFrame(data, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=kroviniai.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


# ---- Planavimas ----


@app.get("/planavimas", response_class=HTMLResponse)
def planavimas_page(request: Request):
    return templates.TemplateResponse("planavimas.html", {"request": request})


@app.get("/api/planavimas")
def planavimas_api(
    request: Request,
    grupe: str | None = None,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=1)
    end_date = today + datetime.timedelta(days=14)
    date_list = [
        start_date + datetime.timedelta(days=i)
        for i in range((end_date - start_date).days + 1)
    ]
    date_strs = [d.isoformat() for d in date_list]

    is_admin = user_has_role(request, cursor, Role.ADMIN)
    # truck info
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
        return {"columns": ["Vilkikas"] + date_strs, "data": []}

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
                "SELECT regiono_kodas FROM grupiu_regionai WHERE grupe_id=?", (gid,)
            )
            regionai = [row[0] for row in cursor.fetchall()]
            if regionai:
                df = df[
                    df["vietos_kodas"].apply(
                        lambda x: any(x.startswith(r) for r in regionai)
                    )
                ]

    if df.empty:
        return {"columns": ["Vilkikas"] + date_strs, "data": []}

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

    df_last["cell_val"] = df_last.apply(
        lambda r: make_cell(r["vilkikas"], r["data"], r["vietos_kodas"]), axis=1
    )
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

    result = pivot_df.reset_index().to_dict(orient="records")
    return {"columns": ["Vilkikas"] + date_strs, "data": result}


@app.get("/vilkikai", response_class=HTMLResponse)
def vilkikai_list(request: Request):
    return templates.TemplateResponse("vilkikai_list.html", {"request": request})


@app.get("/vilkikai/add", response_class=HTMLResponse)
def vilkikai_add_form(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        trailers = [
            r[0] for r in cursor.execute("SELECT numeris FROM priekabos").fetchall()
        ]
        vair_rows = cursor.execute(
            "SELECT id, vardas, pavarde FROM vairuotojai"
        ).fetchall()
        vadyb_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=?",
            ("Transporto vadybininkas",),
        ).fetchall()
    else:
        imone = request.session.get("imone", "")
        trailers = [
            r[0]
            for r in cursor.execute(
                "SELECT numeris FROM priekabos WHERE imone=?",
                (imone,),
            ).fetchall()
        ]
        vair_rows = cursor.execute(
            "SELECT id, vardas, pavarde FROM vairuotojai WHERE imone=?",
            (imone,),
        ).fetchall()
        vadyb_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=? AND imone=?",
            ("Transporto vadybininkas", imone),
        ).fetchall()
    markes = [
        r[0]
        for r in cursor.execute(
            "SELECT reiksme FROM lookup WHERE kategorija='Markė'"
        ).fetchall()
    ]
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


@app.get("/vilkikai/{vid}/edit", response_class=HTMLResponse)
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
        trailers = [
            r[0] for r in cursor.execute("SELECT numeris FROM priekabos").fetchall()
        ]
        vair_rows = cursor.execute(
            "SELECT id, vardas, pavarde FROM vairuotojai"
        ).fetchall()
        vadyb_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=?",
            ("Transporto vadybininkas",),
        ).fetchall()
    else:
        imone = request.session.get("imone", "")
        trailers = [
            r[0]
            for r in cursor.execute(
                "SELECT numeris FROM priekabos WHERE imone=?",
                (imone,),
            ).fetchall()
        ]
        vair_rows = cursor.execute(
            "SELECT id, vardas, pavarde FROM vairuotojai WHERE imone=?",
            (imone,),
        ).fetchall()
        vadyb_rows = cursor.execute(
            "SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe=? AND imone=?",
            ("Transporto vadybininkas", imone),
        ).fetchall()
    markes = [
        r[0]
        for r in cursor.execute(
            "SELECT reiksme FROM lookup WHERE kategorija='Markė'"
        ).fetchall()
    ]
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


@app.post("/vilkikai/save")
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


@app.get("/api/vilkikai")
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


@app.get("/api/vilkikai.csv")
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


# ---- Priekabų priskyrimas ----


@app.get("/trailer-swap", response_class=HTMLResponse)
def trailer_swap_form(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    is_admin = user_has_role(request, cursor, Role.ADMIN)
    if is_admin:
        cursor.execute("SELECT numeris, priekaba FROM vilkikai ORDER BY numeris")
    else:
        cursor.execute(
            "SELECT numeris, priekaba FROM vilkikai WHERE imone=? ORDER BY numeris",
            (request.session.get("imone"),),
        )
    trucks = cursor.fetchall()
    if is_admin:
        cursor.execute("SELECT numeris FROM priekabos ORDER BY numeris")
    else:
        cursor.execute(
            "SELECT numeris FROM priekabos WHERE imone=? ORDER BY numeris",
            (request.session.get("imone"),),
        )
    trailers = [r[0] for r in cursor.fetchall()]
    trailer_info: list[tuple[str, str | None]] = []
    for num in trailers:
        if is_admin:
            cursor.execute(
                "SELECT numeris FROM vilkikai WHERE priekaba=?",
                (num,),
            )
        else:
            cursor.execute(
                "SELECT numeris FROM vilkikai WHERE priekaba=? AND imone=?",
                (num, request.session.get("imone")),
            )
        row = cursor.fetchone()
        assigned = row[0] if row and row[0] else None
        trailer_info.append((num, assigned))
    context = {
        "request": request,
        "trucks": trucks,
        "trailers": trailer_info,
    }
    return templates.TemplateResponse("trailer_swap.html", context)


@app.post("/trailer-swap")
def trailer_swap(
    request: Request,
    vilkikas: str = Form(...),
    priekaba: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    is_admin = user_has_role(request, cursor, Role.ADMIN)
    params = (vilkikas,) if is_admin else (vilkikas, request.session.get("imone"))
    cursor.execute(
        "SELECT id, priekaba FROM vilkikai WHERE numeris=?"
        + ("" if is_admin else " AND imone=?"),
        params,
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Vilkikas nerastas")
    vid, cur_trailer = row[0], row[1] or ""
    if priekaba:
        params2 = (priekaba,) if is_admin else (priekaba, request.session.get("imone"))
        cursor.execute(
            "SELECT id, numeris FROM vilkikai WHERE priekaba=?"
            + ("" if is_admin else " AND imone=?"),
            params2,
        )
        other = cursor.fetchone()
        other_id = other[0] if other else None
        other_num = other[1] if other else None
    else:
        other_id = None
        other_num = None

    if other_id and other_num != vilkikas:
        params3 = (
            (cur_trailer or "", other_num)
            if is_admin
            else (cur_trailer or "", other_num, request.session.get("imone"))
        )
        cursor.execute(
            "UPDATE vilkikai SET priekaba=? WHERE numeris=?"
            + ("" if is_admin else " AND imone=?"),
            params3,
        )
        log_action(
            conn, cursor, request.session.get("user_id"), "update", "vilkikai", other_id
        )

    params4 = (
        (priekaba or "", vilkikas)
        if is_admin
        else (priekaba or "", vilkikas, request.session.get("imone"))
    )
    cursor.execute(
        "UPDATE vilkikai SET priekaba=? WHERE numeris=?"
        + ("" if is_admin else " AND imone=?"),
        params4,
    )
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), "update", "vilkikai", vid)
    return RedirectResponse("/trailer-swap", status_code=303)


# ---- Priekabos ----


@app.get("/priekabos", response_class=HTMLResponse)
def priekabos_list(request: Request):
    return templates.TemplateResponse("priekabos_list.html", {"request": request})


@app.get("/priekabos/add", response_class=HTMLResponse)
def priekabos_add_form(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    imone = request.session.get("imone", "")
    cursor.execute(
        "SELECT reiksme FROM company_settings WHERE imone=? AND kategorija='Priekabos tipas' ORDER BY reiksme",
        (imone,),
    )
    rows = cursor.fetchall()
    if rows:
        tipai = [r[0] for r in rows]
    else:
        cursor.execute(
            "SELECT reiksme FROM lookup WHERE kategorija='Priekabos tipas' ORDER BY reiksme"
        )
        tipai = [r[0] for r in cursor.fetchall()]
    markes = [
        r[0]
        for r in cursor.execute(
            "SELECT reiksme FROM lookup WHERE kategorija='Markė'"
        ).fetchall()
    ]
    return templates.TemplateResponse(
        "priekabos_form.html",
        {"request": request, "data": {}, "tipai": tipai, "markes": markes},
    )


@app.get("/priekabos/{pid}/edit", response_class=HTMLResponse)
def priekabos_edit_form(
    pid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM priekabos WHERE id=?", (pid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(priekabos)")]
    data = dict(zip(columns, row))
    imone = request.session.get("imone", "")
    cursor.execute(
        "SELECT reiksme FROM company_settings WHERE imone=? AND kategorija='Priekabos tipas' ORDER BY reiksme",
        (imone,),
    )
    rows = cursor.fetchall()
    if rows:
        tipai = [r[0] for r in rows]
    else:
        cursor.execute(
            "SELECT reiksme FROM lookup WHERE kategorija='Priekabos tipas' ORDER BY reiksme"
        )
        tipai = [r[0] for r in cursor.fetchall()]
    markes = [
        r[0]
        for r in cursor.execute(
            "SELECT reiksme FROM lookup WHERE kategorija='Markė'"
        ).fetchall()
    ]
    return templates.TemplateResponse(
        "priekabos_form.html",
        {
            "request": request,
            "data": data,
            "tipai": tipai,
            "markes": markes,
        },
    )


@app.post("/priekabos/save")
def priekabos_save(
    request: Request,
    pid: int = Form(0),
    priekabu_tipas: str = Form(""),
    numeris: str = Form(...),
    marke: str = Form(""),
    pagaminimo_metai: str = Form(""),
    tech_apziura: str = Form(""),
    draudimas: str = Form(""),
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if pid:
        cursor.execute(
            "UPDATE priekabos SET priekabu_tipas=?, numeris=?, marke=?, pagaminimo_metai=?, tech_apziura=?, draudimas=?, imone=? WHERE id=?",
            (
                priekabu_tipas,
                numeris,
                marke,
                pagaminimo_metai,
                tech_apziura,
                draudimas,
                imone,
                pid,
            ),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO priekabos (priekabu_tipas, numeris, marke, pagaminimo_metai, tech_apziura, draudimas, imone) VALUES (?,?,?,?,?,?,?)",
            (
                priekabu_tipas,
                numeris,
                marke,
                pagaminimo_metai,
                tech_apziura,
                draudimas,
                imone,
            ),
        )
        pid = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), action, "priekabos", pid)
    return RedirectResponse("/priekabos", status_code=303)


@app.get("/api/priekabos")
def priekabos_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM priekabos")
    else:
        cursor.execute(
            "SELECT * FROM priekabos WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(priekabos)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@app.get("/api/priekabos.csv")
def priekabos_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM priekabos")
    else:
        cursor.execute(
            "SELECT * FROM priekabos WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(priekabos)")]
    df = pd.DataFrame(rows, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=priekabos.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


# ---- Vairuotojai ----


@app.get("/vairuotojai", response_class=HTMLResponse)
def vairuotojai_list(request: Request):
    return templates.TemplateResponse("vairuotojai_list.html", {"request": request})


@app.get("/vairuotojai/add", response_class=HTMLResponse)
def vairuotojai_add_form(request: Request):
    return templates.TemplateResponse(
        "vairuotojai_form.html",
        {
            "request": request,
            "data": {},
            "tautybes": DRIVER_NATIONALITIES,
        },
    )


@app.get("/vairuotojai/{did}/edit", response_class=HTMLResponse)
def vairuotojai_edit_form(
    did: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM vairuotojai WHERE id=?", (did,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(vairuotojai)")]
    data = dict(zip(columns, row))
    return templates.TemplateResponse(
        "vairuotojai_form.html",
        {
            "request": request,
            "data": data,
            "tautybes": DRIVER_NATIONALITIES,
        },
    )


@app.post("/vairuotojai/save")
def vairuotojai_save(
    request: Request,
    did: int = Form(0),
    vardas: str = Form(...),
    pavarde: str = Form(""),
    gimimo_metai: str = Form(""),
    tautybe: str = Form(""),
    kadencijos_pabaiga: str = Form(""),
    atostogu_pabaiga: str = Form(""),
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if did:
        cursor.execute(
            "UPDATE vairuotojai SET vardas=?, pavarde=?, gimimo_metai=?, tautybe=?, kadencijos_pabaiga=?, atostogu_pabaiga=?, imone=? WHERE id=?",
            (
                vardas,
                pavarde,
                gimimo_metai,
                tautybe,
                kadencijos_pabaiga,
                atostogu_pabaiga,
                imone,
                did,
            ),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO vairuotojai (vardas, pavarde, gimimo_metai, tautybe, kadencijos_pabaiga, atostogu_pabaiga, imone) VALUES (?,?,?,?,?,?,?)",
            (
                vardas,
                pavarde,
                gimimo_metai,
                tautybe,
                kadencijos_pabaiga,
                atostogu_pabaiga,
                imone,
            ),
        )
        did = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), action, "vairuotojai", did)
    return RedirectResponse("/vairuotojai", status_code=303)


@app.get("/api/vairuotojai")
def vairuotojai_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM vairuotojai")
    else:
        cursor.execute(
            "SELECT * FROM vairuotojai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(vairuotojai)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@app.get("/api/vairuotojai.csv")
def vairuotojai_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM vairuotojai")
    else:
        cursor.execute(
            "SELECT * FROM vairuotojai WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(vairuotojai)")]
    df = pd.DataFrame(rows, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=vairuotojai.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


# ---- Darbuotojai ----


@app.get("/darbuotojai", response_class=HTMLResponse)
def darbuotojai_list(request: Request):
    return templates.TemplateResponse("darbuotojai_list.html", {"request": request})


@app.get("/darbuotojai/add", response_class=HTMLResponse)
def darbuotojai_add_form(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    grupes = [r[0] for r in cursor.execute("SELECT numeris FROM grupes").fetchall()]
    return templates.TemplateResponse(
        "darbuotojai_form.html",
        {
            "request": request,
            "data": {},
            "roles": EMPLOYEE_ROLES,
            "grupes": grupes,
        },
    )


@app.get("/darbuotojai/{did}/edit", response_class=HTMLResponse)
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
    return templates.TemplateResponse(
        "darbuotojai_form.html",
        {
            "request": request,
            "data": data,
            "roles": EMPLOYEE_ROLES,
            "grupes": grupes,
        },
    )


@app.post("/darbuotojai/save")
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
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
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
    return RedirectResponse("/darbuotojai", status_code=303)


@app.get("/api/darbuotojai")
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


@app.get("/api/darbuotojai.csv")
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


# ---- Grupes ----


@app.get("/grupes", response_class=HTMLResponse)
def grupes_list(request: Request):
    return templates.TemplateResponse("grupes_list.html", {"request": request})


@app.get("/grupes/add", response_class=HTMLResponse)
def grupes_add_form(request: Request):
    return templates.TemplateResponse(
        "grupes_form.html", {"request": request, "data": {}}
    )


@app.get("/grupes/{gid}/edit", response_class=HTMLResponse)
def grupes_edit_form(
    gid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM grupes WHERE id=?", (gid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(grupes)")]
    data = dict(zip(columns, row))
    return templates.TemplateResponse(
        "grupes_form.html", {"request": request, "data": data}
    )


@app.post("/grupes/save")
def grupes_save(
    request: Request,
    gid: int = Form(0),
    numeris: str = Form(...),
    pavadinimas: str = Form(""),
    aprasymas: str = Form(""),
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if gid:
        cursor.execute(
            "UPDATE grupes SET numeris=?, pavadinimas=?, aprasymas=?, imone=? WHERE id=?",
            (numeris, pavadinimas, aprasymas, imone, gid),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO grupes (numeris, pavadinimas, aprasymas, imone) VALUES (?,?,?,?)",
            (numeris, pavadinimas, aprasymas, imone),
        )
        gid = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), action, "grupes", gid)
    return RedirectResponse("/grupes", status_code=303)


@app.get("/api/grupes")
def grupes_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM grupes")
    else:
        cursor.execute(
            "SELECT * FROM grupes WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(grupes)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@app.get("/api/grupes.csv")
def grupes_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute("SELECT * FROM grupes")
    else:
        cursor.execute(
            "SELECT * FROM grupes WHERE imone=?",
            (request.session.get("imone"),),
        )
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(grupes)")]
    df = pd.DataFrame(rows, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=grupes.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


# ---- Grupiu regionai ----


@app.get("/group-regions", response_class=HTMLResponse)
def group_regions_page(request: Request):
    return templates.TemplateResponse("group_regions.html", {"request": request})


@app.post("/group-regions/add")
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


@app.get("/group-regions/{rid}/delete")
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


@app.get("/api/group-regions")
def group_regions_api(
    gid: int, db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)
):
    conn, cursor = db
    cursor.execute(
        "SELECT id, regiono_kodas FROM grupiu_regionai WHERE grupe_id=? ORDER BY regiono_kodas",
        (gid,),
    )
    rows = cursor.fetchall()
    data = [{"id": r[0], "regiono_kodas": r[1]} for r in rows]
    return {"data": data}


@app.get("/api/group-regions.csv")
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


# ---- Klientai ----


@app.get("/klientai", response_class=HTMLResponse)
def klientai_list(request: Request):
    return templates.TemplateResponse("klientai_list.html", {"request": request})


@app.get("/klientai/add", response_class=HTMLResponse)
def klientai_add_form(request: Request):
    data = {"imone": request.session.get("imone", "")}
    return templates.TemplateResponse(
        "klientai_form.html",
        {"request": request, "data": data, "salys": EU_COUNTRIES},
    )


@app.get("/klientai/{cid}/edit", response_class=HTMLResponse)
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


@app.post("/klientai/save")
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


@app.get("/api/klientai")
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


@app.get("/api/klientai.csv")
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


# ---- Trailer types ----


@app.get("/trailer-types", response_class=HTMLResponse)
def trailer_types_list(
    request: Request,
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    return templates.TemplateResponse("trailer_types_list.html", {"request": request})


@app.get("/trailer-types/add", response_class=HTMLResponse)
def trailer_types_add_form(
    request: Request,
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    return templates.TemplateResponse(
        "trailer_types_form.html", {"request": request, "data": {}}
    )


@app.get("/trailer-types/{tid}/edit", response_class=HTMLResponse)
def trailer_types_edit_form(
    tid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        row = cursor.execute(
            "SELECT id, reiksme FROM lookup WHERE kategorija='Priekabos tipas' AND id=?",
            (tid,),
        ).fetchone()
    else:
        imone = request.session.get("imone", "")
        row = cursor.execute(
            "SELECT id, reiksme FROM company_settings WHERE kategorija='Priekabos tipas' AND id=? AND imone=?",
            (tid, imone),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    data = {"id": row[0], "reiksme": row[1]}
    return templates.TemplateResponse(
        "trailer_types_form.html", {"request": request, "data": data}
    )


@app.post("/trailer-types/save")
def trailer_types_save(
    request: Request,
    tid: int = Form(0),
    reiksme: str = Form(...),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        table = "lookup"
        if tid:
            cursor.execute(
                "UPDATE lookup SET reiksme=? WHERE id=? AND kategorija='Priekabos tipas'",
                (reiksme, tid),
            )
            action = "update"
        else:
            cursor.execute(
                "INSERT INTO lookup (kategorija, reiksme) VALUES ('Priekabos tipas', ?)",
                (reiksme,),
            )
            tid = cursor.lastrowid
            action = "insert"
    else:
        table = "company_settings"
        imone = request.session.get("imone", "")
        if tid:
            cursor.execute(
                "UPDATE company_settings SET reiksme=? WHERE id=?",
                (reiksme, tid),
            )
            action = "update"
        else:
            cursor.execute(
                "INSERT INTO company_settings (imone, kategorija, reiksme) VALUES (?,?,?)",
                (imone, "Priekabos tipas", reiksme),
            )
            tid = cursor.lastrowid
            action = "insert"
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), action, table, tid)
    return RedirectResponse("/trailer-types", status_code=303)


@app.get("/trailer-types/{tid}/delete")
def trailer_types_delete(
    tid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    """Ištrina priekabos tipą."""
    conn, cursor = db
    is_admin = user_has_role(request, cursor, Role.ADMIN)
    if is_admin:
        cursor.execute(
            "DELETE FROM lookup WHERE id=? AND kategorija='Priekabos tipas'",
            (tid,),
        )
        table = "lookup"
    else:
        imone = request.session.get("imone", "")
        cursor.execute(
            "DELETE FROM company_settings WHERE id=? AND imone=? AND kategorija='Priekabos tipas'",
            (tid, imone),
        )
        table = "company_settings"
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found")
    conn.commit()
    log_action(conn, cursor, request.session.get("user_id"), "delete", table, tid)
    return RedirectResponse("/trailer-types", status_code=303)


@app.get("/api/trailer-types")
def trailer_types_api(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        cursor.execute(
            "SELECT id, reiksme FROM lookup WHERE kategorija='Priekabos tipas'"
        )
    else:
        imone = request.session.get("imone", "")
        cursor.execute(
            "SELECT id, reiksme FROM company_settings WHERE imone=? AND kategorija='Priekabos tipas'",
            (imone,),
        )
    rows = cursor.fetchall()
    data = [{"id": r[0], "reiksme": r[1]} for r in rows]
    return {"data": data}


@app.get("/api/trailer-types.csv")
def trailer_types_csv(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        return table_csv_response(cursor, "lookup", "trailer-types.csv")
    imone = request.session.get("imone", "")
    cursor.execute(
        "SELECT id, reiksme FROM company_settings WHERE imone=? AND kategorija='Priekabos tipas'",
        (imone,),
    )
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=["id", "reiksme"])
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=trailer-types.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


# ---- Trailer specs ----


@app.get("/trailer-specs", response_class=HTMLResponse)
def trailer_specs_list(
    request: Request,
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    return templates.TemplateResponse("trailer_specs_list.html", {"request": request})


@app.get("/trailer-specs/add", response_class=HTMLResponse)
def trailer_specs_add_form(
    request: Request,
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    return templates.TemplateResponse(
        "trailer_specs_form.html", {"request": request, "data": {}}
    )


@app.get("/trailer-specs/{sid}/edit", response_class=HTMLResponse)
def trailer_specs_edit_form(
    sid: int,
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    conn, cursor = db
    row = cursor.execute("SELECT * FROM trailer_specs WHERE id=?", (sid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(trailer_specs)")]
    data = dict(zip(columns, row))
    return templates.TemplateResponse(
        "trailer_specs_form.html", {"request": request, "data": data}
    )


@app.post("/trailer-specs/save")
def trailer_specs_save(
    request: Request,
    sid: int = Form(0),
    tipas: str = Form(...),
    ilgis: float = Form(0.0),
    plotis: float = Form(0.0),
    aukstis: float = Form(0.0),
    keliamoji_galia: float = Form(0.0),
    talpa: float = Form(0.0),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    conn, cursor = db
    if sid:
        cursor.execute(
            "UPDATE trailer_specs SET tipas=?, ilgis=?, plotis=?, aukstis=?, keliamoji_galia=?, talpa=? WHERE id=?",
            (tipas, ilgis, plotis, aukstis, keliamoji_galia, talpa, sid),
        )
        action = "update"
    else:
        cursor.execute(
            "INSERT INTO trailer_specs (tipas, ilgis, plotis, aukstis, keliamoji_galia, talpa) VALUES (?,?,?,?,?,?)",
            (tipas, ilgis, plotis, aukstis, keliamoji_galia, talpa),
        )
        sid = cursor.lastrowid
        action = "insert"
    conn.commit()
    log_action(
        conn, cursor, request.session.get("user_id"), action, "trailer_specs", sid
    )
    return RedirectResponse("/trailer-specs", status_code=303)


@app.get("/api/trailer-specs")
def trailer_specs_api(
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    conn, cursor = db
    cursor.execute("SELECT * FROM trailer_specs")
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(trailer_specs)")]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@app.get("/api/trailer-specs.csv")
def trailer_specs_csv(
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    conn, cursor = db
    return table_csv_response(cursor, "trailer_specs", "trailer-specs.csv")


# ---- Settings ----


@app.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    return templates.TemplateResponse("settings.html", {"request": request})


@app.get("/api/default-trailer-types")
def default_trailer_types_api(
    imone: str = "",
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    conn, cursor = db
    cursor.execute(
        "SELECT reiksme FROM company_default_trailers WHERE imone=? ORDER BY priority",
        (imone,),
    )
    rows = cursor.fetchall()
    return {"data": [r[0] for r in rows]}


@app.get("/api/default-trailer-types.csv")
def default_trailer_types_csv(
    imone: str = "",
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    """Grąžina numatytuosius priekabų tipus CSV formatu."""
    conn, cursor = db
    cursor.execute(
        "SELECT reiksme FROM company_default_trailers WHERE imone=? ORDER BY priority",
        (imone,),
    )
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=["reiksme"])
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=default-trailer-types.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


@app.post("/settings/save")
async def settings_save(
    request: Request,
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN)),
):
    form = await request.form()
    values = form.getlist("values")
    conn, cursor = db
    cursor.execute("DELETE FROM company_default_trailers WHERE imone=?", (imone,))
    for pr, val in enumerate(values):
        cursor.execute(
            "INSERT INTO company_default_trailers (imone, reiksme, priority) VALUES (?,?,?)",
            (imone, val, pr),
        )
    conn.commit()
    log_action(
        conn,
        cursor,
        request.session.get("user_id"),
        "update",
        "company_default_trailers",
        0,
    )
    return RedirectResponse("/settings", status_code=303)


# ---- Registracijos ----


@app.get("/registracijos", response_class=HTMLResponse)
def registracijos_list(
    request: Request,
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    return templates.TemplateResponse("registracijos_list.html", {"request": request})


@app.get("/api/registracijos")
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


@app.get("/api/aktyvus")
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


@app.get("/api/aktyvus.csv")
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


@app.get("/api/roles")
def roles_api(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    """Grąžina galimų rolių sąrašą."""
    conn, cursor = db
    cursor.execute("SELECT name FROM roles ORDER BY name")
    return {"data": [r[0] for r in cursor.fetchall()]}


@app.get("/api/roles.csv")
def roles_csv(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    """Rolių sąrašas CSV formatu."""
    conn, cursor = db
    cursor.execute("SELECT name FROM roles ORDER BY name")
    df = pd.DataFrame(cursor.fetchall(), columns=["name"])
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=roles.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


@app.get("/registracijos/{uid}/approve")
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


@app.get("/registracijos/{uid}/approve-admin")
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


@app.get("/registracijos/{uid}/delete")
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


# ---- Audit log ----


@app.get("/audit", response_class=HTMLResponse)
def audit_list(
    request: Request,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        df = fetch_logs(conn, cursor)
    else:
        df = fetch_logs(conn, cursor, request.session.get("imone"))
    data = df.to_dict(orient="records")
    return templates.TemplateResponse(
        "audit_list.html", {"request": request, "logs": data}
    )


@app.get("/api/audit")
def audit_api(
    request: Request,
    user: str | None = None,
    table: str | None = None,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        df = fetch_logs(conn, cursor)
    else:
        df = fetch_logs(conn, cursor, request.session.get("imone"))
    if user:
        df = df[df["user"] == user]
    if table:
        df = df[df["table_name"] == table]
    data = df.to_dict(orient="records")
    return {"data": data}


@app.get("/api/audit.csv")
def audit_csv(
    request: Request,
    user: str | None = None,
    table: str | None = None,
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
    auth: None = Depends(require_roles(Role.ADMIN, Role.COMPANY_ADMIN)),
):
    conn, cursor = db
    if user_has_role(request, cursor, Role.ADMIN):
        df = fetch_logs(conn, cursor)
    else:
        df = fetch_logs(conn, cursor, request.session.get("imone"))
    if user:
        df = df[df["user"] == user]
    if table:
        df = df[df["table_name"] == table]
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=audit.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)


# ---- Updates ----


@app.get("/updates", response_class=HTMLResponse)
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


@app.get("/updates/add", response_class=HTMLResponse)
def updates_add_form(request: Request):
    return templates.TemplateResponse(
        "updates_form.html", {"request": request, "data": {}}
    )


@app.get("/api/shipments")
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


@app.get("/updates/{uid}/edit", response_class=HTMLResponse)
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


@app.get("/updates/ship/{sid}", response_class=HTMLResponse)
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


@app.post("/updates/save")
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


@app.get("/api/updates")
def updates_api(db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM vilkiku_darbo_laikai")
    rows = cursor.fetchall()
    columns = [
        col[1] for col in cursor.execute("PRAGMA table_info(vilkiku_darbo_laikai)")
    ]
    data = [dict(zip(columns, row)) for row in rows]
    return {"data": data}


@app.get("/api/updates.csv")
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


@app.get("/api/updates-range")
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


@app.get("/api/updates-range.csv")
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


# ---- Authentication ----


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    user_id, imone = verify_user(conn, cursor, username, password)
    if user_id:
        request.session["user_id"] = user_id
        request.session["username"] = username
        request.session["imone"] = imone
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Neteisingi prisijungimo duomenys"},
        status_code=400,
    )


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse(
        "register.html", {"request": request, "error": None, "msg": None}
    )


@app.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    vardas: str = Form(""),
    pavarde: str = Form(""),
    pareigybe: str = Form(""),
    grupe: str = Form(""),
    imone: str = Form(""),
    db: tuple[sqlite3.Connection, sqlite3.Cursor] = Depends(get_db),
):
    conn, cursor = db
    cursor.execute("SELECT 1 FROM users WHERE username=?", (username,))
    if cursor.fetchone():
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "error": "Toks vartotojas jau egzistuoja",
                "msg": None,
            },
            status_code=400,
        )
    pw_hash = hash_password(password)
    cursor.execute(
        "INSERT INTO users (username, password_hash, imone, vardas, pavarde, pareigybe, grupe, aktyvus) VALUES (?,?,?,?,?,?,?,0)",
        (username, pw_hash, imone or None, vardas, pavarde, pareigybe, grupe),
    )
    conn.commit()
    log_action(
        conn,
        cursor,
        request.session.get("user_id"),
        "register",
        "users",
        cursor.lastrowid,
    )
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "error": None, "msg": "Parai\u0161ka pateikta"},
    )


@app.get("/health")
def health():
    return {"status": "ok"}
