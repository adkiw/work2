import os
import sqlite3
from modules import login, auth_utils
from modules.roles import Role
from tests.test_web_app import create_client


def test_update_user_roles(tmp_path):
    client = create_client(tmp_path)
    db_path = tmp_path / "app.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    pw = auth_utils.hash_password("pass")
    c.execute(
        "INSERT INTO users (username, password_hash, imone, aktyvus) VALUES (?,?,?,1)",
        ("u@a.com", pw, "A"),
    )
    uid = c.lastrowid
    conn.commit()
    conn.close()

    resp = client.post(f"/api/user-roles/{uid}", json={"roles": ["user"]})
    assert resp.status_code == 200

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        "SELECT r.name FROM user_roles ur JOIN roles r ON ur.role_id=r.id WHERE ur.user_id=?",
        (uid,),
    )
    roles = {r[0] for r in c.fetchall()}
    conn.close()
    assert roles == {"user"}


def test_user_roles_forbidden(tmp_path):
    client = create_client(tmp_path, do_login=False)
    db_path = tmp_path / "app.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    pw = auth_utils.hash_password("pass")
    c.execute(
        "INSERT INTO users (username, password_hash, imone, aktyvus) VALUES (?,?,?,1)",
        ("user1@a.com", pw, "A"),
    )
    uid1 = c.lastrowid
    login.assign_role(conn, c, uid1, Role.USER)
    c.execute(
        "INSERT INTO users (username, password_hash, imone, aktyvus) VALUES (?,?,?,1)",
        ("user2@a.com", pw, "A"),
    )
    uid2 = c.lastrowid
    conn.commit()
    conn.close()

    resp = client.post(
        "/login",
        data={"username": "user1@a.com", "password": "pass"},
        allow_redirects=False,
    )
    assert resp.status_code == 303

    resp = client.post(f"/api/user-roles/{uid2}", json={"roles": ["user"]})
    assert resp.status_code == 403
