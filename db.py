# db.py
import sqlite3
import os
from modules.auth_utils import hash_password
from modules.roles import Role

# Default expedition group definitions
def _range_codes(prefix: str, start: int, end: int, width: int = 2) -> list[str]:
    """Helper to generate codes like FR01..FR99."""
    return [f"{prefix}{i:0{width}}" for i in range(start, end + 1)]


DEFAULT_EXP_GROUPS: dict[str, list[str]] = {
    "1": [
        "FR02",
        "FR08",
        "FR10",
        "FR21",
        "FR27",
        "FR28",
        "FR45",
        "FR51",
        "FR54",
        "FR55",
        "FR57",
        "FR59",
        "FR60",
        "FR62",
        "FR67",
        "FR68",
        "FR70",
        "FR75",
        "FR76",
        "FR77",
        "FR78",
        "FR80",
        "FR88",
        "FR89",
        "FR90",
        "FR91",
        "FR92",
        "FR93",
        "FR94",
        "FR95",
        "FR52",
        *_range_codes("BE", 1, 99),
        *_range_codes("NL", 1, 99),
        *(f"LU{i}" for i in range(1, 11)),
    ],
    "2": [
        *_range_codes("IT", 0, 99),
        *_range_codes("SL", 1, 99),
        "FR13",
        "FR83",
        "FR06",
        "FR04",
        "FR05",
        "FR84",
        *_range_codes("CH", 1, 99),
    ],
    "3": [
        "FR50",
        "FR14",
        "FR61",
        "FR72",
        "FR53",
        "FR35",
        "FR22",
        "FR29",
        "FR56",
        "FR44",
        "FR49",
        "FR85",
        "FR79",
        "FR17",
        "FR41",
        "FR37",
        "FR36",
        "FR18",
        "FR86",
        "FR16",
        "FR87",
        "FR24",
        "FR19",
        "FR46",
        "FR15",
        "FR12",
        "FR48",
        "FR58",
        "FR71",
        "FR03",
        "FR63",
        "FR23",
        *_range_codes("GB", 1, 99),
        "FR25",
        "FR39",
        "FR01",
        "FR69",
        "FR42",
        "FR74",
        "FR73",
        "FR38",
        "FR26",
        "FR07",
        "FR30",
        "FR43",
    ],
    "4": [
        *_range_codes("ES", 0, 99),
        "FR40",
        "FR64",
        "FR65",
        "FR09",
        "FR11",
        "FR66",
        "FR34",
        "FR33",
        "FR47",
        "FR32",
        "FR82",
        "FR31",
        "FR81",
    ],
    "5": [
        *_range_codes("DE", 1, 98),
        *_range_codes("AT", 10, 99),
        *_range_codes("CZ", 10, 99),
        *_range_codes("PL", 1, 99),
        *_range_codes("HU", 1, 99),
        *_range_codes("SI", 1, 99),  # Slovenia
        *_range_codes("SL", 1, 99),
        *_range_codes("DK", 1, 99),
        *(f"SK{i}" for i in range(1, 11)),
    ],
}


