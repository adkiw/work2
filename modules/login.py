import streamlit as st
import hashlib


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_user(conn, c, username: str, password: str):
    c.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    if row and row[1] == hash_password(password):
        return row[0]
    return None


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
            st.session_state.clear()
            st.experimental_rerun()
    else:
        st.sidebar.subheader("Prisijungimas")
        username = st.sidebar.text_input("Vartotojas")
        password = st.sidebar.text_input("Slaptažodis", type="password")
        if st.sidebar.button("Prisijungti"):
            user_id = verify_user(conn, c, username, password)
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.experimental_rerun()
            else:
                st.sidebar.error("Neteisingi prisijungimo duomenys")

