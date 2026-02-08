import streamlit as st
import pandas as pd
import os

# --- CONFIGURAZIONE ---
FILE_DB = 'manga_collection.csv'
COLONNE = ['Titolo', 'Ritmo', 'Stato', 'Vol_Tot_Jap', 'Vol_Usciti_Ita', 'Vol_Posseduti', 'Prezzo']

# --- FUNZIONI DI GESTIONE DATI ---
def carica_dati():
    if os.path.exists(FILE_DB):
        try:
            df = pd.read_csv(FILE_DB)
            
            # 1. MIGRAZIONE: Rimuoviamo i doppi prezzi se c'erano
            if 'Prezzo_Negozio' in df.columns:
                df['Prezzo'] = df['Prezzo_Negozio']
                df = df.drop(columns=['Prezzo_Pagato', 'Prezzo_Negozio'], errors='ignore')
            
            # 2. NUOVA COLONNA "RITMO" (Il Semaforo)
            if 'Ritmo' not in df.columns:
                df['Ritmo'] = "❓ N.D." # Default per i vecchi manga
            
            # Assicuriamoci che ci siano tutte le colonne
            for col in COLONNE:
                if col not in df.columns:
                    df[col] = 0 if col in ['Vol_Tot_Jap', 'Vol_Usciti_Ita', 'Vol_Posseduti', 'Prezzo'] else ""
            
            # 3. PULIZIA DATI NUMERICI
            cols_num = ['Vol_Tot_Jap', 'Vol_Usciti_Ita', 'Vol_Posseduti', 'Prezzo']
            for c in cols_num:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
            # 4. PULIZIA TESTO
            if 'Stato' in df.columns:
                df['Stato'] = df['Stato'].astype(str).str.title().str.strip()

            return df
        except:
            return pd.DataFrame(columns=COLONNE)
    return pd.DataFrame(columns=COLONNE)

def salva_dati(df):
    colonne_reali = [c for c in df.columns if c in COLONNE]
    df[colonne_reali].to_csv(FILE_DB, index=False)

# --- INTERFACCIA GRAFICA ---
st.set_page_config(page_title="Manga Manager", page_icon="📚", layout="wide")

st.title("🎌 Manga Manager")

# 1. Carichiamo i dati
df = carica_dati()

# 2. CALCOLI
if not df.empty:
    df['Da_Comprare'] = df['Vol_Usciti_Ita'] - df['Vol_Posseduti']
    df['Da_Comprare'] = df['Da_Comprare'].apply(lambda x: x if x > 0 else 0)
    
    # Costo Futuro
    df['Costo_Serie'] = df['Da_Comprare'] * df['Prezzo']

    # Progresso %
    def calcola_progresso(row):
        totale = row['Vol_Tot_Jap']
        posseduti = row['Vol_Posseduti']
        if totale <= 0: return 0.0
        perc = (posseduti / totale) * 100
        return min(perc, 100.0)

    df['Progresso'] = df.apply(calcola_progresso, axis=1)

    # --- ORDINAMENTO INTELLIGENTE ---
    priority_map = {"Concluso": 0, "In Corso": 1, "Hiatus": 2}
    df['_Sort_Priority'] = df['Stato'].map(priority_map).fillna(3)
    df = df.sort_values(by=['_Sort_Priority', 'Vol_Posseduti'], ascending=[True, False])
    df = df.drop(columns=['_Sort_Priority'])

# 3. Creiamo le SCHEDE
tab1, tab2, tab3 = st.tabs(["📋 La Mia Collezione", "➕ Aggiungi Nuovo", "📊 Statistiche"])

