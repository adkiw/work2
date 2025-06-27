from db import init_db
from modules import login, auth_utils


def test_admin_login(tmp_path):
    db_file = tmp_path / "t.db"
    conn, c = init_db(str(db_file))
    user_id, imone = login.verify_user(conn, c, "admin", "admin")
    assert user_id is not None
    assert imone == "Admin"
    user_id2, _ = login.verify_user(conn, c, "admin", "wrong")
    assert user_id2 is None


def test_user_registration_flow(tmp_path):
    db_file = tmp_path / "r.db"
    conn, c = init_db(str(db_file))
    pw_hash = auth_utils.hash_password("pass123")
    c.execute(
        "INSERT INTO users (username, password_hash, imone, aktyvus) VALUES (?, ?, ?, 1)",
        ("user", pw_hash, "Comp"),
    )
    conn.commit()
    user_id, _ = login.verify_user(conn, c, "user", "pass123")
    assert user_id is not None
    bad, _ = login.verify_user(conn, c, "user", "bad")
    assert bad is None
