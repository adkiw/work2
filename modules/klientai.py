import streamlit as st
import pandas as pd

def show(conn, c):
    # 1. Užtikrinti, kad egzistuotų reikiami stulpeliai
    expected = {
        'vat_numeris':          'TEXT',
        'kontaktinis_asmuo':    'TEXT',
        'kontaktinis_el_pastas':'TEXT',
        'kontaktinis_tel':      'TEXT',
        'salis':                'TEXT',
        'regionas':             'TEXT',
        'miestas':              'TEXT',
        'adresas':              'TEXT',
        'saskaitos_asmuo':      'TEXT',
        'saskaitos_el_pastas':  'TEXT',
        'saskaitos_tel':        'TEXT',
        'coface_limitas':       'REAL',
        'musu_limitas':         'REAL',
        'likes_limitas':        'REAL',
    }
    c.execute("PRAGMA table_info(klientai)")
    existing = {r[1] for r in c.fetchall()}
    for col, typ in expected.items():
        if col not in existing:
            c.execute(f"ALTER TABLE klientai ADD COLUMN {col} {typ}")
    conn.commit()

    # Atgaliniai kvietimai
    def clear_selection():
        st.session_state.selected_client = None

    def start_new():
        st.session_state.selected_client = 0

    def start_edit(cid):
        st.session_state.selected_client = cid

    # 2. Antraštė + „Pridėti naują klientą“ mygtukas
    title_col, add_col = st.columns([9, 1])
    title_col.title("Klientai")
    add_col.button("➕ Pridėti naują klientą", on_click=start_new)

    # 3. Būsenos inicializavimas
    if 'selected_client' not in st.session_state:
        st.session_state.selected_client = None

    # 4. Sąrašo rodinys (be antraščių virš ir po filtrų; filtrų laukeliai su vietos žymėmis)
    if st.session_state.selected_client is None:
        # Užkrauti duomenis
        df = pd.read_sql(
            "SELECT id, pavadinimas, salis, regionas, miestas, likes_limitas AS limito_likutis FROM klientai",
            conn
        )
        if df.empty:
            st.info("ℹ️ Nėra klientų.")
            return

        # Pakeisti NaN į tuščias eilutes rodymui
        df = df.fillna('')

        # Filtrai su vietos žymėmis (be antraščių virš ar po)
        filter_cols = st.columns(len(df.columns) + 1)
        for i, col in enumerate(df.columns):
            filter_cols[i].text_input(label="", placeholder=col, key=f"f_{col}")
        filter_cols[-1].write("")

        # Filtrų taikymas
        df_filt = df.copy()
        for col in df.columns:
            val = st.session_state.get(f"f_{col}", "")
            if val:
                df_filt = df_filt[df_filt[col].astype(str).str.contains(val, case=False, na=False)]

        # Duomenų eilutės su redagavimo mygtuku (be antraštės)
        for _, row in df_filt.iterrows():
            row_cols = st.columns(len(df_filt.columns) + 1)
            for i, col in enumerate(df_filt.columns):
                row_cols[i].write(row[col])
            row_cols[-1].button(
                "✏️",
                key=f"edit_{row['id']}",
                on_click=start_edit,
                args=(row['id'],)
            )
        return

    # 5. Detali forma / naujas įrašas
    sel = st.session_state.selected_client
    is_new = (sel == 0)
    cli = {}
    if not is_new:
        df_cli = pd.read_sql("SELECT * FROM klientai WHERE id=?", conn, params=(sel,))
        if df_cli.empty:
            st.error("Klientas nerastas.")
            clear_selection()
            return
        cli = df_cli.iloc[0]

    st.markdown("### Kliento duomenys")
    # Sukurti žemėlapį: esamas PVM numeris → coface_limitas
    existing_vats = {
        row['vat_numeris']: row['coface_limitas']
        for _, row in pd.read_sql("SELECT vat_numeris, coface_limitas FROM klientai", conn).iterrows()
        if row['vat_numeris']
    }

    # 6. Formos laukai (PVM privalomas; COFACE limitas įvedamas ranka)
    col1, col2 = st.columns(2)
    with st.form("client_form", clear_on_submit=False):
        pavadinimas = col1.text_input(
            "Įmonės pavadinimas",
            value=("" if is_new else cli.get("pavadinimas", "")),
            key="pavadinimas"
        )
        vat_default = "" if is_new else cli.get("vat_numeris", "")
        vat_numeris = col1.text_input(
            "PVM/VAT numeris *",
            value=vat_default,
            key="vat_numeris"
        )
        kontaktinis_asmuo = col1.text_input(
            "Kontaktinis asmuo",
            value=("" if is_new else cli.get("kontaktinis_asmuo", "")),
            key="kontaktinis_asmuo"
        )
        kontaktinis_el_pastas = col1.text_input(
            "Kontaktinis el. paštas",
            value=("" if is_new else cli.get("kontaktinis_el_pastas", "")),
            key="kontaktinis_el_pastas"
        )
        kontaktinis_tel = col1.text_input(
            "Kontaktinis tel. nr",
            value=("" if is_new else cli.get("kontaktinis_tel", "")),
            key="kontaktinis_tel"
        )
        salis = col1.text_input(
            "Šalis",
            value=("" if is_new else cli.get("salis", "")),
            key="salis"
        )
        regionas = col1.text_input(
            "Regionas",
            value=("" if is_new else cli.get("regionas", "")),
            key="regionas"
        )
        miestas = col1.text_input(
            "Miestas",
            value=("" if is_new else cli.get("miestas", "")),
            key="miestas"
        )
        adresas = col1.text_input(
            "Adresas",
            value=("" if is_new else cli.get("adresas", "")),
            key="adresas"
        )

        saskaitos_asmuo = col2.text_input(
            "Sąskaitų kontaktinis asmuo",
            value=("" if is_new else cli.get("saskaitos_asmuo", "")),
            key="saskaitos_asmuo"
        )
        saskaitos_el_pastas = col2.text_input(
            "Sąskaitų el. paštas",
            value=("" if is_new else cli.get("saskaitos_el_pastas", "")),
            key="saskaitos_el_pastas"
        )
        saskaitos_tel = col2.text_input(
            "Sąskaitų tel. nr",
            value=("" if is_new else cli.get("saskaitos_tel", "")),
            key="saskaitos_tel"
        )

        # Jeigu PVM numeris jau egzistuoja ir kuriamas naujas klientas, iš anksto užpildyti COFACE limitą
        coface_prefill = ""
        if is_new and vat_default == "" and st.session_state.get("vat_numeris", "") in existing_vats:
            coface_prefill = str(existing_vats[st.session_state["vat_numeris"]])
        elif not is_new:
            coface_prefill = str(cli.get("coface_limitas", ""))

        coface_limitas = col2.text_input(
            "COFACE limitas",
            value=coface_prefill,
            key="coface_limitas"
        )

        # Apskaičiuoti „Mūsų limitą“ ir „Limito likutį“ (tik skaitymui)
        def compute_limits(vat, coface):
            try:
                coface_val = float(coface)
            except:
                return "", ""
            musu = coface_val / 3.0
            # Jei lentelės 'kroviniai' nėra, unpaid_sum = 0
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='kroviniai'")
            if not c.fetchone():
                unpaid_sum = 0.0
            else:
                try:
                    r = c.execute("""
                        SELECT SUM(k.frachtas) 
                        FROM kroviniai AS k
                        JOIN klientai AS cl ON k.klientas = cl.pavadinimas
                        WHERE cl.vat_numeris = ? 
                          AND k.saskaitos_busena != 'Apmokėta'
                    """, (vat,)).fetchone()
                    unpaid_sum = r[0] if r and r[0] is not None else 0.0
                except:
                    unpaid_sum = 0.0
            liks = musu - unpaid_sum
            if liks < 0:
                liks = 0.0
            return round(musu, 2), round(liks, 2)

        musu_limitas_display = ""
        liks_display = ""
        if st.session_state.get("vat_numeris", "") and st.session_state.get("coface_limitas", ""):
            m, l = compute_limits(st.session_state["vat_numeris"], st.session_state["coface_limitas"])
            musu_limitas_display = str(m)
            liks_display = str(l)

        col2.markdown(f"**Mūsų limitas (COFACE/3):** {musu_limitas_display}")
        col2.markdown(f"**Limito likutis:** {liks_display}")

        save = st.form_submit_button("💾 Išsaugoti")
        back = st.form_submit_button("🔙 Grįžti į sąrašą", on_click=clear_selection)

    # 7. Išsaugojimo / Grįžimo logika
    if save:
        # Validavimas: PVM numeris privalomas
        if not st.session_state["vat_numeris"].strip():
            st.error("❌ PVM/VAT numeris yra privalomas.")
            return

        # COFACE konvertavimas į skaičių
        try:
            coface_val = float(st.session_state["coface_limitas"])
        except:
            st.error("❌ Netinkamas COFACE limitas. Įveskite skaičių.")
            return

        # Apskaičiuoti Mūsų limitą ir limito likutį šiam PVM
        musu_limitas_calc, liks_calc = compute_limits(
            st.session_state["vat_numeris"], 
            st.session_state["coface_limitas"]
        )

        vals = {
            'pavadinimas':         st.session_state["pavadinimas"],
            'vat_numeris':         st.session_state["vat_numeris"],
            'kontaktinis_asmuo':   st.session_state["kontaktinis_asmuo"],
            'kontaktinis_el_pastas':st.session_state["kontaktinis_el_pastas"],
            'kontaktinis_tel':     st.session_state["kontaktinis_tel"],
            'salis':               st.session_state["salis"],
            'regionas':            st.session_state["regionas"],
            'miestas':             st.session_state["miestas"],
            'adresas':             st.session_state["adresas"],
            'saskaitos_asmuo':     st.session_state["saskaitos_asmuo"],
            'saskaitos_el_pastas': st.session_state["saskaitos_el_pastas"],
            'saskaitos_tel':       st.session_state["saskaitos_tel"],
            'coface_limitas':      coface_val,
            'musu_limitas':        musu_limitas_calc,
            'likes_limitas':       liks_calc
        }

        try:
            if is_new:
                cols_sql = ", ".join(vals.keys())
                ph = ", ".join("?" for _ in vals)
                c.execute(f"INSERT INTO klientai ({cols_sql}) VALUES ({ph})", tuple(vals.values()))
            else:
                vals_list = list(vals.values()) + [sel]
                sc = ", ".join(f"{k}=?" for k in vals.keys())
                c.execute(f"UPDATE klientai SET {sc} WHERE id=?", tuple(vals_list))
            conn.commit()

            # Išsaugojus / atnaujinus, atnaujinti visus klientus su tuo pačiu PVM:
            vat = st.session_state["vat_numeris"]
            # Perskaičiuoti neapmokėto frachto sumą šiam PVM
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='kroviniai'")
            if not c.fetchone():
                unpaid_total = 0.0
            else:
                try:
                    r2 = c.execute("""
                        SELECT SUM(k.frachtas)
                        FROM kroviniai AS k
                        JOIN klientai AS cl ON k.klientas = cl.pavadinimas
                        WHERE cl.vat_numeris = ?
                          AND k.saskaitos_busena != 'Apmokėta'
                    """, (vat,)).fetchone()
                    unpaid_total = r2[0] if r2 and r2[0] is not None else 0.0
                except:
                    unpaid_total = 0.0
            new_musu = coface_val / 3.0
            new_liks = new_musu - unpaid_total
            if new_liks < 0:
                new_liks = 0.0

            # Atnaujinti visus įrašus, kurių vat_numeris = vat
            c.execute("""
                UPDATE klientai
                SET coface_limitas = ?, musu_limitas = ?, likes_limitas = ?
                WHERE vat_numeris = ?
            """, (coface_val, new_musu, new_liks, vat))
            conn.commit()

            st.success("✅ Duomenys įrašyti ir limitai atnaujinti visiems su tuo pačiu VAT numeriu.")
            clear_selection()
        except Exception as e:
            st.error(f"❌ Klaida: {e}")
