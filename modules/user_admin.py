import streamlit as st
import pandas as pd


def rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def show(conn, c):
    st.title("Naudotojų patvirtinimas")
    df = pd.read_sql_query("SELECT id, username FROM users WHERE aktyvus = 0", conn)

    if df.empty:
        st.info("Nėra laukiančių vartotojų")
        return

    for _, row in df.iterrows():
        cols = st.columns([3, 1, 1])
        cols[0].write(row['username'])
        if cols[1].button("Patvirtinti", key=f"approve_{row['id']}"):
            c.execute("UPDATE users SET aktyvus = 1 WHERE id = ?", (row['id'],))
            conn.commit()
            rerun()
        if cols[2].button("Šalinti", key=f"delete_{row['id']}"):
            c.execute("DELETE FROM users WHERE id = ?", (row['id'],))
            conn.commit()
            rerun()
