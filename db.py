# db.py
import sqlite3
import os
from modules.auth_utils import hash_password

def init_db(db_path: str | None = None):
    """
    Inicializuoja SQLite duomenų bazę:
    • sukuria lenteles, jei jų dar nėra
    • grąžina (conn, cursor)
    """
    db_path = db_path or os.getenv("DB_PATH", "main.db")
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
            priekaba          TEXT,
            imone            TEXT
        )
    """)
    c.execute("PRAGMA table_info(vilkikai)")
    cols = [row[1] for row in c.fetchall()]
    if 'imone' not in cols:
        c.execute("ALTER TABLE vilkikai ADD COLUMN imone TEXT")
    conn.commit()

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
            imone     TEXT,
            aktyvus   INTEGER DEFAULT 1
        )
    """)
    c.execute("PRAGMA table_info(darbuotojai)")
    cols = [row[1] for row in c.fetchall()]
    if 'imone' not in cols:
        c.execute("ALTER TABLE darbuotojai ADD COLUMN imone TEXT")
    if 'aktyvus' not in cols:
        c.execute("ALTER TABLE darbuotojai ADD COLUMN aktyvus INTEGER DEFAULT 1")
    conn.commit()

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

    # ------------- Naudotojų autentikacija -------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            imone TEXT,
            aktyvus INTEGER DEFAULT 0
        )
    """)

    # If the table existed before, ensure the 'aktyvus' and 'imone' columns are present
    c.execute("PRAGMA table_info(users)")
    existing_cols = [row[1] for row in c.fetchall()]
    if "aktyvus" not in existing_cols:
        c.execute("ALTER TABLE users ADD COLUMN aktyvus INTEGER DEFAULT 0")
        conn.commit()
    if "imone" not in existing_cols:
        c.execute("ALTER TABLE users ADD COLUMN imone TEXT")
        conn.commit()

    c.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER,
            role_id INTEGER,
            PRIMARY KEY (user_id, role_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (role_id) REFERENCES roles(id)
        )
    """)

    conn.commit()

    # Sukuriame numatytąjį administratoriaus naudotoją, jei jo nėra
    c.execute("SELECT id FROM users WHERE username = 'admin'")
    row = c.fetchone()
    if not row:
        admin_hash = hash_password('admin')
        c.execute(
            "INSERT INTO users (username, password_hash, imone, aktyvus) VALUES (?, ?, ?, 1)",
            ('admin', admin_hash, 'Admin')
        )
        conn.commit()
        row = (c.lastrowid,)

    admin_user_id = row[0]

    # Užtikriname, kad egzistuotų "admin" rolė ir kad ji būtų priskirta adminui
    c.execute("SELECT id FROM roles WHERE name = 'admin'")
    r = c.fetchone()
    if not r:
        c.execute("INSERT INTO roles (name) VALUES ('admin')")
        conn.commit()
        role_id = c.lastrowid
    else:
        role_id = r[0]

    c.execute(
        "SELECT 1 FROM user_roles WHERE user_id = ? AND role_id = ?",
        (admin_user_id, role_id)
    )
    if not c.fetchone():
        c.execute(
            "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
            (admin_user_id, role_id)
        )
        conn.commit()

    return conn, c
