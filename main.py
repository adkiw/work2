# main.py
import streamlit as st
from modules.roles import Role
from modules.utils import rerun

# 1) Puslapio nustatymai
st.set_page_config(layout="wide")

# Theme selection stored in session_state
if "theme" not in st.session_state:
    st.session_state.theme = "Light"

st.config.set_option("theme.base", st.session_state.theme.lower())

selected = st.sidebar.selectbox(
    "Theme",
    ["Light", "Dark"],
    index=0 if st.session_state.theme == "Light" else 1,
)

if selected != st.session_state.theme:
    st.session_state.theme = selected
    st.config.set_option("theme.base", selected.lower())
    rerun()

# 2) Minimalus CSS – meniu prigludęs prie viršaus
st.markdown(
    """
<style>
  .css-18e3th9 { padding-top: 0 !important; margin-top: 0 !important; }
  .stApp { padding-top: 0 !important; }
</style>
""",
    unsafe_allow_html=True,
)
# 4) Inicializuojame DB – lentelės sukuriamos funkcijoje init_db()
from db import init_db
conn, c = init_db()    # naudos failą „main.db“

# 4) Importuojame visus modulius
from modules import (
    kroviniai,
    vilkikai,
    priekabos,
    grupes,
    vairuotojai,
    klientai,
    darbuotojai,
    user_admin,
    audit,
    planavimas,
    update,
    settings,
    login,
)

login.show(conn, c)

if "user_id" not in st.session_state:
    st.info("Prašome prisijungti")
    st.stop()

# 5) Horizontalus meniu
module_functions = {
    "Užsakymai": kroviniai.show,
    "Vilkikai": vilkikai.show,
    "Priekabos": priekabos.show,
    "Grupės": grupes.show,
    "Vairuotojai": vairuotojai.show,
    "Klientai": klientai.show,
    "Darbuotojai": darbuotojai.show,
    "Registracijos": user_admin.show,
    "Audit": audit.show,
    "Planavimas": planavimas.show,
    "Update": update.show,
    "Nustatymai": settings.show,
}

MODULE_ROLES = {
    "Registracijos": [Role.ADMIN, Role.COMPANY_ADMIN],
    "Audit": [Role.ADMIN],
    "Nustatymai": [Role.ADMIN],
}

def allowed(name: str) -> bool:
    roles = MODULE_ROLES.get(name)
    if not roles:
        return True
    return any(login.has_role(conn, c, r) for r in roles)

available_modules = [n for n in module_functions.keys() if allowed(n)]

# 6) Meniu juosta naudojant Streamlit tabs
tabs = st.tabs(available_modules)
for tab, name in zip(tabs, available_modules):
    with tab:
        module_functions[name](conn, c)
