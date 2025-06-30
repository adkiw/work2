from db import init_db


def test_default_trailer_types_inserted(tmp_path):
    db_file = tmp_path / "dtr.db"
    conn, c = init_db(str(db_file))
    rows = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE kategorija='Priekabos tipas'"
    ).fetchall()]
    assert "Tautliner" in rows
    assert "Box" in rows
