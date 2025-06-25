# modules/grupes.py

import streamlit as st
import pandas as pd

def show(conn, c):
    st.title("Grupės")

    # 1) Užtikrinti, kad egzistuotų lentelė „grupes“
    c.execute("""
        CREATE TABLE IF NOT EXISTS grupes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numeris TEXT UNIQUE,
            pavadinimas TEXT,
            aprasymas TEXT
        )
    """)
    # 2) Užtikrinti, kad egzistuotų lentelė „grupiu_regionai“
    c.execute("""
        CREATE TABLE IF NOT EXISTS grupiu_regionai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupe_id INTEGER NOT NULL,
            regiono_kodas TEXT NOT NULL,
            FOREIGN KEY (grupe_id) REFERENCES grupes(id)
        )
    """)
    conn.commit()

    # 3) Automatiškai sukurti numatytąsias grupes (EKSP1–EKSP5, TR1–TR5), jei jų dar nėra
    default_eksp = [f"EKSP{i}" for i in range(1, 6)]
    default_tr   = [f"TR{i}"   for i in range(1, 6)]
    for kod in default_eksp + default_tr:
        c.execute("SELECT 1 FROM grupes WHERE numeris = ?", (kod,))
        if not c.fetchone():
            c.execute(
                "INSERT INTO grupes (numeris, pavadinimas, aprasymas) VALUES (?, ?, ?)",
                (kod, kod, "")
            )
    conn.commit()

    # 4) Mygtukas formos rodymui/uždarymui
    if "show_add_form" not in st.session_state:
        st.session_state["show_add_form"] = False

    if st.button("➕ Pridėti grupę"):
        st.session_state["show_add_form"] = True

    # 5) Jei paspausta „Pridėti grupę“, atvaizduoti formą
    if st.session_state["show_add_form"]:
        st.subheader("➕ Naujos grupės forma")
        with st.form("grupes_forma", clear_on_submit=True):
            numeris     = st.text_input("Grupės numeris (pvz., EKSP6 arba TR6)")
            pavadinimas = st.text_input("Pavadinimas")
            aprasymas   = st.text_area("Aprašymas")
            save_btn    = st.form_submit_button("💾 Išsaugoti grupę")
            cancel_btn  = st.form_submit_button("🔙 Atšaukti")

            if cancel_btn:
                st.session_state["show_add_form"] = False

            if save_btn:
                if not numeris:
                    st.error("❌ Grupės numeris privalomas.")
                else:
                    kodas = numeris.strip().upper()
                    try:
                        c.execute(
                            "INSERT INTO grupes (numeris, pavadinimas, aprasymas) VALUES (?, ?, ?)",
                            (kodas, pavadinimas.strip(), aprasymas.strip())
                        )
                        conn.commit()
                        st.success(f"✅ Grupė „{kodas}“ įrašyta.")
                        st.session_state["show_add_form"] = False
                    except Exception as e:
                        st.error(f"❌ Klaida: {e}")

    st.markdown("---")
    st.subheader("📋 Grupių sąrašas")

    # 6) Visų grupių sąrašas (atidaryti visada)
    grupes_df = pd.read_sql_query("SELECT id, numeris, pavadinimas FROM grupes ORDER BY numeris", conn)
    if grupes_df.empty:
        st.info("Kol kas nėra jokių grupių.")
        return

    # 7) Dropdown pasirinkti grupę
    pasirinkti = [""] + grupes_df["numeris"].tolist()
    pasirinkta_grupe = st.selectbox("Pasirinkite grupę", pasirinkti)

    if not pasirinkta_grupe:
        st.info("Pasirinkite grupę, kad pamatytumėte jos informaciją.")
        return

    # 8) Randame pasirinktos grupės ID
    grupe_row = grupes_df[grupes_df["numeris"] == pasirinkta_grupe]
    if grupe_row.empty:
        st.error("Pasirinkta grupė nerasta duomenų bazėje.")
        return
    grupe_id = int(grupe_row["id"].iloc[0])

    # 9) Nustatome grupės tipą pagal prefiksą
    kodas = pasirinkta_grupe.upper()
    if kodas.startswith("TR"):
        st.subheader(f"🚚 Transporto grupė: {pasirinkta_grupe}")

        #  –––––––– PAKEISTAS UŽKLAUSOS JOIN sąlyga ––––––––
        # Buvo: JOIN darbuotojai d ON v.vadybininkas = d.vardas
        # Dabar: jungiamas vardas + tarpas + pavardė prie pilno lauko v.vadybininkas
        query = """
            SELECT
                v.numeris     AS vilkiko_numeris,
                v.priekaba,
                v.vadybininkas
            FROM vilkikai v
            JOIN darbuotojai d
              ON v.vadybininkas = (d.vardas || ' ' || d.pavarde)
            WHERE d.grupe = ?
            ORDER BY v.numeris
        """
        vilkikai = pd.read_sql_query(query, conn, params=(pasirinkta_grupe,))
        if vilkikai.empty:
            st.info("Šiai transporto grupei dar nepriskirtas nei vienas vilkikas.")
        else:
            st.markdown("**🚛 Priskirti vilkikai:**")
            st.dataframe(vilkikai)

    elif kodas.startswith("EKSP"):
        st.subheader(f"📦 Ekspedicijos grupė: {pasirinkta_grupe}")

        # 10a) Rodyti priskirtus darbuotojus
        st.markdown("**👥 Priskirti darbuotojai:**")
        darb_query = """
            SELECT vardas, pavarde, pareigybe
            FROM darbuotojai
            WHERE grupe = ?
            ORDER BY pavarde, vardas
        """
        darbuotojai = pd.read_sql_query(darb_query, conn, params=(pasirinkta_grupe,))
        if darbuotojai.empty:
            st.info("Šiai ekspedicijos grupei dar nepriskirtas nei vienas darbuotojas.")
        else:
            st.dataframe(darbuotojai)

        # 10b) Rodyti įvestus regionus
        st.markdown("**🌍 Aptarnaujami regionai:**")
        regionai_df = pd.read_sql_query(
            "SELECT regiono_kodas FROM grupiu_regionai WHERE grupe_id = ? ORDER BY regiono_kodas",
            conn,
            params=(grupe_id,)
        )
        if regionai_df.empty:
            st.info("Šiai ekspedicijos grupei dar nepriskirtas nei vienas regionas.")
        else:
            st.write(", ".join(regionai_df["regiono_kodas"].tolist()))

        # 10c) Forma naujiems regionams pridėti (keli vienu kartu)
        with st.form("prideti_regionus", clear_on_submit=True):
            st.write("Įveskite regionų kodus semikolonais atskirtus (pvz.: FR10;FR20;IT05)")
            regionu_input = st.text_area("Regionų sąrašas", max_chars=10000)
            prideti_btn = st.form_submit_button("➕ Pridėti regionus")

            if prideti_btn:
                if not regionu_input.strip():
                    st.error("❌ Įveskite bent vieną regiono kodą.")
                else:
                    įvesti_regionai = [
                        r.strip().upper() for r in regionu_input.split(";") if r.strip()
                    ]
                    if not įvesti_regionai:
                        st.error("❌ Nepavyko atpažinti jokių regionų kodų.")
                    else:
                        pridėta = []
                        jau_egzistuojantys = []
                        klaidos = []
                        for kodas_val in įvesti_regionai:
                            exists = c.execute(
                                "SELECT 1 FROM grupiu_regionai WHERE grupe_id = ? AND regiono_kodas = ?",
                                (grupe_id, kodas_val)
                            ).fetchone()
                            if exists:
                                jau_egzistuojantys.append(kodas_val)
                            else:
                                try:
                                    c.execute(
                                        "INSERT INTO grupiu_regionai (grupe_id, regiono_kodas) VALUES (?, ?)",
                                        (grupe_id, kodas_val)
                                    )
                                    conn.commit()
                                    pridėta.append(kodas_val)
                                except Exception as e:
                                    klaidos.append((kodas_val, str(e)))

                        if pridėta:
                            st.success(f"✅ Pridėti regionai: {', '.join(pridėta)}.")
                        if jau_egzistuojantys:
                            st.warning(f"⚠️ Šie regionai jau buvo priskirti: {', '.join(jau_egzistuojantys)}.")
                        if klaidos:
                            msg = "; ".join([f"{k}: {e}" for k, e in klaidos])
                            st.error(f"❌ Klaidos įterpiant: {msg}")
    else:
        st.warning("Pasirinkta grupė nepriskirta nei TR, nei EKSP tipo kriterijams.")
