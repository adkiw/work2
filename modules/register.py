import streamlit as st

from .auth_utils import hash_password


def show(conn, c):
    st.subheader("Registracija")
    email = st.text_input("El. paštas")
    password = st.text_input("Slaptažodis", type="password")
    vardas = st.text_input("Vardas")
    pavarde = st.text_input("Pavardė")
    pareigybe = st.text_input("Pareigybė")
    imone = st.text_input("Įmonė")

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
                st.success("Registracija pateikta. Palaukite administratoriaus patvirtinimo.")
