# modules/vairuotojai.py
import streamlit as st
import pandas as pd
from datetime import date
from . import login
from .roles import Role
from .utils import rerun, title_with_add, display_table_with_edit

# ---------- Konstantos ----------
TAUTYBES = [
    ("", ""),  # „visi“ filtruojant
    ("Lietuva", "LT"),
    ("Baltarusija", "BY"),
    ("Ukraina", "UA"),
    ("Uzbekistanas", "UZ"),
    ("Indija", "IN"),
    ("Nigerija", "NG"),
    ("Lenkija", "PL"),
]

# ---------- Helperiai ----------
def _ensure_columns(c, conn):
    """Įsitikina, kad lentelėje 'vairuotojai' yra visi reikalingi stulpeliai."""
    existing = {r[1] for r in c.execute("PRAGMA table_info(vairuotojai)").fetchall()}
    needed = {
        "vardas": "TEXT",
        "pavarde": "TEXT",
        "gimimo_metai": "TEXT",
        "tautybe": "TEXT",
        "kadencijos_pabaiga": "TEXT",
        "atostogu_pabaiga": "TEXT",
        "imone": "TEXT",
    }
    for col, typ in needed.items():
        if col not in existing:
            c.execute(f"ALTER TABLE vairuotojai ADD COLUMN {col} {typ}")
    conn.commit()


def _driver_to_vilkik_map(c, is_admin):
    """Grąžina vardas pavardė → vilkiko numeris žemėlapį (str:str)."""
    result = {}
    if is_admin:
        rows = c.execute("SELECT numeris, vairuotojai FROM vilkikai").fetchall()
    else:
        rows = c.execute(
            "SELECT numeris, vairuotojai FROM vilkikai WHERE imone = ?",
            (st.session_state.get('imone'),),
        ).fetchall()
    for numeris, drv_str in rows:
        if drv_str:
            for fn in drv_str.split(", "):
                result[fn] = numeris
    return result


def _text_filter(field, placeholder):
    """Grąžina tekstinio filtro reikšmę (stateful)."""
    return st.text_input("", placeholder=placeholder, key=f"flt_{field}")


