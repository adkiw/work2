import streamlit as st

from .auth_utils import hash_password
from .audit import log_action


def rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def show(conn, c):
    st.subheader("Registracija")
    email = st.text_input("El. paštas", key="reg_email")
    password = st.text_input("Slaptažodis", type="password", key="reg_password")
    vardas = st.text_input("Vardas", key="reg_vardas")
    pavarde = st.text_input("Pavardė", key="reg_pavarde")
    pareigybe = st.text_input("Pareigybė", key="reg_pareigybe")
    imone = st.text_input("Įmonė", key="reg_imone")

    if st.button("Pateikti paraišką"):
        if not email or not password:
            st.error("Įveskite el. paštą ir slaptažodį")
        else:
            c.execute("SELECT 1 FROM users WHERE username = ?", (email,))
            if c.fetchone():
                st.error("Toks vartotojas jau egzistuoja")
            else:
                c.execute(
                    "INSERT INTO users (username, password_hash, imone, vardas, pavarde, pareigybe, aktyvus) VALUES (?, ?, ?, ?, ?, ?, 0)",
                    (
                        email,
                        hash_password(password),
                        imone or None,
                        vardas,
                        pavarde,
                        pareigybe,
                    ),
                )
                conn.commit()
                log_action(conn, c, None, "register", "users", c.lastrowid)
                st.session_state.registration_message = "Paraiška pateikta"
                for key in [
                    "reg_email",
                    "reg_password",
                    "reg_vardas",
                    "reg_pavarde",
                    "reg_pareigybe",
                    "reg_imone",
                ]:
                    st.session_state.pop(key, None)
                st.session_state.show_register = False
                rerun()

