# main.py
import streamlit as st

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
    planavimas,
    update
)

# 5) Horizontalus meniu
moduliai = [
    "Kroviniai",
    "Vilkikai",
    "Priekabos",
    "Grupės",
    "Vairuotojai",
    "Klientai",
    "Darbuotojai",
    "Planavimas",
    "Update"
]
pasirinktas = st.radio("", moduliai, horizontal=True)

# 6) Maršrutizacija
if pasirinktas == "Kroviniai":
    kroviniai.show(conn, c)
elif pasirinktas == "Vilkikai":
    vilkikai.show(conn, c)
elif pasirinktas == "Priekabos":
    priekabos.show(conn, c)
elif pasirinktas == "Grupės":
    grupes.show(conn, c)
elif pasirinktas == "Vairuotojai":
    vairuotojai.show(conn, c)
elif pasirinktas == "Klientai":
    klientai.show(conn, c)
elif pasirinktas == "Darbuotojai":
    darbuotojai.show(conn, c)
elif pasirinktas == "Planavimas":
    planavimas.show(conn, c)
elif pasirinktas == "Update":
    update.show(conn, c)
