# db.py
import sqlite3

def init_db(db_path: str = "main.db"):
    """
    Inicializuoja SQLite duomenų bazę:
    • sukuria lenteles, jei jų dar nėra
    • grąžina (conn, cursor)
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    c    = conn.cursor()

    # ------------- Pagalbinė lentelė -------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS lookup (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kategorija TEXT,
            reiksme    TEXT UNIQUE
        )
    """)

    # ------------- Pagrindinės lentelės -------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS klientai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pavadinimas TEXT,
            kontaktai   TEXT,
            salis       TEXT,
            miestas     TEXT,
            regionas    TEXT,
            vat_numeris TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS kroviniai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            klientas          TEXT,
            uzsakymo_numeris  TEXT,
            pakrovimo_data    TEXT,
            iskrovimo_data    TEXT,
            kilometrai        INTEGER,
            frachtas          REAL,
            busena            TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS vilkikai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numeris           TEXT UNIQUE,
            marke             TEXT,
            pagaminimo_metai  INTEGER,
            tech_apziura      DATE,
            vadybininkas      TEXT,
            vairuotojai       TEXT,
            priekaba          TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS priekabos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            priekabu_tipas    TEXT,
            numeris           TEXT UNIQUE,
            marke             TEXT,
            pagaminimo_metai  INTEGER,
            tech_apziura      DATE,
            priskirtas_vilkikas TEXT,
            draudimas         DATE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS grupes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numeris     TEXT UNIQUE,
            pavadinimas TEXT,
            aprasymas   TEXT
        )
    """)

    # Regionų priskyrimas grupėms (naudoja grupes.py)
    c.execute("""
        CREATE TABLE IF NOT EXISTS grupiu_regionai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupe_id      INTEGER NOT NULL,
            regiono_kodas TEXT NOT NULL,
            FOREIGN KEY (grupe_id) REFERENCES grupes(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS vairuotojai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vardas            TEXT,
            pavarde           TEXT,
            gimimo_metai      TEXT,
            tautybe           TEXT,
            kadencijos_pabaiga TEXT,
            atostogu_pabaiga   TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS darbuotojai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vardas    TEXT,
            pavarde   TEXT,
            pareigybe TEXT,
            el_pastas TEXT,
            telefonas TEXT,
            grupe     TEXT,
            aktyvus   INTEGER DEFAULT 1
        )
    """)

    # Vilkikų darbo laiko lentelė (naudojama update.py & planavimas.py)
    c.execute("""
        CREATE TABLE IF NOT EXISTS vilkiku_darbo_laikai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vilkiko_numeris TEXT,
            data           TEXT,
            darbo_laikas   INTEGER,
            likes_laikas   INTEGER
        )
    """)

    conn.commit()
    return conn, c
