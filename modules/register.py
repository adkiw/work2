import streamlit as st

from .login import hash_password


def show(conn, c):
    st.subheader("Registracija")
    username = st.text_input("Vartotojo vardas")
    password = st.text_input("Slaptažodis", type="password")

    if st.button("Pateikti paraišką"):
        if not username or not password:
            st.error("Įveskite vartotojo vardą ir slaptažodį")
        else:
            c.execute("SELECT 1 FROM users WHERE username = ?", (username,))
            if c.fetchone():
                st.error("Toks vartotojas jau egzistuoja")
            else:
                c.execute(
                    "INSERT INTO users (username, password_hash, aktyvus) VALUES (?, ?, 0)",
                    (username, hash_password(password)),
                )
                conn.commit()
                st.success("Registracija pateikta. Palaukite administratoriaus patvirtinimo.")
