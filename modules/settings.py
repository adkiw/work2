import streamlit as st
from . import trailer_types, login
from .roles import Role

DEFAULT_CATEGORY = "Numatytas priekabos tipas"


def get_default_trailer_type(c, imone: str) -> str | None:
    c.execute(
        "SELECT reiksme FROM company_settings WHERE imone=? AND kategorija=?",
        (imone, DEFAULT_CATEGORY),
    )
    row = c.fetchone()
    return row[0] if row else None


def set_default_trailer_type(conn, c, imone: str, value: str | None) -> None:
    c.execute(
        "DELETE FROM company_settings WHERE imone=? AND kategorija=?",
        (imone, DEFAULT_CATEGORY),
    )
    if value:
        c.execute(
            "INSERT INTO company_settings (imone, kategorija, reiksme) VALUES (?,?,?)",
            (imone, DEFAULT_CATEGORY, value),
        )
    conn.commit()


def show(conn, c):
    """Settings page embedding trailer type management."""
    is_admin = login.has_role(conn, c, Role.ADMIN)
    is_comp_admin = login.has_role(conn, c, Role.COMPANY_ADMIN)
    if not (is_admin or is_comp_admin):
        st.error("Neturite teisių")
        return

    st.header("Nustatymai")

    trailer_types.show(conn, c)

    imone = st.session_state.get("imone")
    if not imone:
        return

    st.markdown("---")
    st.subheader("Numatytasis priekabos tipas")

    rows = c.execute(
        "SELECT reiksme FROM company_settings WHERE imone=? AND kategorija='Priekabos tipas' ORDER BY reiksme",
        (imone,),
    ).fetchall()
    if rows:
        options = [r[0] for r in rows]
    else:
        options = [
            r[0]
            for r in c.execute(
                "SELECT reiksme FROM lookup WHERE kategorija='Priekabos tipas' ORDER BY reiksme"
            ).fetchall()
        ]

    current = get_default_trailer_type(c, imone)
    idx = options.index(current) + 1 if current in options else 0
    choice = st.selectbox("Pasirinkite numatytąjį priekabos tipą", [""] + options, index=idx)

    if st.button("💾 Išsaugoti nustatymą"):
        set_default_trailer_type(conn, c, imone, choice or None)
        st.success("✅ Išsaugota")

