import streamlit as st
from . import trailer_types, login
from .roles import Role

DEFAULT_CATEGORY = "Numatytas priekabos tipas"


def get_default_trailer_types(c, imone: str) -> list[str]:
    """Return ordered list of default trailer types for a company."""
    rows = c.execute(
        "SELECT reiksme FROM company_default_trailers WHERE imone=? ORDER BY priority",
        (imone,),
    ).fetchall()
    return [r[0] for r in rows]


def set_default_trailer_types(conn, c, imone: str, values: list[str]) -> None:
    """Replace company's default trailer type list with the given values."""
    c.execute("DELETE FROM company_default_trailers WHERE imone=?", (imone,))
    for pr, val in enumerate(values):
        c.execute(
            "INSERT INTO company_default_trailers (imone, reiksme, priority) VALUES (?,?,?)",
            (imone, val, pr),
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

    # Embed trailer type management with unique widget keys
    trailer_types.show(conn, c, key_prefix="settings_")

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

    defaults = get_default_trailer_types(c, imone)
    if "def_trailers" not in st.session_state:
        st.session_state.def_trailers = defaults or []

    for i, val in enumerate(st.session_state.def_trailers):
        cols = st.columns([6, 1, 1, 1])
        idx = options.index(val) if val in options else 0
        st.session_state.def_trailers[i] = cols[0].selectbox(
            f"Numatytoji #{i+1}", options, index=idx, key=f"def_sel_{i}"
        )
        if cols[1].button("⬆️", key=f"def_up_{i}") and i > 0:
            st.session_state.def_trailers[i - 1], st.session_state.def_trailers[i] = (
                st.session_state.def_trailers[i],
                st.session_state.def_trailers[i - 1],
            )
            st.experimental_rerun()
        if cols[2].button("⬇️", key=f"def_down_{i}") and i < len(st.session_state.def_trailers) - 1:
            st.session_state.def_trailers[i + 1], st.session_state.def_trailers[i] = (
                st.session_state.def_trailers[i],
                st.session_state.def_trailers[i + 1],
            )
            st.experimental_rerun()
        if cols[3].button("🗑️", key=f"def_del_{i}"):
            st.session_state.def_trailers.pop(i)
            st.experimental_rerun()

    if st.button("➕ Pridėti numatytąjį"):
        st.session_state.def_trailers.append(options[0] if options else "")
        st.experimental_rerun()

    if st.button("💾 Išsaugoti nustatymą"):
        set_default_trailer_types(conn, c, imone, st.session_state.def_trailers)
        st.success("✅ Išsaugota")

