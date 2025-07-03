import sqlite3
from typing import Generator
import pandas as pd
from db import init_db

# Column definitions copied from the original monolithic app
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


def compute_limits(cursor: sqlite3.Cursor, vat: str, coface: float) -> tuple[float, float]:
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


def table_csv_response(cursor: sqlite3.Cursor, table: str, filename: str) -> pd.DataFrame:
    """Return a Response with the entire table as CSV."""
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    columns = [col[1] for col in cursor.execute(f"PRAGMA table_info({table})")]
    df = pd.DataFrame(rows, columns=columns)
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    from fastapi.responses import Response

    return Response(content=csv_data, media_type="text/csv", headers=headers)


def get_db() -> Generator[tuple[sqlite3.Connection, sqlite3.Cursor], None, None]:
    conn, cursor = init_db()
    ensure_columns(conn, cursor)
    try:
        yield conn, cursor
    finally:
        conn.close()
