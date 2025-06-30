import streamlit as st
from . import login
from .roles import Role
from .utils import title_with_add, rerun

CATEGORY = "Priekabos tipas"


def show(conn, c, *, key_prefix: str = ""):
    """Interface to manage trailer types."""
    is_admin = login.has_role(conn, c, Role.ADMIN)
    is_comp_admin = login.has_role(conn, c, Role.COMPANY_ADMIN)
    if not (is_admin or is_comp_admin):
        st.error("Neturite teisių")
        return

    # Ensure necessary tables exist
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS lookup (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kategorija TEXT,
            reiksme TEXT,
            UNIQUE (kategorija, reiksme)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS company_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imone TEXT,
            kategorija TEXT,
            reiksme TEXT,
            UNIQUE (imone, kategorija, reiksme)
        )
        """
    )
    conn.commit()

    if "show_add_type" not in st.session_state:
        st.session_state.show_add_type = False
    if "edit_type" not in st.session_state:
        st.session_state.edit_type = None

    if title_with_add("Priekabų tipai", "➕ Pridėti tipą", key=f"{key_prefix}add_btn"):
        st.session_state.show_add_type = True

    # ----- Edit existing type -----
    if st.session_state.edit_type:
        rec_id, initial = st.session_state.edit_type
        with st.form(f"{key_prefix}edit_type_form"):
            val = st.text_input("Priekabos tipas", value=initial)
            save = st.form_submit_button("💾 Išsaugoti")
            cancel = st.form_submit_button("🔙 Atšaukti")
        if cancel:
            st.session_state.edit_type = None
        if save:
            if val.strip():
                try:
                    table = "lookup" if is_admin else "company_settings"
                    c.execute(f"UPDATE {table} SET reiksme=? WHERE id=?", (val.strip(), rec_id))
                    conn.commit()
                    st.session_state.edit_type = None
                    st.success("✅ Išsaugota")
                    rerun()
                except Exception as e:
                    st.error(f"❌ Klaida: {e}")
            else:
                st.warning("⚠️ Įveskite tipą.")
        return

    # ----- Add new type form -----
    if st.session_state.show_add_type:
        with st.form(f"{key_prefix}add_type_form", clear_on_submit=True):
            val = st.text_input("Priekabos tipas")
            save = st.form_submit_button("💾 Išsaugoti")
            cancel = st.form_submit_button("🔙 Atšaukti")
        if cancel:
            st.session_state.show_add_type = False
        elif save:
            if val.strip():
                try:
                    if is_admin:
                        c.execute(
                            "INSERT INTO lookup (kategorija, reiksme) VALUES (?, ?)",
                            (CATEGORY, val.strip()),
                        )
                    else:
                        c.execute(
                            "INSERT INTO company_settings (imone, kategorija, reiksme) VALUES (?,?,?)",
                            (st.session_state.get('imone'), CATEGORY, val.strip()),
                        )
                    conn.commit()
                    st.session_state.show_add_type = False
                    st.success("✅ Įrašyta")
                    rerun()
                except Exception as e:
                    st.error(f"❌ Klaida: {e}")
            else:
                st.warning("⚠️ Įveskite tipą.")
        return

    st.markdown("---")
    st.subheader("Priekabų tipų sąrašas")
    if is_admin:
        rows = c.execute(
            "SELECT id, reiksme FROM lookup WHERE kategorija=? ORDER BY reiksme",
            (CATEGORY,),
        ).fetchall()
    else:
        rows = c.execute(
            "SELECT id, reiksme FROM company_settings WHERE imone=? AND kategorija=? ORDER BY reiksme",
            (st.session_state.get('imone'), CATEGORY),
        ).fetchall()
    if not rows:
        st.info("Nėra priekabų tipų.")
        return

    for rec_id, val in rows:
        cols = st.columns([8, 1, 1])
        cols[0].write(val)
        if cols[1].button("✏️", key=f"{key_prefix}edit_{rec_id}"):
            st.session_state.edit_type = (rec_id, val)
            rerun()
        if cols[2].button("🗑️", key=f"{key_prefix}del_{rec_id}"):
            table = "lookup" if is_admin else "company_settings"
            c.execute(f"DELETE FROM {table} WHERE id=?", (rec_id,))
            conn.commit()
            st.success("❎ Ištrinta")
            rerun()
