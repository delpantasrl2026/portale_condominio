import hashlib
import sqlite3
import streamlit as st

DB_NAME = "condominio.db"


def genera_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


# --- INTERFACCIA GRAFICA WEB CON STREAMLIT ---

st.set_page_config(page_title="Portale Condominio", page_icon="🔥", layout="centered")

st.title("🏢 Portale Riscaldamento Condominiale")
st.write("Accedi per verificare i consumi del tuo appartamento.")

# Creiamo lo stato della sessione per ricordare se l'utente ha fatto il login
if "loggato" not in st.session_state:
    st.session_state.loggato = False
    st.session_state.username = ""
    st.session_state.ruolo = ""
    st.session_state.interno = ""

# --- SCHERMATA DI LOGIN ---
if not st.session_state.loggato:
    st.subheader("🔑 Login Utente")
    username_input = st.text_input("Nome Utente").strip().lower()
    password_input = st.text_input("Password", type="password").strip()

    if st.button("Accedi"):
        hash_inserito = genera_hash(password_input)

        # Controlliamo nel database esistente
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, ruolo, interno FROM utenti WHERE username = ? AND password_hash = ?",
            (username_input, hash_inserito),
        )
        utente = cursor.fetchone()
        conn.close()

        if utente:
            st.session_state.loggato = True
            st.session_state.username = utente[0]
            st.session_state.ruolo = utente[1]
            st.session_state.interno = utente[2]
            st.rerun()  # Ricarica la pagina per mostrare il menu corretto
        else:
            st.error("❌ Credenziali errate. Riprova.")

# --- SCHERMATA DOPO IL LOGIN ---
else:
    # Pulsante per uscire sempre visibile in alto a destra
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("Esci 🚪"):
            st.session_state.loggato = False
            st.rerun()

    with col1:
        st.success(
            f"Connesso come: **{st.session_state.username.upper()}** ({st.session_state.interno})"
        )

    # --- MENU AMMINISTRATORE ---
    if st.session_state.ruolo == "admin":
        st.markdown("### 🛠️ Pannello di Gestione Amministratore")

        menu = st.radio(
            "Cosa vuoi fare?",
            [
                "Registra nuovo Condòmino",
                "Inserisci Consumi",
                "Visualizza tutti i consumi",
            ],
        )

        if menu == "Registra nuovo Condòmino":
            new_user = (
                st.text_input("Username del nuovo condòmino").strip().lower()
            )
            new_pwd = st.text_input("Password temporanea", type="password").strip()
            new_int = st.text_input("Numero interno appartamento (es. Int. 4)").strip()

            if st.button("Salva Nuovo Utente"):
                if new_user and new_pwd:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "INSERT INTO utenti VALUES (?, ?, 'condomino', ?)",
                            (new_user, genera_hash(new_pwd), new_int),
                        )
                        conn.commit()
                        st.success(f"✔️ Condòmino {new_user} registrato!")
                    except sqlite3.IntegrityError:
                        st.error("❌ Questo username esiste già.")
                    finally:
                        conn.close()
                else:
                    st.warning("Compila tutti i campi.")

        elif menu == "Inserisci Consumi":
            # Recuperiamo la lista dei condomini per fare un menu a tendina
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username FROM utenti WHERE ruolo = 'condomino'"
            )
            lista_condomini = [r[0] for r in cursor.fetchall()]
            conn.close()

            if not lista_condomini:
                st.info("Non ci sono ancora condòmini registrati.")
            else:
                user_scelto = st.selectbox("Seleziona il Condòmino", lista_condomini)
                mese_scelto = st.selectbox(
                    "Seleziona il Mese",
                    [
                        "Gennaio 2026",
                        "Febbraio 2026",
                        "Marzo 2026",
                        "Novembre 2026",
                        "Dicembre 2026",
                    ],
                )
                scatti = st.number_input(
                    "Scatti/kWh consumati", min_value=0.0, step=1.0
                )

                if st.button("Registra Lettura"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO consumi (username, mese, scatti_riscaldamento) 
                        VALUES (?, ?, ?)
                        ON CONFLICT(username, mese) DO UPDATE SET scatti_riscaldamento = excluded.scatti_riscaldamento
                    """,
                        (user_scelto, mese_scelto, scatti),
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"✔️ Consumo aggiornato per {user_scelto}!")

        elif menu == "Visualizza tutti i consumi":
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT utenti.username, utenti.interno, consumi.mese, consumi.scatti_riscaldamento 
                FROM consumi 
                JOIN utenti ON consumi.username = utenti.username
            """)
            righe = cursor.fetchall()
            conn.close()

            if righe:
                # Mostriamo i dati in una comoda tabella web grafica
                st.dataframe(
                    righe,
                    columns=["Username", "Interno", "Mese", "Consumo (Scatti)"],
                )
            else:
                st.info("Nessun consumo inserito nel database.")

    # --- MENU CONDÒMINO ---
    elif st.session_state.ruolo == "condomino":
        st.markdown("### 📊 I Tuoi Consumi Personali")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT mese, scatti_riscaldamento FROM consumi WHERE username = ? ORDER BY mese DESC",
            (st.session_state.username,),
        )
        record = cursor.fetchall()
        conn.close()

        if record:
            st.write(
                "Ecco lo storico delle letture relative al tuo riscaldamento:"
            )
            st.dataframe(record, columns=["Mese di Riferimento", "Valore Letto"])
        else:
            st.info("ℹ️ Non ci sono ancora letture caricate per il tuo appartamento.")
