import streamlit as st
import pandas as pd
from . import login


def rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def show(conn, c):
    st.title("Naudotojų patvirtinimas")

    is_admin = login.has_role(conn, c, "admin")
    is_comp_admin = login.has_role(conn, c, "company_admin")

    if is_admin:
        df = pd.read_sql_query(
            "SELECT id, username, imone FROM users WHERE aktyvus = 0", conn
        )
    elif is_comp_admin:
        df = pd.read_sql_query(
            "SELECT id, username, imone FROM users WHERE aktyvus = 0 AND imone = ?",
            conn,
            params=(st.session_state.get("imone"),),
        )
    else:
        st.error("Neturite teisių")
        return

    if df.empty:
        st.info("Nėra laukiančių vartotojų")
        return

    for _, row in df.iterrows():
        if is_admin:
            cols = st.columns([4, 1, 1, 1])
        else:
            cols = st.columns([4, 1, 1])
        user_display = row['username']
        if row.get('imone'):
            user_display += f" ({row['imone']})"
        cols[0].write(user_display)
        if cols[1].button("Patvirtinti", key=f"approve_{row['id']}"):
            c.execute("UPDATE users SET aktyvus = 1 WHERE id = ?", (row['id'],))
            conn.commit()
            login.assign_role(conn, c, row['id'], "user")
            rerun()
        col_index = 2
        if is_admin:
            if cols[2].button("Patvirtinti kaip adminą", key=f"approve_admin_{row['id']}"):
                c.execute("UPDATE users SET aktyvus = 1 WHERE id = ?", (row['id'],))
                conn.commit()
                login.assign_role(conn, c, row['id'], "company_admin")
                rerun()
            col_index = 3
        if cols[col_index].button("Šalinti", key=f"delete_{row['id']}"):
            c.execute("DELETE FROM users WHERE id = ?", (row['id'],))
            conn.commit()
            rerun()
