import streamlit as st
import pandas as pd
from . import login
from .roles import Role


def rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def show(conn, c):
    st.title("Naudotojų patvirtinimas")

    is_admin = login.has_role(conn, c, Role.ADMIN)
    is_comp_admin = login.has_role(conn, c, Role.COMPANY_ADMIN)

    if is_admin:
        df = pd.read_sql_query(
            "SELECT id, username, imone, vardas, pavarde, pareigybe FROM users WHERE aktyvus = 0",
            conn,
        )
    elif is_comp_admin:
        df = pd.read_sql_query(
            "SELECT id, username, imone, vardas, pavarde, pareigybe FROM users WHERE aktyvus = 0 AND imone = ?",
            conn,
            params=(st.session_state.get("imone"),),
        )
    else:
        st.error("Neturite teisių")
        return

    if df.empty:
        st.info("Nėra laukiančių vartotojų")
    else:
        admin_domain = ""
        if is_comp_admin and "@" in st.session_state.get("username", ""):
            admin_domain = st.session_state["username"].split("@")[-1].lower()

        for _, row in df.iterrows():
            if is_admin:
                cols = st.columns([4, 1, 1, 1])
            else:
                cols = st.columns([4, 1, 1])

            user_display = f"{row.get('vardas','')} {row.get('pavarde','')} ({row['username']})"
            if row.get('imone'):
                user_display += f" ({row['imone']})"

            warn = False
            if admin_domain and "@" in row['username']:
                warn = row['username'].split("@")[-1].lower() != admin_domain

            if warn:
                cols[0].write(f"⚠️ {user_display}")
            else:
                cols[0].write(user_display)

            if cols[1].button("Patvirtinti", key=f"approve_{row['id']}"):
                c.execute("UPDATE users SET aktyvus = 1 WHERE id = ?", (row['id'],))
                conn.commit()
                login.assign_role(conn, c, row['id'], Role.USER)
                c.execute(
                    "INSERT INTO darbuotojai (vardas, pavarde, pareigybe, el_pastas, imone, aktyvus) VALUES (?,?,?,?,?,1)",
                    (
                        row.get('vardas'),
                        row.get('pavarde'),
                        row.get('pareigybe'),
                        row['username'],
                        row.get('imone'),
                    ),
                )
                conn.commit()
                rerun()
            col_index = 2
            if is_admin:
                if cols[2].button("Patvirtinti kaip adminą", key=f"approve_admin_{row['id']}"):
                    c.execute("UPDATE users SET aktyvus = 1 WHERE id = ?", (row['id'],))
                    conn.commit()
                    login.assign_role(conn, c, row['id'], Role.COMPANY_ADMIN)
                    c.execute(
                        "INSERT INTO darbuotojai (vardas, pavarde, pareigybe, el_pastas, imone, aktyvus) VALUES (?,?,?,?,?,1)",
                        (
                            row.get('vardas'),
                            row.get('pavarde'),
                            row.get('pareigybe'),
                            row['username'],
                            row.get('imone'),
                        ),
                    )
                    conn.commit()
                    rerun()
                col_index = 3
            if cols[col_index].button("Šalinti", key=f"delete_{row['id']}"):
                c.execute("DELETE FROM users WHERE id = ?", (row['id'],))
                conn.commit()
                rerun()

    st.markdown("---")
    st.subheader("Aktyvūs naudotojai")
    if is_admin:
        df_act = pd.read_sql_query(
            "SELECT username, imone, last_login FROM users WHERE aktyvus = 1 ORDER BY imone, username",
            conn,
        )
    else:
        df_act = pd.read_sql_query(
            "SELECT username, imone, last_login FROM users WHERE aktyvus = 1 AND imone = ? ORDER BY username",
            conn,
            params=(st.session_state.get("imone"),),
        )

    if df_act.empty:
        st.info("Nėra aktyvių naudotojų")
    else:
        for comp, grp in df_act.groupby("imone"):
            st.write(f"**{comp or 'Be įmonės'}**")
            display_df = grp[["username", "last_login"]].rename(columns={
                "username": "Vartotojas",
                "last_login": "Paskutinis prisijungimas",
            })
            st.table(display_df.fillna(""))