# ---------- Main ----------
def show(conn, c):
    _ensure_columns(c, conn)
    is_admin = login.has_role(conn, c, Role.ADMIN)

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

    # --- sesijos kintamieji ---
    if "selected_vair" not in st.session_state:
        st.session_state.selected_vair = None

    def _clear_sel():
        st.session_state.selected_vair = None

    def _new_vair():
        st.session_state.selected_vair = 0

    def _edit_vair(v_id):
        st.session_state.selected_vair = v_id

    title_with_add("Vairuotojų valdymas", "➕ Pridėti vairuotoją", on_click=_new_vair)

    sel = st.session_state.selected_vair
    drv2vilk = _driver_to_vilkik_map(c, is_admin)

    # --------------------------------------------------- Naujas vairuotojas
    if sel == 0:
        with st.form("new_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            vardas = col1.text_input("Vardas")
            pavarde = col2.text_input("Pavardė")

            gim_data = st.date_input(
                "Gimimo data", value=date(1980, 1, 1), min_value=date(1950, 1, 1)
            )

            taut_opts = [f"{v} ({k})" if k else v for v, k in TAUTYBES[1:]]
            tautybe = st.selectbox("Tautybė", taut_opts)

            atost_pab = st.date_input("Atostogų pabaiga", value=date.today())

            colL, colR = st.columns(2)
            save = colL.form_submit_button("💾 Išsaugoti")
            back = colR.form_submit_button("🔙 Atgal", on_click=_clear_sel)

        if save:
            if not vardas or not pavarde:
                st.warning("⚠️ Reikia įvesti vardą ir pavardę.")
            else:
                c.execute(
                    """
                    INSERT INTO vairuotojai (
                        vardas, pavarde, gimimo_metai, tautybe,
                        kadencijos_pabaiga, atostogu_pabaiga, imone
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        vardas,
                        pavarde,
                        gim_data.isoformat(),
                        tautybe.split("(")[-1][:-1] if "(" in tautybe else tautybe,
                        "",  # kadencijos_pabaiga
                        atost_pab.isoformat(),
                        st.session_state.get('imone'),
                    ),
                )
                conn.commit()
                st.session_state.vairuotojai_msg = "✅ Įrašyta."
                _clear_sel()
                rerun()
        return

    # --------------------------------------------------- Redagavimas
    if sel not in (None, 0):
        if is_admin:
            df_sel = pd.read_sql_query(
                "SELECT * FROM vairuotojai WHERE id = ?",
                conn,
                params=(sel,),
            )
        else:
            df_sel = pd.read_sql_query(
                "SELECT * FROM vairuotojai WHERE id = ? AND imone = ?",
                conn,
                params=(sel, st.session_state.get('imone')),
            )
        if df_sel.empty:
            st.error("❌ Nerasta.")
            _clear_sel()
            return

        row = df_sel.iloc[0]
        full_name = f"{row['vardas']} {row['pavarde']}"
        is_assigned = full_name in drv2vilk

        with st.form("edit_form"):
            col1, col2 = st.columns(2)
            vardas = col1.text_input("Vardas", value=row["vardas"])
            pavarde = col2.text_input("Pavardė", value=row["pavarde"])

            gim_data = st.date_input(
                "Gimimo data",
                value=date.fromisoformat(row["gimimo_metai"]) if row["gimimo_metai"] else date(1980, 1, 1),
            )

            taut_opts = [f"{v} ({k})" if k else v for v, k in TAUTYBES[1:]]
            idx = next((i for i, v in enumerate(taut_opts) if row["tautybe"] in v), 0)
            tautybe = st.selectbox("Tautybė", taut_opts, index=idx)

            if is_assigned:
                kad_pab = st.date_input(
                    "Kadencijos pabaiga",
                    value=date.fromisoformat(row["kadencijos_pabaiga"]) if row["kadencijos_pabaiga"] else date.today(),
                )
                atost_str = ""
            else:
                atost_pab = st.date_input(
                    "Atostogų pabaiga",
                    value=date.fromisoformat(row["atostogu_pabaiga"]) if row["atostogu_pabaiga"] else date.today(),
                )
                kad_pab = None
                atost_str = atost_pab.isoformat()

            colL, colR = st.columns(2)
            save = colL.form_submit_button("💾 Išsaugoti")
            back = colR.form_submit_button("🔙 Atgal", on_click=_clear_sel)

        if save:
            c.execute(
                """
                UPDATE vairuotojai
                SET vardas=?, pavarde=?, gimimo_metai=?, tautybe=?,
                    kadencijos_pabaiga=?, atostogu_pabaiga=?
                WHERE id=? {cond}
                """.format(cond="" if is_admin else "AND imone = ?"),
                (
                    vardas,
                    pavarde,
                    gim_data.isoformat(),
                    tautybe.split("(")[-1][:-1] if "(" in tautybe else tautybe,
                    kad_pab.isoformat() if kad_pab else "",
                    atost_str,
                    sel,
                )
                if is_admin
                else (
                    vardas,
                    pavarde,
                    gim_data.isoformat(),
                    tautybe.split("(")[-1][:-1] if "(" in tautybe else tautybe,
                    kad_pab.isoformat() if kad_pab else "",
                    atost_str,
                    sel,
                    st.session_state.get('imone'),
                ),
            )
            conn.commit()
            st.session_state.vairuotojai_msg = "✅ Pakeitimai išsaugoti."
            _clear_sel()
            rerun()
        return

    # --------------------------------------------------- Sąrašas + FILTRAI

    if is_admin:
        df = pd.read_sql_query("SELECT * FROM vairuotojai", conn)
    else:
        df = pd.read_sql_query(
            "SELECT * FROM vairuotojai WHERE imone = ?",
            conn,
            params=(st.session_state.get('imone'),),
        )

    msg = st.session_state.pop('vairuotojai_msg', None)
    if msg:
        st.success(msg)
    df = df.fillna("")

    # ---------- Filtrų eilutė ----------
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    f_vardas  = col_f1.text_input("", placeholder="Vardas", key="flt_vardas")
    f_pavarde = col_f2.text_input("", placeholder="Pavardė", key="flt_pavarde")
    f_tautybe = col_f3.selectbox(
        "", [""] + [t[1] for t in TAUTYBES[1:]], format_func=lambda x: x if x else "Tautybė", key="flt_tautybe"
    )
    f_metai = col_f4.text_input("", placeholder="Gim. metai (YYYY)", key="flt_metai")

    # --- Filtruojame ---
    if f_vardas:
        df = df[df.vardas.str.contains(f_vardas, case=False, na=False)]
    if f_pavarde:
        df = df[df.pavarde.str.contains(f_pavarde, case=False, na=False)]
    if f_tautybe:
        df = df[df.tautybe == f_tautybe]
    if f_metai:
        df = df[df.gimimo_metai.str.startswith(f_metai)]

    if df.empty:
        st.info("ℹ️ Nėra įrašų pagal filtrus.")
        return

    df_disp = df[
        ["id", "vardas", "pavarde", "gimimo_metai", "tautybe", "kadencijos_pabaiga", "atostogu_pabaiga"]
    ].rename(
        columns={
            "vardas": "Vardas",
            "pavarde": "Pavardė",
            "gimimo_metai": "Gim. data",
            "tautybe": "Tautybė",
            "kadencijos_pabaiga": "Kadencijos pabaiga",
            "atostogu_pabaiga": "Atostogų pabaiga",
        }
    )

    df_disp = df_disp
    display_table_with_edit(df_disp, _edit_vair, id_col="id")

