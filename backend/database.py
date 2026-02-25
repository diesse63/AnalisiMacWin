import sqlite3
import os

# --- VARIABILI GLOBALI ESPORTATE ---

# Imposta la cartella del database su ../db rispetto a questo file (cartella 'db' nella root dell'app)
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_FOLDER = os.path.join(APP_ROOT, "db")
if not os.path.exists(DB_FOLDER):
    try:
        os.makedirs(DB_FOLDER)
    except OSError as e:
        print(f"Errore creazione cartella dati: {e}")
DB_PATH = os.path.join(DB_FOLDER, "analisi.db")

def set_db_path(user_data_dir):
    """
    Imposta il percorso del database in una cartella scrivibile dall'utente.
    """
    global DB_PATH, DB_FOLDER
    
    # Cartella dedicata ai dati
    DB_FOLDER = os.path.join(user_data_dir, "AnalisiManagerData")
    
    if not os.path.exists(DB_FOLDER):
        try:
            os.makedirs(DB_FOLDER)
        except OSError as e:
            print(f"Errore creazione cartella dati: {e}")
            return

    DB_PATH = os.path.join(DB_FOLDER, "analisi.db")
    print(f"--- DATABASE SETUP ---")
    print(f"FOLDER: {DB_FOLDER}")
    print(f"FILE:   {DB_PATH}")
    print(f"----------------------")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS referti (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_inserimento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        nome_paziente TEXT,
        note TEXT,
        data_referto TEXT,
        numero_accettazione TEXT UNIQUE,
        file_path TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS risultati (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_referto INTEGER,
        nome_esame TEXT,
        risultato TEXT,
        unita_misura TEXT,
        riferimento TEXT,
        anomalia INTEGER, 
        FOREIGN KEY(id_referto) REFERENCES referti(id) ON DELETE CASCADE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS grafici (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_referto INTEGER,
        tipo_grafico TEXT,
        immagine BLOB,
        FOREIGN KEY(id_referto) REFERENCES referti(id) ON DELETE CASCADE
    )''')
    
    conn.commit()
    conn.close()

# --- SCRITTURA ---

def salva_referto(dati_testata, righe_esami, percorso_pdf_finale, immagine_grafico=None):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO referti (nome_paziente, note, data_referto, numero_accettazione, file_path) VALUES (?, ?, ?, ?, ?)",
              (dati_testata['paziente'], dati_testata.get('note', ''), dati_testata['data'], dati_testata['accettazione'], percorso_pdf_finale))
        id_referto = c.lastrowid
        
        dati_esami = []
        for riga in righe_esami:
            dati_esami.append((
                id_referto, riga['esame'], riga['risultato'], 
                riga['um'], riga['rif'], riga['anomalia']
            ))
        
        c.executemany('''INSERT INTO risultati 
                         (id_referto, nome_esame, risultato, unita_misura, riferimento, anomalia)
                         VALUES (?, ?, ?, ?, ?, ?)''', dati_esami)
            
        if immagine_grafico:
            c.execute("INSERT INTO grafici (id_referto, tipo_grafico, immagine) VALUES (?, ?, ?)",
                      (id_referto, "ELETTROFORESI", immagine_grafico))
        
        conn.commit()
        return True, "Referto archiviato con successo!"
        
    except sqlite3.IntegrityError:
        return False, f"Referto N. {dati_testata.get('accettazione')} già presente."
    except Exception as e:
        return False, f"Errore DB: {str(e)}"
    finally:
        conn.close()

def cancella_referto_completo(id_referto):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT file_path FROM referti WHERE id = ?", (id_referto,))
        res = c.fetchone()
        file_path = res['file_path'] if res else None

        c.execute("DELETE FROM referti WHERE id = ?", (id_referto,))
        conn.commit()
        
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        return True, "Referto eliminato."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def salva_testata(dati_testata, percorso_pdf_finale, immagine_grafico=None):
    """
    Salva solo la testata del referto (senza risultati). Restituisce (True, id_referto) oppure (False, msg)
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO referti (nome_paziente, note, data_referto, numero_accettazione, file_path) VALUES (?, ?, ?, ?, ?)",
                  (dati_testata.get('paziente', ''), dati_testata.get('note', ''), dati_testata.get('data', ''), dati_testata.get('accettazione', ''), percorso_pdf_finale))
        id_referto = c.lastrowid
        if immagine_grafico:
            c.execute("INSERT INTO grafici (id_referto, tipo_grafico, immagine) VALUES (?, ?, ?)",
                      (id_referto, "ELETTROFORESI", immagine_grafico))
        conn.commit()
        return True, id_referto
    except sqlite3.IntegrityError:
        return False, f"Referto N. {dati_testata.get('accettazione')} già presente."
    except Exception as e:
        return False, f"Errore DB: {str(e)}"
    finally:
        conn.close()


def salva_risultato(id_referto, riga):
    """Salva una singola riga risultato per un referto esistente. Restituisce (True, id_risultato) o (False, msg)"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO risultati (id_referto, nome_esame, risultato, unita_misura, riferimento, anomalia)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (id_referto, riga.get('esame', ''), riga.get('risultato', ''), riga.get('um', ''), riga.get('rif', ''), int(riga.get('anomalia', 0))))
        id_ris = c.lastrowid
        conn.commit()
        return True, id_ris
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def cancella_risultato(id_risultato):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM risultati WHERE id = ?", (id_risultato,))
        conn.commit()
        return True, "Risultato eliminato"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def verifica_esistenza_referto(numero_accettazione):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM referti WHERE numero_accettazione = ?", (numero_accettazione,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

# --- LETTURA ---

def get_tutti_i_dati_completi():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT r.data_referto, r.nome_paziente, r.note, res.nome_esame, res.risultato, 
               res.unita_misura, res.riferimento, res.anomalia, r.id as id_referto, r.numero_accettazione
        FROM risultati res
        JOIN referti r ON res.id_referto = r.id
        ORDER BY r.data_referto DESC, r.nome_paziente ASC
    ''')
    rows = c.fetchall()
    conn.close()
    
    return [{
        "data": r['data_referto'], "paziente": r['nome_paziente'], "note": r['note'],
        "esame": r['nome_esame'], "risultato": r['risultato'],
        "um": r['unita_misura'], "rif": r['riferimento'],
        "anomalia": r['anomalia'], "id_referto": r['id_referto'],
        "accettazione": r['numero_accettazione']
    } for r in rows]

def get_immagine_grafico(id_referto):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT immagine FROM grafici WHERE id_referto = ?", (id_referto,))
    res = c.fetchone()
    conn.close()
    return res['immagine'] if res else None