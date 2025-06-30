from db import init_db


def test_lookup_table_and_insert(tmp_path):
    db_file = tmp_path / "l.db"
    conn, c = init_db(str(db_file))
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lookup'")
    assert c.fetchone() is not None
    c.execute(
        "INSERT INTO lookup (kategorija, reiksme) VALUES (?, ?)",
        ("Priekabos tipas", "TestTipas"),
    )
    c.execute(
        "INSERT INTO lookup (kategorija, reiksme) VALUES (?, ?)",
        ("Markė", "TestTipas"),
    )
    conn.commit()
    c.execute("SELECT COUNT(*) FROM lookup WHERE reiksme=?", ("TestTipas",))
    assert c.fetchone()[0] == 2

    import pytest, sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        c.execute(
            "INSERT INTO lookup (kategorija, reiksme) VALUES (?, ?)",
            ("Priekabos tipas", "TestTipas"),
        )
