from .roles import Role
import bcrypt


def assign_role(conn, c, user_id: int, role: Role) -> None:
    """Ensure the role exists and assign it to the given user."""
    role_name = role.value
    c.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO roles (name) VALUES (?)", (role_name,))
        conn.commit()
        role_id = c.lastrowid
    else:
        role_id = row[0]

    c.execute(
        "SELECT 1 FROM user_roles WHERE user_id = ? AND role_id = ?",
        (user_id, role_id),
    )
    if not c.fetchone():
        c.execute(
            "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
            (user_id, role_id),
        )
        conn.commit()

def verify_user(conn, c, username: str, password: str):
    c.execute(
        "SELECT id, password_hash, imone FROM users WHERE username = ? AND aktyvus = 1",
        (username,)
    )
    row = c.fetchone()
    if row and bcrypt.checkpw(password.encode(), row[1].encode()):
        from datetime import datetime
        ts = datetime.utcnow().replace(second=0, microsecond=0).isoformat(timespec="minutes")
        c.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (ts, row[0]),
        )
        conn.commit()
        return row[0], row[2]
    return (None, None)


def get_user_roles(c, user_id: int) -> list[str]:
    """Grąžina vartotojui priskirtų rolių sąrašą."""
    c.execute(
        """
        SELECT r.name FROM user_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.user_id = ?
        """,
        (user_id,),
    )
    return [row[0] for row in c.fetchall()]




