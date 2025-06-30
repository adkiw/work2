import streamlit as st
from . import login
from .roles import Role
from .utils import title_with_add

CATEGORY = "Priekabos tipas"


def show(conn, c):
    """Admin interface to manage trailer types."""
    if not login.has_role(conn, c, Role.ADMIN):
        st.error("Neturite teisių")
        return

    # Ensure lookup table exists
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS lookup (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kategorija TEXT,
            reiksme TEXT UNIQUE
        )
        """
    )
    conn.commit()

    if "show_add_type" not in st.session_state:
        st.session_state.show_add_type = False
    if "edit_type" not in st.session_state:
        st.session_state.edit_type = None

    if title_with_add("Priekabų tipai", "➕ Pridėti tipą"):
        st.session_state.show_add_type = True

    # ----- Edit existing type -----
    if st.session_state.edit_type:
        rec_id, initial = st.session_state.edit_type
        with st.form("edit_type_form"):
            val = st.text_input("Priekabos tipas", value=initial)
            save = st.form_submit_button("💾 Išsaugoti")
            cancel = st.form_submit_button("🔙 Atšaukti")
        if cancel:
            st.session_state.edit_type = None
        if save:
            if val.strip():
                try:
                    c.execute("UPDATE lookup SET reiksme=? WHERE id=?", (val.strip(), rec_id))
                    conn.commit()
                    st.session_state.edit_type = None
                    st.success("✅ Išsaugota")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ Klaida: {e}")
            else:
                st.warning("⚠️ Įveskite tipą.")
        return

    # ----- Add new type form -----
    if st.session_state.show_add_type:
        with st.form("add_type_form", clear_on_submit=True):
            val = st.text_input("Priekabos tipas")
            save = st.form_submit_button("💾 Išsaugoti")
            cancel = st.form_submit_button("🔙 Atšaukti")
        if cancel:
            st.session_state.show_add_type = False
        elif save:
            if val.strip():
                try:
                    c.execute(
                        "INSERT INTO lookup (kategorija, reiksme) VALUES (?, ?)",
                        (CATEGORY, val.strip()),
                    )
                    conn.commit()
                    st.session_state.show_add_type = False
                    st.success("✅ Įrašyta")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ Klaida: {e}")
            else:
                st.warning("⚠️ Įveskite tipą.")
        return

    st.markdown("---")
    st.subheader("Priekabų tipų sąrašas")
    rows = c.execute(
        "SELECT id, reiksme FROM lookup WHERE kategorija=? ORDER BY reiksme",
        (CATEGORY,),
    ).fetchall()
    if not rows:
        st.info("Nėra priekabų tipų.")
        return

    for rec_id, val in rows:
        cols = st.columns([8, 1, 1])
        cols[0].write(val)
        if cols[1].button("✏️", key=f"edit_{rec_id}"):
            st.session_state.edit_type = (rec_id, val)
            st.experimental_rerun()
        if cols[2].button("🗑️", key=f"del_{rec_id}"):
            c.execute("DELETE FROM lookup WHERE id=?", (rec_id,))
            conn.commit()
            st.success("❎ Ištrinta")
            st.experimental_rerun()
