import argparse
from datetime import date, timedelta
from db import init_db

PREFIX = "DEMO_"


def seed_data(conn, c):
    # Klientai
    clients = [
        {"pavadinimas": f"{PREFIX}Klientas1", "vat_numeris": "DEMO123", "salis": "Lietuva", "miestas": "Vilnius", "regionas": "", "imone": "DemoCo"},
        {"pavadinimas": f"{PREFIX}Klientas2", "vat_numeris": "DEMO456", "salis": "Latvija", "miestas": "Ryga", "regionas": "", "imone": "DemoCo"},
    ]
    for cl in clients:
        c.execute(
            "INSERT INTO klientai (pavadinimas, vat_numeris, salis, miestas, regionas, imone) VALUES (?,?,?,?,?,?)",
            (cl["pavadinimas"], cl["vat_numeris"], cl["salis"], cl["miestas"], cl["regionas"], cl["imone"]),
        )

    # Grupes
    groups = [
        ("DEMO_TR", "Demo Transporto", "", "DemoCo"),
        ("DEMO_EKSP", "Demo Ekspedicija", "", "DemoCo"),
    ]
    for num, pav, apr, im in groups:
        c.execute(
            "INSERT INTO grupes (numeris, pavadinimas, aprasymas, imone) VALUES (?,?,?,?)",
            (num, pav, apr, im),
        )
    conn.commit()

    # Grupiu regionai
    eksp_id = c.execute("SELECT id FROM grupes WHERE numeris=?", ("DEMO_EKSP",)).fetchone()[0]
    for region in ["LT01", "LV02", "PL03"]:
        c.execute(
            "INSERT INTO grupiu_regionai (grupe_id, regiono_kodas) VALUES (?,?)",
            (eksp_id, region),
        )

    # Darbuotojai
    workers = [
        ("Jonas", "Jonaitis", "Ekspedicijos vadybininkas", "demo1@example.com", "+37060000001", "DEMO_EKSP"),
        ("Petras", "Petraitis", "Transporto vadybininkas", "demo2@example.com", "+37060000002", "DEMO_TR"),
    ]
    for w in workers:
        c.execute(
            "INSERT INTO darbuotojai (vardas, pavarde, pareigybe, el_pastas, telefonas, grupe) VALUES (?,?,?,?,?,?)",
            w,
        )

    # Vairuotojai
    drivers = [
        ("Tomas", "Tomaitis", "1985", "LT", "", "", "DemoCo"),
        ("Andrius", "Andrejevas", "1990", "LV", "", "", "DemoCo"),
    ]
    for d in drivers:
        c.execute(
            "INSERT INTO vairuotojai (vardas, pavarde, gimimo_metai, tautybe, kadencijos_pabaiga, atostogu_pabaiga, imone) VALUES (?,?,?,?,?,?,?)",
            d,
        )

    # Vilkikai
    trucks = [
        ("DEMO_TRUCK1", "Volvo", 2018, date.today().isoformat(), workers[1][0] + " " + workers[1][1], "Tomas Tomaitis", ""),
        ("DEMO_TRUCK2", "Scania", 2017, date.today().isoformat(), workers[1][0] + " " + workers[1][1], "Andrius Andrejevas", ""),
    ]
    for t in trucks:
        c.execute(
            "INSERT INTO vilkikai (numeris, marke, pagaminimo_metai, tech_apziura, vadybininkas, vairuotojai, priekaba) VALUES (?,?,?,?,?,?,?)",
            t,
        )

    # Priekabos
    trailers = [
        ("Tentinė", "DEMO-T1", "Krone", 2018, date.today().isoformat(), "", date.today().isoformat()),
        ("Šaldytuvas", "DEMO-T2", "Schmitz", 2019, date.today().isoformat(), "", date.today().isoformat()),
    ]
    for tr in trailers:
        c.execute(
            "INSERT INTO priekabos (priekabu_tipas, numeris, marke, pagaminimo_metai, tech_apziura, priskirtas_vilkikas, draudimas) VALUES (?,?,?,?,?,?,?)",
            tr,
        )

    # Kroviniai
    shipments = [
        {
            "klientas": clients[0]["pavadinimas"],
            "uzsakymo_numeris": "DEMO_CARGO1",
            "pakrovimo_data": date.today().isoformat(),
            "iskrovimo_data": (date.today() + timedelta(days=2)).isoformat(),
            "kilometrai": 500,
            "frachtas": 1200.0,
            "busena": "Nesuplanuotas",
            "pakrovimo_salis": "Lietuva",
            "pakrovimo_regionas": "LT01",
            "iskrovimo_salis": "Lenkija",
            "iskrovimo_regionas": "PL03",
            "imone": "DemoCo",
        }
    ]
    for s in shipments:
        cols = ",".join(s.keys())
        placeholders = ",".join("?" for _ in s)
        c.execute(f"INSERT INTO kroviniai ({cols}) VALUES ({placeholders})", tuple(s.values()))

    conn.commit()


def clear_data(conn, c):
    tables = {
        "kroviniai": "uzsakymo_numeris",
        "vilkikai": "numeris",
        "priekabos": "numeris",
        "darbuotojai": "el_pastas",
        "vairuotojai": "vardas",
        "klientai": "pavadinimas",
        "grupes": "numeris",
    }
    for table, col in tables.items():
        c.execute(f"DELETE FROM {table} WHERE {col} LIKE ?", (f'{PREFIX}%',))
    c.execute(
        "DELETE FROM grupiu_regionai WHERE grupe_id IN (SELECT id FROM grupes WHERE numeris LIKE ?)",
        (f'{PREFIX}%',)
    )
    conn.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed or clear demo data")
    parser.add_argument("--clear", action="store_true", help="Remove demo entries")
    args = parser.parse_args()

    conn, c = init_db()
    if args.clear:
        clear_data(conn, c)
        print("Demo data removed")
    else:
        seed_data(conn, c)
        print("Demo data inserted")
