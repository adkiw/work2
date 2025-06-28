import streamlit as st


def rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

from .auth_utils import hash_password
import bcrypt


def assign_role(conn, c, user_id: int, role: str) -> None:
    """Ensure the role exists and assign it to the given user."""
    c.execute("SELECT id FROM roles WHERE name = ?", (role,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO roles (name) VALUES (?)", (role,))
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
        return row[0], row[2]
    return (None, None)


def has_role(conn, c, role: str) -> bool:
    if "user_id" not in st.session_state:
        return False
    user_id = st.session_state.user_id
    c.execute(
        """
        SELECT 1 FROM user_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.user_id = ? AND r.name = ?
        """,
        (user_id, role),
    )
    return c.fetchone() is not None


def show(conn, c):
    """Renders login/logout interface in the sidebar."""
    if "user_id" in st.session_state:
        st.sidebar.success(f"Prisijungta kaip {st.session_state.username}")
        if st.sidebar.button("Atsijungti"):
            # Avoid Streamlit bug when using `clear()` directly
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            rerun()
    else:
        if st.session_state.get("show_register"):
            from . import register
            register.show(conn, c)
            if st.sidebar.button("Grįžti"):
                st.session_state.show_register = False
                rerun()
            return

        st.sidebar.subheader("Prisijungimas")
        username = st.sidebar.text_input("Vartotojas")
        password = st.sidebar.text_input("Slaptažodis", type="password")
        if st.sidebar.button("Prisijungti"):
            user_id, imone = verify_user(conn, c, username, password)
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.session_state.imone = imone
                rerun()
            else:
                st.sidebar.error("Neteisingi prisijungimo duomenys")
        if st.sidebar.button("Registruotis"):
            st.session_state.show_register = True
            rerun()

