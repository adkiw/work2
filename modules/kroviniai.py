import streamlit as st
import pandas as pd
from datetime import date, time, timedelta

EU_COUNTRIES = [
    ("", ""), ("Lietuva", "LT"), ("Baltarusija", "BY"), ("Latvija", "LV"), ("Lenkija", "PL"), ("Vokietija", "DE"),
    ("Prancūzija", "FR"), ("Ispanija", "ES"), ("Italija", "IT"), ("Olandija", "NL"), ("Belgija", "BE"),
    ("Austrija", "AT"), ("Švedija", "SE"), ("Suomija", "FI"), ("Čekija", "CZ"), ("Slovakija", "SK"),
    ("Vengrija", "HU"), ("Rumunija", "RO"), ("Bulgarija", "BG"), ("Danija", "DK"), ("Norvegija", "NO"),
    ("Šveicarija", "CH"), ("Kroatija", "HR"), ("Slovėnija", "SI"), ("Portugalija", "PT"), ("Graikija", "GR"),
    ("Airija", "IE"), ("Didžioji Britanija", "GB"),
]

HEADER_LABELS = {
    "id": "ID",
    "busena": "Būsena",
    "pakrovimo_data": "Pakr. data",
    "iskrovimo_data": "Iškr. data",
    "pakrovimo_vieta": "Pakr. vieta",
    "iskrovimo_vieta": "Iškr. vieta",
    "klientas": "Klientas",
    "vilkikas": "Vilkikas",
    "priekaba": "Priekaba",
    "ekspedicijos_vadybininkas": "Eksp. vadyb.",
    "transporto_vadybininkas": "Transp. vadyb.",
    "atsakingas_vadybininkas": "Atsak. vadyb.",
    "uzsakymo_numeris": "Užsak. nr.",
    "kilometrai": "Km",
    "frachtas": "Frachtas",
    "saskaitos_busena": "Sąskaitos būsena"
}

FIELD_ORDER = [
    "id", "busena", "pakrovimo_data", "iskrovimo_data",
    "pakrovimo_vieta", "iskrovimo_vieta",
    "klientas", "vilkikas", "priekaba", "ekspedicijos_vadybininkas",
    "transporto_vadybininkas", "atsakingas_vadybininkas",
    "uzsakymo_numeris", "kilometrai", "frachtas",
    "saskaitos_busena"
]

def get_busena(c, krovinys):
    if not krovinys.get("vilkikas"):
        return "Nesuplanuotas"
    if krovinys.get("vilkikas") == "":
        return "Nesuplanuotas"
    busena = "Suplanuotas"
    r = c.execute("""
        SELECT pakrovimo_statusas, iskrovimo_statusas
        FROM vilkiku_darbo_laikai
        WHERE vilkiko_numeris = ? AND data = ?
        ORDER BY id DESC LIMIT 1
    """, (krovinys['vilkikas'], krovinys['pakrovimo_data'])).fetchone()
    if not r:
        return busena
    pk_status, ik_status = r
    if ik_status == "Iškrauta":
        return "Iškrauta"
    if ik_status == "Atvyko":
        return "Atvyko į iškrovimą"
    if ik_status == "Kita" and pk_status != "Pakrauta":
        return "Kita (iškrovimas)"
    if pk_status == "Pakrauta":
        return "Pakrauta"
    if pk_status == "Atvyko":
        return "Atvyko į pakrovimą"
    if pk_status == "Kita":
        return "Kita (pakrovimas)"
    return busena

def get_vieta(salis, regionas):
    if not salis:
        return ""
    return f"{salis}{regionas or ''}"