def _setup_default_exp_groups(conn: sqlite3.Connection, c: sqlite3.Cursor) -> None:
    """Insert default expedition groups and regions if they are missing."""
    for num, codes in DEFAULT_EXP_GROUPS.items():
        c.execute(
            "SELECT id FROM grupes WHERE numeris=? AND imone IS NULL",
            (num,),
        )
        row = c.fetchone()
        if row:
            gid = row[0]
        else:
            c.execute(
                "INSERT INTO grupes (numeris, pavadinimas, aprasymas, imone) "
                "VALUES (?,?,?,NULL)",
                (num, "", ""),
            )
            gid = c.lastrowid

        for code in codes:
            code = code.upper()
            c.execute(
                "SELECT 1 FROM grupiu_regionai WHERE grupe_id=? AND regiono_kodas=?",
                (gid, code),
            )
            if not c.fetchone():
                c.execute(
                    "INSERT INTO grupiu_regionai (grupe_id, regiono_kodas, vadybininkas_id) VALUES (?,?,NULL)",
                    (gid, code),
                )
    conn.commit()

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
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS lookup (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kategorija TEXT,
            reiksme    TEXT,
            UNIQUE (kategorija, reiksme)
        )
        """
    )
    # Migrate from old schema with UNIQUE(reiksme) if needed
    idx_list = c.execute("PRAGMA index_list(lookup)").fetchall()
    has_composite = False
    needs_migration = False
    for _, idx_name, unique, *_ in idx_list:
        if unique:
            cols_info = [row[2] for row in c.execute(f"PRAGMA index_info({idx_name})")]
            if cols_info == ["kategorija", "reiksme"]:
                has_composite = True
            if cols_info == ["reiksme"]:
                needs_migration = True

    if needs_migration and not has_composite:
        c.execute("ALTER TABLE lookup RENAME TO lookup_old")
        c.execute(
            """
            CREATE TABLE lookup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kategorija TEXT,
                reiksme    TEXT,
                UNIQUE (kategorija, reiksme)
            )
            """
        )
        c.execute(
            "INSERT OR IGNORE INTO lookup (id, kategorija, reiksme) SELECT id, kategorija, reiksme FROM lookup_old"
        )
        c.execute("DROP TABLE lookup_old")

        conn.commit()

    # Default trailer types
    trailer_types = [
        "Van",
        "Tautliner",
        "Box",
        "Open",
        "Trax Walking Floor",
        "Coil",
        "Jumbo Trailer",
        "Mega Trailer",
        "Isothermic",
        "Refrigerated",
        "Freezer",
        "Multi Temperature",
        "Flat",
        "Lowloader",
        "Public Works Tiper",
        "Cereal Tippers",
        "Steel Through",
        "Armoured Through",
        "Palletable Bulk Carrier",
        "Walking Floor",
        "Liquid Tank",
        "Pulverulent Tank",
        "Container 20 feet",
        "Container 40 feet",
        "Container 45 feet",
    ]
    for t in trailer_types:
        c.execute(
            "INSERT OR IGNORE INTO lookup (kategorija, reiksme) VALUES (?, ?)",
            ("Priekabos tipas", t),
        )
    conn.commit()

    # Per-įmonės nustatymų lentelė
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS company_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imone TEXT,
            kategorija TEXT,
            reiksme TEXT,
            UNIQUE (imone, kategorija, reiksme)
        )
        """
    )

    # Defaults for trailer types per company with explicit ordering
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS company_default_trailers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imone TEXT,
            reiksme TEXT,
            priority INTEGER,
            UNIQUE(imone, priority)
        )
        """
    )
    # Add priority column if running on an older DB version
    c.execute("PRAGMA table_info(company_default_trailers)")
    cols = [row[1] for row in c.fetchall()]
    if "priority" not in cols:
        c.execute("ALTER TABLE company_default_trailers ADD COLUMN priority INTEGER")
    conn.commit()

    # Migrate single default stored in company_settings if present
    rows = c.execute(
        "SELECT imone, reiksme FROM company_settings WHERE kategorija=?",
        ("Numatytas priekabos tipas",),
    ).fetchall()
    for imone, reiksme in rows:
        c.execute(
            "INSERT OR IGNORE INTO company_default_trailers (imone, reiksme, priority) VALUES (?,?,0)",
            (imone, reiksme),
        )
    if rows:
        c.execute(
            "DELETE FROM company_settings WHERE kategorija=?",
            ("Numatytas priekabos tipas",),
        )
    conn.commit()

    # ------------- Pagrindinės lentelės -------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS klientai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pavadinimas TEXT,
            kontaktai   TEXT,
            salis       TEXT,
            miestas     TEXT,
            regionas    TEXT,
            vat_numeris TEXT,
            imone       TEXT
        )
    """)
    c.execute("PRAGMA table_info(klientai)")
    cols = [row[1] for row in c.fetchall()]
    if 'imone' not in cols:
        c.execute("ALTER TABLE klientai ADD COLUMN imone TEXT")
    conn.commit()

    c.execute("""
        CREATE TABLE IF NOT EXISTS kroviniai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            klientas          TEXT,
            uzsakymo_numeris  TEXT,
            pakrovimo_data    TEXT,
            iskrovimo_data    TEXT,
            kilometrai        INTEGER,
            frachtas          REAL,
            busena            TEXT,
            imone            TEXT
        )
    """)
    c.execute("PRAGMA table_info(kroviniai)")
    cols = [row[1] for row in c.fetchall()]
    if 'imone' not in cols:
        c.execute("ALTER TABLE kroviniai ADD COLUMN imone TEXT")
    conn.commit()

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
    c.execute("PRAGMA table_info(priekabos)")
    cols = [row[1] for row in c.fetchall()]
    if 'imone' not in cols:
        c.execute("ALTER TABLE priekabos ADD COLUMN imone TEXT")
    conn.commit()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS trailer_specs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipas TEXT UNIQUE,
            ilgis REAL,
            plotis REAL,
            aukstis REAL,
            keliamoji_galia REAL,
            talpa REAL
        )
        """
    )
    conn.commit()

    c.execute("""
        CREATE TABLE IF NOT EXISTS grupes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numeris     TEXT,
            pavadinimas TEXT,
            aprasymas   TEXT,
            imone       TEXT,
            UNIQUE (numeris, imone)
        )
    """)
    c.execute("PRAGMA table_info(grupes)")
    cols = [row[1] for row in c.fetchall()]
    if 'imone' not in cols:
        c.execute("ALTER TABLE grupes ADD COLUMN imone TEXT")
        conn.commit()

    # Jei lentelė sukurta su unikalia 'numeris' reikšme (be 'imone'), atliekame migraciją
    idx_list = c.execute("PRAGMA index_list(grupes)").fetchall()
    for _, idx_name, unique, *_ in idx_list:
        if unique:
            cols_info = [row[2] for row in c.execute(f"PRAGMA index_info({idx_name})")]
            if cols_info == ["numeris"]:
                c.execute("ALTER TABLE grupes RENAME TO grupes_old")
                c.execute("""
                    CREATE TABLE grupes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        numeris     TEXT,
                        pavadinimas TEXT,
                        aprasymas   TEXT,
                        imone       TEXT,
                        UNIQUE (numeris, imone)
                    )
                """)
                c.execute(
                    "INSERT INTO grupes (id, numeris, pavadinimas, aprasymas, imone) "
                    "SELECT id, numeris, pavadinimas, aprasymas, imone FROM grupes_old"
                )
                c.execute("DROP TABLE grupes_old")
                conn.commit()
                break

    # Regionų priskyrimas grupėms (naudoja grupes.py)
    c.execute("""
        CREATE TABLE IF NOT EXISTS grupiu_regionai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupe_id      INTEGER NOT NULL,
            regiono_kodas TEXT NOT NULL,
            vadybininkas_id INTEGER,
            FOREIGN KEY (grupe_id) REFERENCES grupes(id)
        )
    """)
    c.execute("PRAGMA table_info(grupiu_regionai)")
    cols = [row[1] for row in c.fetchall()]
    if "vadybininkas_id" not in cols:
        c.execute("ALTER TABLE grupiu_regionai ADD COLUMN vadybininkas_id INTEGER")
        conn.commit()

    # Insert default expedition groups and their regions
    _setup_default_exp_groups(conn, c)

    c.execute("""
        CREATE TABLE IF NOT EXISTS vairuotojai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vardas            TEXT,
            pavarde           TEXT,
            gimimo_metai      TEXT,
            tautybe           TEXT,
            kadencijos_pabaiga TEXT,
            atostogu_pabaiga   TEXT,
            imone             TEXT
        )
    """)
    c.execute("PRAGMA table_info(vairuotojai)")
    cols = [row[1] for row in c.fetchall()]
    if 'imone' not in cols:
        c.execute("ALTER TABLE vairuotojai ADD COLUMN imone TEXT")
    conn.commit()

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
            username   TEXT UNIQUE,
            password_hash TEXT,
            imone      TEXT,
            vardas     TEXT,
            pavarde    TEXT,
            pareigybe  TEXT,
            grupe      TEXT,
            aktyvus    INTEGER DEFAULT 0,
            last_login TEXT
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
    if "vardas" not in existing_cols:
        c.execute("ALTER TABLE users ADD COLUMN vardas TEXT")
        conn.commit()
    if "pavarde" not in existing_cols:
        c.execute("ALTER TABLE users ADD COLUMN pavarde TEXT")
        conn.commit()
    if "pareigybe" not in existing_cols:
        c.execute("ALTER TABLE users ADD COLUMN pareigybe TEXT")
        conn.commit()
    if "grupe" not in existing_cols:
        c.execute("ALTER TABLE users ADD COLUMN grupe TEXT")
        conn.commit()
    if "last_login" not in existing_cols:
        c.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
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

    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            table_name TEXT,
            record_id INTEGER,
            timestamp TEXT,
            details TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()

    # Sukuriame numatytąjį administratoriaus naudotoją, jei jo nėra
    # Insert the default admin user if it doesn't exist yet. Using
    # ``INSERT OR IGNORE`` avoids ``IntegrityError`` when multiple
    # ``init_db`` calls race to create the account.
    admin_hash = hash_password("admin")
    c.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, imone, aktyvus) VALUES (?, ?, ?, 1)",
        ("admin", admin_hash, "Admin"),
    )
    conn.commit()
    c.execute("SELECT id FROM users WHERE username = 'admin'")
    row = c.fetchone()
    admin_user_id = row[0]

    # Užtikriname, kad egzistuotų būtinos rolės
    required_roles = [Role.ADMIN, Role.COMPANY_ADMIN, Role.USER]
    role_ids = {}
    for role in required_roles:
        r_name = role.value
        c.execute("SELECT id FROM roles WHERE name = ?", (r_name,))
        row_role = c.fetchone()
        if not row_role:
            c.execute("INSERT INTO roles (name) VALUES (?)", (r_name,))
            conn.commit()
            role_ids[r_name] = c.lastrowid
        else:
            role_ids[r_name] = row_role[0]

    # Užtikriname, kad admin gautų ADMIN rolę
    c.execute(
        "SELECT 1 FROM user_roles WHERE user_id = ? AND role_id = ?",
        (admin_user_id, role_ids[Role.ADMIN.value])
    )
    if not c.fetchone():
        c.execute(
            "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
            (admin_user_id, role_ids[Role.ADMIN.value])
        )
        conn.commit()

    return conn, c
