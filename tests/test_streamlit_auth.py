from db import init_db
from modules import login, auth_utils
from modules.roles import Role


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


def test_roles_and_assignment(tmp_path):
    db_file = tmp_path / "roles.db"
    conn, c = init_db(str(db_file))

    # Roles table should contain predefined roles
    c.execute("SELECT name FROM roles")
    roles = {row[0] for row in c.fetchall()}
    expected = {r.value for r in [Role.ADMIN, Role.COMPANY_ADMIN, Role.USER]}
    assert expected.issubset(roles)

    # Create user and assign role
    pw_hash = auth_utils.hash_password("pass")
    c.execute(
        "INSERT INTO users (username, password_hash, imone, aktyvus) VALUES (?,?,?,1)",
        ("boss", pw_hash, "ACME"),
    )
    user_id = c.lastrowid
    login.assign_role(conn, c, user_id, Role.COMPANY_ADMIN)

    c.execute(
        "SELECT 1 FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id=? AND r.name=?",
        (user_id, Role.COMPANY_ADMIN.value),
    )
    assert c.fetchone() is not None
