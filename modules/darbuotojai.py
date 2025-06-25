import streamlit as st
import pandas as pd

def show(conn, c):
    # Užtikrinti, kad egzistuotų stulpelis „aktyvus“ darbuotojų lentelėje
    c.execute("PRAGMA table_info(darbuotojai)")
    cols = {row[1] for row in c.fetchall()}
    if 'aktyvus' not in cols:
        c.execute("ALTER TABLE darbuotojai ADD COLUMN aktyvus INTEGER DEFAULT 1")
        conn.commit()

    # Callback’ai
    def clear_selection():
        st.session_state.selected_emp = None

    def start_new():
        st.session_state.selected_emp = 0

    def start_edit(emp_id):
        st.session_state.selected_emp = emp_id

    # Antraštė + „Pridėti naują darbuotoją“ mygtukas
    title_col, add_col = st.columns([9, 1])
    title_col.title("Darbuotojai")
    add_col.button("➕ Pridėti naują darbuotoją", on_click=start_new, use_container_width=True)

    # Inicializuojame būseną
    if 'selected_emp' not in st.session_state:
        st.session_state.selected_emp = None

    # 1. SĄRAŠO rodinys su filtravimu (be headerių virš ir po filtrų)
    if st.session_state.selected_emp is None:
        df = pd.read_sql(
            "SELECT id, vardas, pavarde, pareigybe, el_pastas, telefonas, grupe, aktyvus FROM darbuotojai",
            conn
        )

        if df.empty:
            st.info("ℹ️ Nėra darbuotojų.")
            return

        # Paruošiame rodymui: None → ""
        df = df.fillna('')

        # 1.1) Filtravimo laukai su placeholder’iais (tik patys filtrai, be antraščių)
        filter_cols = st.columns(len(df.columns) + 1)
        for i, col in enumerate(df.columns):
            filter_cols[i].text_input(label="", placeholder=col, key=f"f_emp_{col}")
        filter_cols[-1].write("")

        # 1.2) Taikome filtrus
        df_filt = df.copy()
        for col in df.columns:
            val = st.session_state.get(f"f_emp_{col}", "")
            if val:
                df_filt = df_filt[df_filt[col].astype(str).str.contains(val, case=False, na=False)]

        # 1.3) Eilučių atvaizdavimas su redagavimo mygtuku (be headerių po filtrų)
        for _, row in df_filt.iterrows():
            row_cols = st.columns(len(df_filt.columns) + 1)
            for i, col in enumerate(df_filt.columns):
                if col == "aktyvus":
                    row_cols[i].write("Taip" if row[col] == 1 else "Ne")
                else:
                    row_cols[i].write(row[col])
            row_cols[-1].button(
                "✏️",
                key=f"edit_emp_{row['id']}",
                on_click=start_edit,
                args=(row['id'],)
            )
        return

    # 2. DETALĖS / NAUJAS DARBUOTOJAS
    sel = st.session_state.selected_emp
    is_new = (sel == 0)
    emp_data = {}
    if not is_new:
        df_emp = pd.read_sql(
            "SELECT * FROM darbuotojai WHERE id=?", conn,
            params=(sel,)
        )
        if df_emp.empty:
            st.error("Darbuotojas nerastas.")
            clear_selection()
            return
        emp_data = df_emp.iloc[0]

    # Paruošiame pareigybių sąrašą
    pareigybes = ["Ekspedicijos vadybininkas", "Transporto vadybininkas"]

    # Iš DB gauname visų grupių sąrašą
    all_grupes_df = pd.read_sql_query("SELECT numeris FROM grupes ORDER BY numeris", conn)
    all_grupes = all_grupes_df["numeris"].tolist()

    # Padalijame grupes pagal prefiksus
    ekspedicijos_gr = [g for g in all_grupes if g.upper().startswith("EKSP")]
    transporto_gr  = [g for g in all_grupes if g.upper().startswith("TR")]

    # Formos dalys (trys stulpeliai viršuje, trys apačioje)
    cols1 = st.columns(3)
    cols2 = st.columns(3)

    # 1) Vardas
    cols1[0].text_input(
        "Vardas", key="vardas",
        value=("" if is_new else emp_data.get("vardas", ""))
    )
    # 2) Pavardė
    cols1[1].text_input(
        "Pavardė", key="pavarde",
        value=("" if is_new else emp_data.get("pavarde", ""))
    )
    # 3) Pareigybė – selectbox
    if is_new:
        default_pareigybe = pareigybes[0]
    else:
        default_pareigybe = emp_data.get("pareigybe", pareigybes[0])
    selected_pareigybe = cols1[2].selectbox(
        "Pareigybė", pareigybes, key="pareigybe",
        index=pareigybes.index(default_pareigybe)
    )

    # 4) El. paštas
    cols2[0].text_input(
        "El. paštas", key="el_pastas",
        value=("" if is_new else emp_data.get("el_pastas", ""))
    )
    # 5) Telefonas
    cols2[1].text_input(
        "Telefonas", key="telefonas",
        value=("" if is_new else emp_data.get("telefonas", ""))
    )

    # 6) Dinaminis grupių selectbox pagal pareigybę
    if selected_pareigybe == "Ekspedicijos vadybininkas":
        galimos_grupes = ekspedicijos_gr
    else:
        galimos_grupes = transporto_gr

    if is_new:
        default_grupe = galimos_grupes[0] if galimos_grupes else ""
    else:
        default_grupe = emp_data.get("grupe", galimos_grupes[0] if galimos_grupes else "")

    cols2[2].selectbox(
        "Grupė", galimos_grupes, key="grupe",
        index=galimos_grupes.index(default_grupe) if default_grupe in galimos_grupes else 0
    )

    # 7) Aktyvumo statusas – checkbox
    if is_new:
        default_status = True
    else:
        default_status = (emp_data.get("aktyvus", 1) == 1)
    aktivus_checkbox = st.checkbox(
        "Aktyvus darbuotojas", key="aktyvus", value=default_status
    )

    # 8) Išsaugojimo ir „Grįžti“ mygtukai
    def do_save():
        fields = ["vardas", "pavarde", "pareigybe", "el_pastas", "telefonas", "grupe"]
        vals = [st.session_state[key] for key in fields]
        # Aktyvumo reikšmė: 1 ar 0
        vals.append(1 if st.session_state["aktyvus"] else 0)
        if is_new:
            cols_sql     = ", ".join(fields + ["aktyvus"])
            placeholders = ", ".join("?" for _ in range(len(fields) + 1))
            c.execute(
                f"INSERT INTO darbuotojai ({cols_sql}) VALUES ({placeholders})",
                tuple(vals)
            )
        else:
            vals.append(sel)
            set_clause = ", ".join(f"{k}=?" for k in (fields + ["aktyvus"]))
            c.execute(
                f"UPDATE darbuotojai SET {set_clause} WHERE id=?",
                tuple(vals)
            )
        conn.commit()
        st.success("✅ Duomenys įrašyti.")
        clear_selection()

    btn_save, btn_back = st.columns(2)
    btn_save.button("💾 Išsaugoti darbuotoją", on_click=do_save)
    btn_back.button("🔙 Grįžti į sąrašą", on_click=clear_selection)
