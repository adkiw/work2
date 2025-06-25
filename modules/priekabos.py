import streamlit as st
import pandas as pd
from datetime import date

def show(conn, c):
    st.title("Priekabų valdymas")

    # 1) Užtikriname, kad lentelėje 'priekabos' egzistuotų visi reikalingi stulpeliai
    existing = [r[1] for r in c.execute("PRAGMA table_info(priekabos)").fetchall()]
    extras = {
        'priekabu_tipas': 'TEXT',
        'numeris': 'TEXT',
        'marke': 'TEXT',
        'pagaminimo_metai': 'TEXT',
        'tech_apziura': 'TEXT',
        'draudimas': 'TEXT'
        # Nebereikalingas 'priskirtas_vilkikas' stulpelis, nes jį gausime iš vilkikai modulyje
    }
    for col, typ in extras.items():
        if col not in existing:
            c.execute(f"ALTER TABLE priekabos ADD COLUMN {col} {typ}")
    conn.commit()

    # 2) Paruošiame Dropdown duomenis
    vilkikai_list = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]

    # 3) Sesijos būsena
    if 'selected_priek' not in st.session_state:
        st.session_state.selected_priek = None

    def clear_sel():
        st.session_state.selected_priek = None
        # Išvalome filtrus
        for key in list(st.session_state):
            if key.startswith("f_"):
                st.session_state[key] = ""

    def new():
        st.session_state.selected_priek = 0

    def edit(id):
        st.session_state.selected_priek = id

    # 4) "Pridėti priekabą" mygtukas viršuje
    st.button("➕ Pridėti priekabą", on_click=new, use_container_width=True)

    sel = st.session_state.selected_priek

    # 5) Redagavimo rodinys (kai pasirenkama esama priekaba)
    if sel not in (None, 0):
        df_sel = pd.read_sql_query(
            "SELECT * FROM priekabos WHERE id = ?", conn, params=(sel,)
        )
        if df_sel.empty:
            st.error("❌ Priekaba nerasta.")
            clear_sel()
            return

        row = df_sel.iloc[0]
        with st.form("edit_form", clear_on_submit=False):
            # 5.1) Priekabos tipas – DROPlistas su fiksuotomis reikšmėmis
            priekabu_tipas_opts = ["", "Standartinis Tentas", "Kietašonė puspriekabė", "Šaldytuvas"]
            tip_idx = 0
            if row['priekabu_tipas'] in priekabu_tipas_opts:
                tip_idx = priekabu_tipas_opts.index(row['priekabu_tipas'])
            tip = st.selectbox("Priekabos tipas", priekabu_tipas_opts, index=tip_idx)

            # 5.2) Kiti laukai
            num = st.text_input("Numeris", value=row['numeris'])
            model = st.text_input("Markė", value=row['marke'])
            pr_data = st.date_input(
                "Pirmos registracijos data",
                value=(date.fromisoformat(row['pagaminimo_metai']) if row['pagaminimo_metai'] else date(2000,1,1)),
                key="pr_data"
            )
            tech = st.date_input(
                "Tech. apžiūra",
                value=(date.fromisoformat(row['tech_apziura']) if row['tech_apziura'] else date.today()),
                key="tech_date"
            )
            draud_date = st.date_input(
                "Draudimo galiojimo pabaiga",
                value=(date.fromisoformat(row['draudimas']) if row['draudimas'] else date.today()),
                key="draud_date"
            )

            # 5.3) Priskirtas vilkikas – skaitome iš vilkikai lentelės
            assigned_vilk = c.execute(
                "SELECT numeris FROM vilkikai WHERE priekaba = ?", (row['numeris'],)
            ).fetchone()
            pv = assigned_vilk[0] if assigned_vilk else ""
            st.text_input("Priskirtas vilkikas", value=pv, disabled=True)

            col1, col2 = st.columns(2)
            save = col1.form_submit_button("💾 Išsaugoti")
            back = col2.form_submit_button("🔙 Grįžti į sąrašą", on_click=clear_sel)

        if save:
            try:
                c.execute(
                    "UPDATE priekabos SET priekabu_tipas=?, numeris=?, marke=?, pagaminimo_metai=?, tech_apziura=?, draudimas=? WHERE id=?",
                    (
                        tip or None,
                        num,
                        model or None,
                        (pr_data.isoformat() if pr_data else None),
                        (tech.isoformat() if tech else None),
                        (draud_date.isoformat() if draud_date else None),
                        sel
                    )
                )
                conn.commit()
                st.success("✅ Pakeitimai išsaugoti.")
                clear_sel()
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
        return

    # 6) Naujos priekabos įvedimo forma
    if sel == 0:
        with st.form("new_form", clear_on_submit=True):
            priekabu_tipas_opts = ["", "Standartinis Tentas", "Kietašonė puspriekabė", "Šaldytuvas"]
            tip = st.selectbox("Priekabos tipas", priekabu_tipas_opts)

            num = st.text_input("Numeris")
            model = st.text_input("Markė")
            pr_data = st.date_input("Pirmos registracijos data", value=date(2000,1,1), key="new_pr_data")
            tech = st.date_input("Tech. apžiūra", value=date.today(), key="new_tech_date")
            draud_date = st.date_input("Draudimo galiojimo pabaiga", value=date.today(), key="new_draud_date")

            col1, col2 = st.columns(2)
            save = col1.form_submit_button("💾 Išsaugoti priekabą")
            back = col2.form_submit_button("🔙 Grįžti į sąrašą", on_click=clear_sel)

        if save:
            if not num:
                st.warning("⚠️ Įveskite numerį.")
            else:
                try:
                    c.execute(
                        "INSERT INTO priekabos(priekabu_tipas, numeris, marke, pagaminimo_metai, tech_apziura, draudimas) VALUES(?,?,?,?,?,?)",
                        (
                            tip or None,
                            num,
                            model or None,
                            pr_data.isoformat(),
                            tech.isoformat(),
                            draud_date.isoformat()
                        )
                    )
                    conn.commit()
                    st.success("✅ Priekaba įrašyta.")
                    clear_sel()
                except Exception as e:
                    st.error(f"❌ Klaida: {e}")
        return

    # 7) Priekabų sąrašas
    df = pd.read_sql_query("SELECT * FROM priekabos", conn)
    if df.empty:
        st.info("ℹ️ Nėra priekabų.")
        return

    # 7.1) Paruošiame rodymui: None → ""
    df = df.fillna('')
    df_disp = df.copy()
    df_disp.rename(
        columns={
            'marke': 'Markė',
            'pagaminimo_metai': 'Pirmos registracijos data',
            'draudimas': 'Draudimo galiojimo pabaiga'
        },
        inplace=True
    )

    # 7.2) Pridedame stulpelį "Priskirtas vilkikas" pagal vilkikai modulį
    assigned_list = []
    for _, row in df.iterrows():
        prn = row['numeris']
        assigned_vilk = c.execute(
            "SELECT numeris FROM vilkikai WHERE priekaba = ?", (prn,)
        ).fetchone()
        assigned_list.append(assigned_vilk[0] if assigned_vilk else "")
    df_disp['Priskirtas vilkikas'] = assigned_list

    # 7.3) Apskaičiuojame kiek dienų iki tech apžiūros ir draudimo
    df_disp['Liko iki tech apžiūros'] = df_disp['tech_apziura'].apply(
        lambda x: (date.fromisoformat(x) - date.today()).days if x else ''
    )
    df_disp['Liko iki draudimo'] = df_disp['Draudimo galiojimo pabaiga'].apply(
        lambda x: (date.fromisoformat(x) - date.today()).days if x else ''
    )

    # 7.4) Filtravimo laukai (tik placeholder, be jokių headerių virš jų)
    filter_cols = st.columns(len(df_disp.columns) + 1)
    for i, col in enumerate(df_disp.columns):
        filter_cols[i].text_input(label="", placeholder=col, key=f"f_{col}")
    filter_cols[-1].write("")

    df_filt = df_disp.copy()
    for col in df_disp.columns:
        val = st.session_state.get(f"f_{col}", "")
        if val:
            df_filt = df_filt[
                df_filt[col].astype(str).str.lower().str.startswith(val.lower())
            ]

    # 7.5) Lentelės eilutės su redagavimo mygtuku (be headerių po filtrų)
    for _, row in df_filt.iterrows():
        row_cols = st.columns(len(df_filt.columns) + 1)
        for i, col in enumerate(df_filt.columns):
            row_cols[i].write(row[col])
        row_cols[-1].button(
            "✏️",
            key=f"edit_{row['id']}",
            on_click=edit,
            args=(row['id'],)
        )

    # 7.6) Eksportas į CSV
    csv = df.to_csv(index=False, sep=';').encode('utf-8')
    st.download_button(
        label="💾 Eksportuoti kaip CSV",
        data=csv,
        file_name="priekabos.csv",
        mime="text/csv"
    )
