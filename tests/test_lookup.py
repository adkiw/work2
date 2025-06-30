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
    conn.commit()
    c.execute(
        "SELECT reiksme FROM lookup WHERE kategorija=? AND reiksme=?",
        ("Priekabos tipas", "TestTipas"),
    )
    assert c.fetchone() is not None
