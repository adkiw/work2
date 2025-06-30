from db import init_db
from modules import settings


def test_default_trailer_type_read_write(tmp_path):
    db_file = tmp_path / "s.db"
    conn, c = init_db(str(db_file))

    imone = "ACME"
    # ensure reading when none returns None
    assert settings.get_default_trailer_type(c, imone) is None

    settings.set_default_trailer_type(conn, c, imone, "Tent")
    assert settings.get_default_trailer_type(c, imone) == "Tent"

    # update value
    settings.set_default_trailer_type(conn, c, imone, "Kieta")
    assert settings.get_default_trailer_type(c, imone) == "Kieta"

    # clear value
    settings.set_default_trailer_type(conn, c, imone, None)
    assert settings.get_default_trailer_type(c, imone) is None