def show(conn, c):
    st.title("Užsakymų valdymas")
    add_clicked = st.button("➕ Pridėti naują krovinį", use_container_width=True)

    # Įsitikinti, kad visi stulpeliai egzistuoja lentelėje 'kroviniai'
    expected = {
        'klientas': 'TEXT',
        'uzsakymo_numeris': 'TEXT',
        'pakrovimo_salis': 'TEXT',
        'pakrovimo_regionas': 'TEXT',
        'pakrovimo_miestas': 'TEXT',
        'pakrovimo_adresas': 'TEXT',
        'pakrovimo_data': 'TEXT',
        'pakrovimo_laikas_nuo': 'TEXT',
        'pakrovimo_laikas_iki': 'TEXT',
        'iskrovimo_salis': 'TEXT',
        'iskrovimo_regionas': 'TEXT',
        'iskrovimo_miestas': 'TEXT',
        'iskrovimo_adresas': 'TEXT',
        'iskrovimo_data': 'TEXT',
        'iskrovimo_laikas_nuo': 'TEXT',
        'iskrovimo_laikas_iki': 'TEXT',
        'vilkikas': 'TEXT',
        'priekaba': 'TEXT',
        'atsakingas_vadybininkas': 'TEXT',
        'ekspedicijos_vadybininkas': 'TEXT',
        'transporto_vadybininkas': 'TEXT',
        'kilometrai': 'INTEGER',
        'frachtas': 'REAL',
        'svoris': 'INTEGER',
        'paleciu_skaicius': 'INTEGER',
        'saskaitos_busena': 'TEXT',
        'busena': 'TEXT'
    }
    c.execute("PRAGMA table_info(kroviniai)")
    existing = {r[1] for r in c.fetchall()}
    for col, typ in expected.items():
        if col not in existing:
            c.execute(f"ALTER TABLE kroviniai ADD COLUMN {col} {typ}")
    conn.commit()

    klientai = [r[0] for r in c.execute("SELECT pavadinimas FROM klientai").fetchall()]
    if len(klientai) == 0:
        st.warning("Nėra nė vieno kliento! Pridėkite klientą modulyje **Klientai** ir grįžkite čia.")
        return

    vilkikai = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
    eksped_vadybininkai = [
        f"{r[0]} {r[1]}"
        for r in c.execute("SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe = ?", ("Ekspedicijos vadybininkas",)).fetchall()
    ]
    eksped_dropdown = [""] + eksped_vadybininkai
    vilkikai_df = pd.read_sql_query("SELECT numeris, vadybininkas FROM vilkikai", conn)
    vilk_vad_map = {r['numeris']: r['vadybininkas'] for _, r in vilkikai_df.iterrows()}

    df_klientai = pd.read_sql_query("SELECT pavadinimas, likes_limitas FROM klientai", conn)
    klientu_limitai = {row['pavadinimas']: row['likes_limitas'] for _, row in df_klientai.iterrows()}

    if 'selected_cargo' not in st.session_state:
        st.session_state['selected_cargo'] = None
    if add_clicked:
        st.session_state['selected_cargo'] = 0

    def clear_sel():
        st.session_state['selected_cargo'] = None
        for k in list(st.session_state):
            if k.startswith("f_"):
                st.session_state[k] = ""

    def edit_cargo(cid):
        st.session_state['selected_cargo'] = cid

    sel = st.session_state['selected_cargo']

    if sel is None:
        df = pd.read_sql_query("SELECT * FROM kroviniai", conn)
        if df.empty:
            st.info("Kol kas nėra krovinių.")
        else:
            df["pakrovimo_vieta"] = df.apply(lambda r: get_vieta(r.get('pakrovimo_salis', ''), r.get('pakrovimo_regionas', '')), axis=1)
            df["iskrovimo_vieta"] = df.apply(lambda r: get_vieta(r.get('iskrovimo_salis', ''), r.get('iskrovimo_regionas', '')), axis=1)
            df["transporto_vadybininkas"] = df["vilkikas"].map(vilk_vad_map).fillna("")
            df["atsakingas_vadybininkas"] = df["vilkikas"].map(vilk_vad_map).fillna("")
            busenos = []
            for _, row in df.iterrows():
                busenos.append(get_busena(c, row))
            df["busena"] = busenos

            df_disp = df[FIELD_ORDER].fillna("")

            filter_cols = st.columns(len(df_disp.columns) + 1)
            for i, col in enumerate(df_disp.columns):
                filter_cols[i].text_input(
                    " ",
                    key=f"f_{col}",
                    label_visibility="collapsed"
                )
            filter_cols[-1].write("")

            df_f = df_disp.copy()
            for col in df_disp.columns:
                v = st.session_state.get(f"f_{col}", "")
                if v:
                    df_f = df_f[df_f[col].astype(str).str.contains(v, case=False, na=False)]

            hdr = st.columns(len(df_disp.columns) + 1)
            for i, col in enumerate(df_disp.columns):
                label = HEADER_LABELS.get(col, col.replace("_", "<br>")[:14])
                hdr[i].markdown(f"<b>{label}</b>", unsafe_allow_html=True)
            hdr[-1].markdown("<b>Veiksmai</b>", unsafe_allow_html=True)

            for _, row in df_f.iterrows():
                row_cols = st.columns(len(df_disp.columns) + 1)
                for i, col in enumerate(df_disp.columns):
                    row_cols[i].write(row[col])
                row_cols[-1].button(
                    "✏️",
                    key=f"edit_{row['id']}",
                    on_click=edit_cargo,
                    args=(row['id'],)
                )

            st.download_button(
                "💾 Eksportuoti kaip CSV",
                data=df_disp.to_csv(index=False, sep=';').encode('utf-8'),
                file_name="kroviniai.csv",
                mime="text/csv"
            )
        return

    is_new = (sel == 0)
    data = {} if is_new else pd.read_sql_query("SELECT * FROM kroviniai WHERE id=?", conn, params=(sel,)).iloc[0]
    if not is_new and data.empty:
        st.error("Įrašas nerastas.")
        clear_sel()
        return

    st.markdown("### Krovinių įvedimas")
    colA, colB, colC, colD = st.columns(4)
    with st.form("cargo_form", clear_on_submit=False):
        opts_k = [""] + klientai
        idx_k = 0 if is_new else opts_k.index(data.get('klientas', ''))
        klientas = colA.selectbox("Klientas", opts_k, index=idx_k, key="kl_klientas")
        limito_likutis = klientu_limitai.get(klientas, "")
        if klientas:
            colA.info(f"Limito likutis: {limito_likutis}")
        uzsak = colA.text_input(
            "Užsakymo nr.",
            value=("" if is_new else data.get('uzsakymo_numeris', '')),
            key="kl_uzsak"
        )
        sask_busenos = ["Neapmokėta", "Apmokėta"]
        sask_busena_val = sask_busenos[0] if is_new else data.get("saskaitos_busena", sask_busenos[0])
        sask_busena = colA.selectbox("Sąskaitos būsena", sask_busenos, index=sask_busenos.index(sask_busena_val), key="sask_busena")

        eksped_val = "" if is_new else data.get('ekspedicijos_vadybininkas', "")
        eksped_idx = eksped_dropdown.index(eksped_val) if eksped_val in eksped_dropdown else 0
        eksped_vad = colA.selectbox("Ekspedicijos vadybininkas", eksped_dropdown, index=eksped_idx, key="eksped_vad")

        pk_data = colB.date_input(
            "Pakrovimo data",
            value=(date.today() if is_new else pd.to_datetime(data['pakrovimo_data']).date()),
            key="pk_data"
        )
        pk_salis_opts = [f"{n} ({c})" for n, c in EU_COUNTRIES]
        pk_salis_index = 0
        if not is_new:
            try:
                pk_salis_index = pk_salis_opts.index(next(x for x in pk_salis_opts if data.get('pakrovimo_salis', '') in x))
            except StopIteration:
                pass
        pk_salis = colB.selectbox("Pakrovimo šalis", pk_salis_opts, index=pk_salis_index, key="pk_sal")
        pk_regionas = colB.text_input(
            "Pakrovimo regionas",
            value=("" if is_new else data.get('pakrovimo_regionas', '')),
            key="pk_regionas"
        )
        pk_mie = colB.text_input(
            "Pakrovimo miestas",
            value=("" if is_new else data.get('pakrovimo_miestas', '')),
            key="pk_mie"
        )
        pk_adr = colB.text_input(
            "Pakrovimo adresas",
            value=("" if is_new else data.get('pakrovimo_adresas', '')),
            key="pk_adr"
        )
        pk_nuo = colB.time_input(
            "Pakrovimo laikas nuo",
            value=(time(8, 0) if is_new else pd.to_datetime(data.get('pakrovimo_laikas_nuo', "08:00")).time()),
            key="pk_nuo"
        )
        pk_iki = colB.time_input(
            "Pakrovimo laikas iki",
            value=(time(17, 0) if is_new else pd.to_datetime(data.get('pakrovimo_laikas_iki', "17:00")).time()),
            key="pk_iki"
        )

        isk_data = colC.date_input(
            "Iškrovimo data",
            value=((pk_data + timedelta(days=1)) if is_new else pd.to_datetime(data['iskrovimo_data']).date()),
            key="isk_data"
        )
        is_salis_opts = pk_salis_opts
        is_salis_index = 0
        if not is_new:
            try:
                is_salis_index = is_salis_opts.index(next(x for x in is_salis_opts if data.get('iskrovimo_salis', '') in x))
            except StopIteration:
                pass
        is_salis = colC.selectbox("Iškrovimo šalis", is_salis_opts, index=is_salis_index, key="is_sal")
        is_regionas = colC.text_input(
            "Iškrovimo regionas",
            value=("" if is_new else data.get('iskrovimo_regionas', '')),
            key="is_regionas"
        )
        is_mie = colC.text_input(
            "Iškrovimo miestas",
            value=("" if is_new else data.get('iskrovimo_miestas', '')),
            key="is_mie"
        )
        is_adr = colC.text_input(
            "Iškrovimo adresas",
            value=("" if is_new else data.get('iskrovimo_adresas', '')),
            key="is_adr"
        )
        is_nuo = colC.time_input(
            "Iškrovimo laikas nuo",
            value=(time(8, 0) if is_new else pd.to_datetime(data.get('iskrovimo_laikas_nuo', "08:00")).time()),
            key="is_nuo"
        )
        is_iki = colC.time_input(
            "Iškrovimo laikas iki",
            value=(time(17, 0) if is_new else pd.to_datetime(data.get('iskrovimo_laikas_iki', "17:00")).time()),
            key="is_iki"
        )

        v_opts = [""] + vilkikai
        v_idx = 0 if is_new else v_opts.index(data.get('vilkikas', ''))
        vilk = colD.selectbox("Vilkikas", v_opts, index=v_idx, key="cr_vilk")
        transp_vad = vilk_vad_map.get(vilk, "") if vilk else ""
        priekaba_value = ""
        if vilk:
            res = c.execute("SELECT priekaba FROM vilkikai WHERE numeris = ?", (vilk,)).fetchone()
            priekaba_value = res[0] if res and res[0] else ""
        colD.text_input("Priekaba", priekaba_value, disabled=True, key="cr_priek")
        km = colD.text_input(
            "Km",
            value=("" if is_new else str(data.get('kilometrai', 0))),
            key="cr_km"
        )
        fr = colD.text_input(
            "Frachtas (€)",
            value=("" if is_new else str(data.get('frachtas', 0))),
            key="cr_fr"
        )
        sv = colD.text_input(
            "Svoris (kg)",
            value=("" if is_new else str(data.get('svoris', 0))),
            key="cr_sv"
        )
        pal = colD.text_input(
            "Padėklų sk.",
            value=("" if is_new else str(data.get('paleciu_skaicius', 0))),
            key="cr_pal"
        )

        save = st.form_submit_button("💾 Išsaugoti")
        back = st.form_submit_button("🔙 Grįžti į sąrašą", on_click=clear_sel)

    if save:
        try:
            frachtas_float = float(fr.replace(",", ".") or 0)
        except:
            st.error("❌ Netinkamas frachtas. Įveskite skaičių.")
            return
        try:
            km_int = int(km or 0)
            sv_int = int(sv or 0)
            pal_int = int(pal or 0)
        except:
            st.error("❌ Netinkamas skaičius (Km / Svoris / Padėklai).")
            return

        if pk_data > isk_data:
            st.error("Pakrovimo data negali būti vėlesnė už iškrovimo.")
            return
        elif not klientas or not uzsak:
            st.error("Privalomi laukai: Klientas ir Užsakymo nr.")
            return
        else:
            if vilk:
                new_pk = pk_data.isoformat()
                new_isk = isk_data.isoformat()
                existing_overlap = c.execute("""
                    SELECT COUNT(*) FROM kroviniai
                    WHERE vilkikas = ?
                      AND id != ?
                      AND (? < iskrovimo_data)
                      AND (pakrovimo_data < ?)
                """, (vilk, sel, new_pk, new_isk)).fetchone()
                if existing_overlap and existing_overlap[0] > 0:
                    st.error("❌ Šis vilkikas jau turi krovinį su persidengiančiomis datomis. Patikrinkite įrašų datas.")
                    return

            vat_row = c.execute(
                "SELECT vat_numeris, coface_limitas FROM klientai WHERE pavadinimas = ?",
                (klientas,)
            ).fetchone()
            if not vat_row or not vat_row[0]:
                st.error("❌ Kliento VAT numeris nerastas arba tuščias.")
                return
            vat_of_client, coface_of_client = vat_row

            musu_limitas = coface_of_client / 3.0
            unpaid_sum = 0.0
            try:
                r = c.execute("""
                    SELECT SUM(k.frachtas)
                    FROM kroviniai AS k
                    JOIN klientai AS cl ON k.klientas = cl.pavadinimas
                    WHERE cl.vat_numeris = ?
                      AND k.saskaitos_busena != 'Apmokėta'
                """, (vat_of_client,)).fetchone()
                if r and r[0] is not None:
                    unpaid_sum = r[0]
            except:
                unpaid_sum = 0.0

            current_limit = musu_limitas - unpaid_sum
            if current_limit < 0:
                current_limit = 0.0

            # === Svarbiausia vieta (patobulintas limitų tikrinimas) ===
            if not is_new and (data.get('saskaitos_busena') != sask_busena) and sask_busena == "Apmokėta":
                pass
            else:
                if frachtas_float > current_limit:
                    st.error(f"Kliento limito likutis ({round(current_limit,2)}) yra mažesnis nei frachtas ({frachtas_float}). Negalima išsaugoti.")
                    return

            vals = {
                'klientas': klientas,
                'uzsakymo_numeris': uzsak,
                'pakrovimo_salis': pk_salis.split("(")[-1][:-1] if "(" in pk_salis else pk_salis,
                'pakrovimo_regionas': pk_regionas,
                'pakrovimo_miestas': pk_mie,
                'pakrovimo_adresas': pk_adr,
                'pakrovimo_data': pk_data.isoformat(),
                'pakrovimo_laikas_nuo': pk_nuo.isoformat(),
                'pakrovimo_laikas_iki': pk_iki.isoformat(),
                'iskrovimo_salis': is_salis.split("(")[-1][:-1] if "(" in is_salis else is_salis,
                'iskrovimo_regionas': is_regionas,
                'iskrovimo_miestas': is_mie,
                'iskrovimo_adresas': is_adr,
                'iskrovimo_data': isk_data.isoformat(),
                'iskrovimo_laikas_nuo': is_nuo.isoformat(),
                'iskrovimo_laikas_iki': is_iki.isoformat(),
                'vilkikas': vilk,
                'priekaba': priekaba_value,
                'atsakingas_vadybininkas': transp_vad,
                'ekspedicijos_vadybininkas': eksped_vad,
                'kilometrai': km_int,
                'frachtas': frachtas_float,
                'svoris': sv_int,
                'paleciu_skaicius': pal_int,
                'saskaitos_busena': sask_busena
            }

            try:
                if is_new:
                    cols = ",".join(vals.keys())
                    placeholders = ",".join(["?"] * len(vals))
                    q = f"INSERT INTO kroviniai ({cols}) VALUES ({placeholders})"
                    c.execute(q, tuple(vals.values()))
                else:
                    set_str = ",".join(f"{k}=?" for k in vals)
                    q = f"UPDATE kroviniai SET {set_str} WHERE id=?"
                    c.execute(q, tuple(vals.values()) + (sel,))
                conn.commit()

                unpaid_total = 0.0
                try:
                    r2 = c.execute("""
                        SELECT SUM(k.frachtas)
                        FROM kroviniai AS k
                        JOIN klientai AS cl ON k.klientas = cl.pavadinimas
                        WHERE cl.vat_numeris = ?
                          AND k.saskaitos_busena != 'Apmokėta'
                    """, (vat_of_client,)).fetchone()
                    if r2 and r2[0] is not None:
                        unpaid_total = r2[0]
                except:
                    unpaid_total = 0.0

                new_musu = coface_of_client / 3.0
                new_liks = new_musu - unpaid_total
                if new_liks < 0:
                    new_liks = 0.0

                c.execute("""
                    UPDATE klientai
                    SET musu_limitas = ?, likes_limitas = ?
                    WHERE vat_numeris = ?
                """, (new_musu, new_liks, vat_of_client))
                conn.commit()

                st.success("✅ Krovinys išsaugotas ir limitai atnaujinti.")
                clear_sel()
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
