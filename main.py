# main.py
import streamlit as st
from modules.roles import Role

# 1) Puslapio nustatymai
st.set_page_config(layout="wide")

# 2) Minimalus CSS (radio bar lieka viršuje)
st.markdown("""
<style>
  .css-18e3th9 { padding-top: 0 !important; }
  .stRadio > div          { height: 1cm !important; margin-top: 0 !important; }
  .stRadio > div > label > div { padding-top: 0 !important; padding-bottom: 0 !important; }
</style>
""", unsafe_allow_html=True)

# 3) Inicializuojame DB – lentelės sukuriamos funkcijoje init_db()
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
    planavimas,
    update,
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
    "Planavimas": planavimas.show,
    "Update": update.show,
}

MODULE_ROLES = {
    "Registracijos": [Role.ADMIN, Role.COMPANY_ADMIN],
}

def allowed(name: str) -> bool:
    roles = MODULE_ROLES.get(name)
    if not roles:
        return True
    return any(login.has_role(conn, c, r) for r in roles)

available_modules = [n for n in module_functions.keys() if allowed(n)]

pasirinktas = st.radio("", available_modules, horizontal=True)

# 6) Maršrutizacija
module_functions[pasirinktas](conn, c)
