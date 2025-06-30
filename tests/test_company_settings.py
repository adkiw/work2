from db import init_db


def test_company_settings_table(tmp_path):
    db_file = tmp_path / "cs.db"
    conn, c = init_db(str(db_file))
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='company_settings'")
    assert c.fetchone() is not None
    c.execute(
        "INSERT INTO company_settings (imone, kategorija, reiksme) VALUES (?,?,?)",
        ("ACME", "Priekabos tipas", "Spec"),
    )
    conn.commit()
    import pytest, sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        c.execute(
            "INSERT INTO company_settings (imone, kategorija, reiksme) VALUES (?,?,?)",
            ("ACME", "Priekabos tipas", "Spec"),
        )