# --- TAB 1: LA LISTA INTERATTIVA ---
with tab1:
    st.subheader("La tua Libreria")
    
    col_filtro1, col_filtro2 = st.columns([1, 3])
    with col_filtro1:
        mostra_solo_mancanti = st.toggle("🛒 Mostra solo da comprare")
    
    df_visualizzato = df.copy()
    if mostra_solo_mancanti:
        df_visualizzato = df_visualizzato[df_visualizzato['Da_Comprare'] > 0]

    # TABELLA MODIFICABILE
    df_modificato = st.data_editor(
        df_visualizzato,
        column_config={
            "Titolo": st.column_config.TextColumn("Titolo", width="medium", required=True),
            
            # --- IL SEMAFORO DEL RITMO ---
            "Ritmo": st.column_config.SelectboxColumn(
                "Ritmo Uscite",
                width="small",
                options=[
                    "🟢 Regolare", 
                    "🟡 Lenta", 
                    "🔴 Irregolare", 
                    "⚫ Ferma", 
                    "✅ Finita",
                    "❓ N.D."
                ],
                required=True,
                help="Indica quanto spesso escono i volumi"
            ),
            
            "Stato": st.column_config.SelectboxColumn(
                "Stato", options=["Concluso", "In Corso", "Hiatus"], required=True
            ),
            "Vol_Tot_Jap": st.column_config.NumberColumn("Tot. Jap", min_value=0),
            "Vol_Usciti_Ita": st.column_config.NumberColumn("Usciti Ita", min_value=0),
            "Vol_Posseduti": st.column_config.NumberColumn("I Miei", min_value=0),
            
            "Prezzo": st.column_config.NumberColumn("Prezzo", format="%.2f €", min_value=0.0, step=0.1),
            
            "Progresso": st.column_config.ProgressColumn(
                "Completamento", format="%.0f%%", min_value=0, max_value=100
            ),
            
            "Da_Comprare": st.column_config.NumberColumn("Mancanti", format="%d 🛒", disabled=True),
            "Costo_Serie": st.column_config.NumberColumn("Spesa Futura", format="%.2f €", disabled=True),
        },
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        # Ordine colonne: Ritmo subito dopo Titolo per dare l'idea del colore!
        column_order=[
            "Titolo", "Ritmo", "Stato", "Vol_Tot_Jap", "Vol_Usciti_Ita", 
            "Vol_Posseduti", "Prezzo", "Mancanti", "Costo_Serie", "Progresso"
        ]
    )

    if not mostra_solo_mancanti: 
        colonne_reali = [c for c in COLONNE]
        dataset_originale = df[colonne_reali].reset_index(drop=True)
        dataset_modificato = df_modificato[colonne_reali].reset_index(drop=True)

        if not dataset_modificato.equals(dataset_originale):
            salva_dati(df_modificato)
            st.rerun()

# --- TAB 2: AGGIUNTA MANUALE ---
with tab2:
    st.write("Inserisci qui i dati di un nuovo manga.")
    
    with st.form("form_aggiunta"):
        c1, c2 = st.columns([2, 1])
        nuovo_titolo = c1.text_input("Titolo Manga")
        # Anche qui puoi scegliere subito il colore
        nuovo_ritmo = c2.selectbox("Ritmo", ["🟢 Regolare", "🟡 Lenta", "🔴 Irregolare", "✅ Finita"])
        
        c3, c4 = st.columns(2)
        nuovo_stato = c3.selectbox("Stato", ["Concluso", "In Corso", "Hiatus"])
        n_prezzo = c4.number_input("Prezzo Copertina (€)", min_value=0.0, step=0.10, value=5.90)
        
        c5, c6, c7 = st.columns(3)
        n_jap = c5.number_input("Vol. Giappone", min_value=0, step=1)
        n_ita = c6.number_input("Vol. Italia", min_value=0, step=1)
        n_miei = c7.number_input("Vol. Posseduti", min_value=0, step=1)
        
        submitted = st.form_submit_button("Salva Manga")
        
        if submitted:
            if nuovo_titolo:
                nuova_riga = pd.DataFrame([{
                    'Titolo': nuovo_titolo,
                    'Ritmo': nuovo_ritmo,
                    'Stato': nuovo_stato,
                    'Vol_Tot_Jap': n_jap,
                    'Vol_Usciti_Ita': n_ita,
                    'Vol_Posseduti': n_miei,
                    'Prezzo': n_prezzo
                }])
                df = pd.concat([df, nuova_riga], ignore_index=True)
                salva_dati(df)
                st.success(f"✅ {nuovo_titolo} aggiunto!")
                st.rerun()
            else:
                st.warning("⚠️ Devi inserire almeno un titolo!")

# --- TAB 3: STATISTICHE ---
with tab3:
    st.header("📊 Statistiche Libreria")
    
    if not df.empty:
        tot_volumi = df['Vol_Posseduti'].sum()
        spesa_futura = df['Costo_Serie'].sum()
        
        # Stima valore usato (semplificato 60%)
        valore_nuovo = (df['Vol_Posseduti'] * df['Prezzo']).sum()
        valore_usato = valore_nuovo * 0.60 
        
        colA, colB, colC = st.columns(3)
        colA.metric("📚 Volumi totali", tot_volumi)
        colB.metric("💎 Stima Usato", f"{valore_usato:.2f} €")
        colC.metric("💸 Serve per finire", f"{spesa_futura:.2f} €", delta_color="inverse")
        
        st.divider()
        st.subheader("Top 5 Completamento")
        
        df_progress = df.sort_values(by='Progresso', ascending=False).head(5)
        
        st.dataframe(
            df_progress[['Titolo', 'Ritmo', 'Progresso']],
            column_config={
                "Progresso": st.column_config.ProgressColumn(
                    "Completamento", format="%.0f%%", min_value=0, max_value=100
                )
            },
            hide_index=True,
            use_container_width=True
        )

    else:
        st.info("Nessun dato disponibile.")