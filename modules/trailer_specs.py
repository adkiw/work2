import streamlit as st
from . import login
from .roles import Role
from .utils import title_with_add, rerun
from .audit import log_action


def show(conn, c):
    """Manage trailer specification records."""
    if not login.has_role(conn, c, Role.ADMIN):
        st.error("Neturite teisių")
        return

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS trailer_specs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipas TEXT UNIQUE,
            ilgis REAL,
            plotis REAL,
            aukstis REAL,
            keliamoji_galia REAL,
            talpa REAL
        )
        """
    )
    conn.commit()

    if "spec_add" not in st.session_state:
        st.session_state.spec_add = False
    if "spec_edit" not in st.session_state:
        st.session_state.spec_edit = None

    if title_with_add("Priekabų charakteristikos", "➕ Pridėti", key="add_spec_btn"):
        st.session_state.spec_add = True

    if st.session_state.spec_edit:
        rec_id = st.session_state.spec_edit
        row = c.execute(
            "SELECT tipas, ilgis, plotis, aukstis, keliamoji_galia, talpa FROM trailer_specs WHERE id=?",
            (rec_id,),
        ).fetchone()
        if not row:
            st.session_state.spec_edit = None
        else:
            with st.form("edit_spec_form"):
                tipas = st.text_input("Tipas", value=row[0])
                ilgis = st.number_input("Ilgis", value=row[1] or 0.0)
                plotis = st.number_input("Plotis", value=row[2] or 0.0)
                aukstis = st.number_input("Aukštis", value=row[3] or 0.0)
                galia = st.number_input("Keliamoji galia", value=row[4] or 0.0)
                talpa = st.number_input("Talpa", value=row[5] or 0.0)
                save = st.form_submit_button("💾 Išsaugoti")
                cancel = st.form_submit_button("🔙 Atšaukti")
            if cancel:
                st.session_state.spec_edit = None
            if save:
                c.execute(
                    """
                    UPDATE trailer_specs
                    SET tipas=?, ilgis=?, plotis=?, aukstis=?, keliamoji_galia=?, talpa=?
                    WHERE id=?
                    """,
                    (tipas.strip(), ilgis, plotis, aukstis, galia, talpa, rec_id),
                )
                conn.commit()
                log_action(
                    conn,
                    c,
                    st.session_state.get('user_id'),
                    'update',
                    'trailer_specs',
                    rec_id,
                )
                st.session_state.spec_edit = None
                st.success("✅ Išsaugota")
                rerun()
        return

    if st.session_state.spec_add:
        with st.form("add_spec_form", clear_on_submit=True):
            tipas = st.text_input("Tipas")
            ilgis = st.number_input("Ilgis", value=0.0)
            plotis = st.number_input("Plotis", value=0.0)
            aukstis = st.number_input("Aukštis", value=0.0)
            galia = st.number_input("Keliamoji galia", value=0.0)
            talpa = st.number_input("Talpa", value=0.0)
            save = st.form_submit_button("💾 Išsaugoti")
            cancel = st.form_submit_button("🔙 Atšaukti")
        if cancel:
            st.session_state.spec_add = False
        elif save:
            if tipas.strip():
                c.execute(
                    "INSERT INTO trailer_specs (tipas, ilgis, plotis, aukstis, keliamoji_galia, talpa) VALUES (?,?,?,?,?,?)",
                    (tipas.strip(), ilgis, plotis, aukstis, galia, talpa),
                )
                conn.commit()
                log_action(
                    conn,
                    c,
                    st.session_state.get('user_id'),
                    'insert',
                    'trailer_specs',
                    c.lastrowid,
                )
                st.session_state.spec_add = False
                st.success("✅ Įrašyta")
                rerun()
            else:
                st.warning("⚠️ Įveskite tipą.")
        return

    st.subheader("Specifikacijų sąrašas")
    rows = c.execute(
        "SELECT id, tipas, ilgis, plotis, aukstis, keliamoji_galia, talpa FROM trailer_specs ORDER BY tipas"
    ).fetchall()
    if not rows:
        st.info("Nėra įrašų.")
        return
    for spec in rows:
        spec_id, tipas, ilgis, plotis, aukstis, galia, talpa = spec
        cols = st.columns([4,2,2,2,2,2,1])
        cols[0].write(tipas)
        cols[1].write(ilgis or "")
        cols[2].write(plotis or "")
        cols[3].write(aukstis or "")
        cols[4].write(galia or "")
        cols[5].write(talpa or "")
        if cols[6].button("✏️", key=f"edit_spec_{spec_id}"):
            st.session_state.spec_edit = spec_id
            rerun()
