from db import init_db
from modules import settings


def test_default_trailer_types_read_write(tmp_path):
    db_file = tmp_path / "s.db"
    conn, c = init_db(str(db_file))

    imone = "ACME"
    assert settings.get_default_trailer_types(c, imone) == []

    settings.set_default_trailer_types(conn, c, imone, ["Tent", "Box"])
    assert settings.get_default_trailer_types(c, imone) == ["Tent", "Box"]

    settings.set_default_trailer_types(conn, c, imone, ["Mega"])
    assert settings.get_default_trailer_types(c, imone) == ["Mega"]

    settings.set_default_trailer_types(conn, c, imone, [])
    assert settings.get_default_trailer_types(c, imone) == []


def test_default_trailer_types_order(tmp_path):
    db_file = tmp_path / "o.db"
    conn, c = init_db(str(db_file))

    imone = "B"
    vals = ["Box", "Tent", "Mega"]
    settings.set_default_trailer_types(conn, c, imone, vals)
    assert settings.get_default_trailer_types(c, imone) == vals

