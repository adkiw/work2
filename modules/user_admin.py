import streamlit as st
import pandas as pd
from . import login
from .roles import Role
from .audit import log_action
from .utils import rerun


def show(conn, c):
    st.title("Naudotojų patvirtinimas")

    is_admin = login.has_role(conn, c, Role.ADMIN)
    is_comp_admin = login.has_role(conn, c, Role.COMPANY_ADMIN)

    st.markdown(
        """
        <style>
          .scroll-container {
            overflow-x: auto;
          }
          table {
            border-collapse: collapse;
            width: 100%;
            white-space: nowrap;
          }
          th, td {
            border: 1px solid #ddd;
            padding: 4px;
            vertical-align: top;
            text-align: center;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if is_admin:
        df = pd.read_sql_query(
            "SELECT id, username, imone, vardas, pavarde, pareigybe, grupe FROM users WHERE aktyvus = 0",
            conn,
        )
    elif is_comp_admin:
        df = pd.read_sql_query(
            "SELECT id, username, imone, vardas, pavarde, pareigybe, grupe FROM users WHERE aktyvus = 0 AND imone = ?",
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
            check_domain = admin_domain
            if is_admin and row.get('imone'):
                c.execute(
                    """
                    SELECT u.username FROM users u
                    JOIN user_roles ur ON ur.user_id = u.id
                    JOIN roles r ON ur.role_id = r.id
                    WHERE r.name = ? AND u.imone = ? AND u.aktyvus = 1
                    LIMIT 1
                    """,
                    (Role.COMPANY_ADMIN.value, row['imone']),
                )
                r_admin = c.fetchone()
                if r_admin and "@" in r_admin[0]:
                    check_domain = r_admin[0].split("@")[-1].lower()

            if check_domain and "@" in row['username']:
                warn = row['username'].split("@")[-1].lower() != check_domain

            if warn:
                cols[0].write(f"⚠️ {user_display}")
            else:
                cols[0].write(user_display)

            if cols[1].button("Patvirtinti", key=f"approve_{row['id']}"):
                if warn:
                    st.error(
                        "Vartotojo el. pašto domenas nesutampa su įmonės domenu."
                    )
                else:
                    c.execute("UPDATE users SET aktyvus = 1 WHERE id = ?", (row['id'],))
                    conn.commit()
                    log_action(conn, c, st.session_state.get('user_id'), 'approve', 'users', row['id'])
                    login.assign_role(conn, c, row['id'], Role.USER)
                    c.execute(
                        "INSERT INTO darbuotojai (vardas, pavarde, pareigybe, el_pastas, grupe, imone, aktyvus) VALUES (?,?,?,?,?,?,1)",
                        (
                            row.get('vardas'),
                            row.get('pavarde'),
                            row.get('pareigybe'),
                            row['username'],
                            row.get('grupe'),
                            row.get('imone'),
                        ),
                    )
                    conn.commit()
                    log_action(conn, c, st.session_state.get('user_id'), 'create', 'darbuotojai', c.lastrowid)
                    rerun()
            col_index = 2
            if is_admin:
                if cols[2].button("Patvirtinti kaip adminą", key=f"approve_admin_{row['id']}"):
                    if warn:
                        st.error(
                            "Vartotojo el. pašto domenas nesutampa su įmonės domenu."
                        )
                    else:
                        c.execute("UPDATE users SET aktyvus = 1 WHERE id = ?", (row['id'],))
                        conn.commit()
                        log_action(conn, c, st.session_state.get('user_id'), 'approve_admin', 'users', row['id'])
                        login.assign_role(conn, c, row['id'], Role.COMPANY_ADMIN)
                        c.execute(
                            "INSERT INTO darbuotojai (vardas, pavarde, pareigybe, el_pastas, grupe, imone, aktyvus) VALUES (?,?,?,?,?,?,1)",
                            (
                                row.get('vardas'),
                                row.get('pavarde'),
                                row.get('pareigybe'),
                                row['username'],
                                row.get('grupe'),
                                row.get('imone'),
                            ),
                        )
                        conn.commit()
                        log_action(conn, c, st.session_state.get('user_id'), 'create_admin', 'darbuotojai', c.lastrowid)
                        rerun()
                col_index = 3
            if cols[col_index].button("Šalinti", key=f"delete_{row['id']}"):
                c.execute("DELETE FROM users WHERE id = ?", (row['id'],))
                conn.commit()
                log_action(conn, c, st.session_state.get('user_id'), 'delete', 'users', row['id'])
                rerun()

    st.markdown("---")
    st.subheader("Aktyvūs naudotojai")
    if is_admin:
        df_act = pd.read_sql_query(
            """
            SELECT u.username, u.imone, u.pareigybe, r.name as role, u.last_login
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.aktyvus = 1
            ORDER BY u.imone, u.username
            """,
            conn,
        )
    else:
        df_act = pd.read_sql_query(
            """
            SELECT u.username, u.imone, u.pareigybe, r.name as role, u.last_login
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.aktyvus = 1 AND u.imone = ?
            ORDER BY u.username
            """,
            conn,
            params=(st.session_state.get("imone"),),
        )

    if df_act.empty:
        st.info("Nėra aktyvių naudotojų")
    else:
        for comp, grp in df_act.groupby("imone"):
            st.write(f"**{comp or 'Be įmonės'}**")
            display_df = grp[["username", "pareigybe", "role", "last_login"]].rename(
                columns={
                    "username": "Vartotojas",
                    "pareigybe": "Pareigybė",
                    "role": "Rolė",
                    "last_login": "Paskutinis prisijungimas",
                }
            )
            st.table(display_df.fillna(""))

