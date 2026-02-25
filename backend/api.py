import sys
import os
import json
import base64
from flask import Flask, jsonify, request
from flask_cors import CORS

# Moduli interni
import database
import pdf_parser

app = Flask(__name__)
CORS(app)

# -------------------------------------------------------------------------
# CONFIGURAZIONE PERCORSI (Supporto Portable)
# -------------------------------------------------------------------------
# Default: cartella corrente + 'db'
BASE_DIR = os.getcwd()

# Se Electron passa l'argomento --data-dir, usiamo quello
if '--data-dir' in sys.argv:
    try:
        idx = sys.argv.index('--data-dir')
        if idx + 1 < len(sys.argv):
            arg_path = sys.argv[idx + 1]
            # Verifica base che il path non sia vuoto o "undefined"
            if arg_path and arg_path != 'undefined':
                BASE_DIR = arg_path
                print(f"[BACKEND] Utilizzo data-dir personalizzata: {BASE_DIR}")
    except ValueError:
        pass

# Definisco la cartella 'db' dentro il percorso base
DB_FOLDER = os.path.join(BASE_DIR, 'db')

# Creo la cartella se non esiste
if not os.path.exists(DB_FOLDER):
    try:
        os.makedirs(DB_FOLDER)
        print(f"[BACKEND] Creata cartella DB: {DB_FOLDER}")
    except Exception as e:
        print(f"[BACKEND] Errore creazione cartella {DB_FOLDER}: {e}")

# INIETTO I PERCORSI NEL MODULO DATABASE
# Assicurati che database.py usi queste variabili o le accetti in init_db
database.DB_FOLDER = DB_FOLDER
database.DB_PATH = os.path.join(DB_FOLDER, 'database.sqlite')

# Inizializzo il DB
database.init_db()

# -------------------------------------------------------------------------
# ROTTE API
# -------------------------------------------------------------------------

@app.route('/status', methods=['GET'])
def status():
    """Restituisce lo stato e il percorso del DB in uso (utile per debug)"""
    return jsonify({
        "status": "ok", 
        "db_folder": database.DB_FOLDER,
        "db_file": database.DB_PATH
    })

@app.route('/referti/<int:id_referto>', methods=['DELETE'])
def delete_referto(id_referto):
    try:
        success, msg = database.cancella_referto_completo(id_referto)
        return jsonify({"success": success, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_referto():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Nessun file inviato"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "Nome file vuoto"}), 400

    # Percorso temporaneo per l'analisi
    temp_path = os.path.join(database.DB_FOLDER, "temp_upload.pdf")
    
    try:
        file.save(temp_path)

        # Se arrivano righe modificate dal frontend
        righe_json = request.form.get('righe')
        
        if righe_json:
            righe_esami = json.loads(righe_json)
            # Recupera solo metadata e immagine, i dati tabelle li abbiamo dal frontend
            metadata, _, img_bytes = pdf_parser.estrai_dati_pdf(temp_path)
        else:
            # Estrazione completa da zero
            metadata, righe_esami, img_bytes = pdf_parser.estrai_dati_pdf(temp_path)

        # Aggiunta note manuali
        note_val = request.form.get('note', '')
        metadata['note'] = note_val

        if not righe_esami:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({"success": False, "message": "Nessun dato trovato nel PDF."})

        accettazione = metadata.get('accettazione', 'unknown').replace('/', '_')
        
        # Controllo duplicati
        if database.verifica_esistenza_referto(accettazione):
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({
                "success": False,
                "message": f"Referto N. {accettazione} già presente in archivio. Eliminare quello esistente prima di reinserirlo."
            })

        # Spostamento definitivo del PDF
        final_pdf_name = f"{accettazione}.pdf"
        final_pdf_path = os.path.join(database.DB_FOLDER, final_pdf_name)

        if os.path.exists(final_pdf_path):
            os.remove(final_pdf_path)
            
        os.replace(temp_path, final_pdf_path)

        # Salvataggio nel DB
        success, msg = database.salva_referto(metadata, righe_esami, final_pdf_path, img_bytes)

        return jsonify({"success": success, "message": msg})

    except Exception as e:
        # Pulizia in caso di errore
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        return jsonify({"success": False, "message": f"Errore server: {str(e)}"}), 500

@app.route('/referti', methods=['GET'])
def get_referti():
    try:
        dati = database.get_tutti_i_dati_completi()
        return jsonify(dati)
    except Exception as e:
        return jsonify([])

@app.route('/grafico/<int:id_referto>', methods=['GET'])
def get_grafico(id_referto):
    try:
        img_blob = database.get_immagine_grafico(id_referto)
        if img_blob:
            img_b64 = base64.b64encode(img_blob).decode('utf-8')
            return jsonify({"image": img_b64})
        return jsonify({"image": None})
    except Exception:
        return jsonify({"image": None})


@app.route('/save_header', methods=['POST'])
def save_header():
    # Salva solo i dati generali del referto (testata) e il PDF inviato
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Nessun file inviato"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "Nome file vuoto"}), 400

    temp_path = os.path.join(database.DB_FOLDER, "temp_header.pdf")
    try:
        file.save(temp_path)

        # Lettura campi testata
        paziente = request.form.get('paziente', '')
        accettazione = request.form.get('accettazione', '')
        data_ref = request.form.get('data', '')
        note = request.form.get('note', '')
        image_b64 = request.form.get('image', None)

        acc_clean = accettazione.replace('/', '_') if accettazione else (str(int(os.times()[4])))
        # Controllo duplicati
        if accettazione and database.verifica_esistenza_referto(accettazione):
            if os.path.exists(temp_path): os.remove(temp_path)
            return jsonify({"success": False, "message": f"Referto N. {accettazione} già presente in archivio."})

        final_pdf_name = f"{acc_clean}.pdf"
        final_pdf_path = os.path.join(database.DB_FOLDER, final_pdf_name)
        if os.path.exists(final_pdf_path):
            os.remove(final_pdf_path)
        os.replace(temp_path, final_pdf_path)

        immagine_bytes = None
        if image_b64:
            try:
                immagine_bytes = base64.b64decode(image_b64)
            except Exception:
                immagine_bytes = None

        dati_testata = {'paziente': paziente, 'accettazione': accettazione, 'data': data_ref, 'note': note}
        success, result = database.salva_testata(dati_testata, final_pdf_path, immagine_bytes)
        if success:
            return jsonify({"success": True, "id_referto": result})
        else:
            return jsonify({"success": False, "message": result})

    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        return jsonify({"success": False, "message": f"Errore server: {str(e)}"}), 500


@app.route('/risultato', methods=['POST'])
def save_risultato():
    try:
        data = request.get_json()
        id_referto = int(data.get('id_referto'))
        riga = data.get('riga')
        success, res = database.salva_risultato(id_referto, riga)
        if success:
            return jsonify({"success": True, "id_risultato": res})
        else:
            return jsonify({"success": False, "message": res})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/risultato/<int:id_risultato>', methods=['DELETE'])
def delete_risultato(id_risultato):
    try:
        success, msg = database.cancella_risultato(id_risultato)
        return jsonify({"success": success, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/grafico', methods=['POST'])
def save_grafico():
    try:
        data = request.get_json()
        id_referto = int(data.get('id_referto'))
        image_b64 = data.get('image')
        if not image_b64:
            return jsonify({"success": False, "message": "Immagine mancante"}), 400
        img_bytes = base64.b64decode(image_b64)
        conn = database.get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO grafici (id_referto, tipo_grafico, immagine) VALUES (?, ?, ?)", (id_referto, 'ELETTROFORESI', img_bytes))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/upload_preview', methods=['POST'])
def upload_preview():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Nessun file inviato"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "Nome file vuoto"}), 400

    temp_path = os.path.join(database.DB_FOLDER, "temp_preview.pdf")
    
    try:
        file.save(temp_path)
        metadata, righe_uniche, img_bytes = pdf_parser.estrai_dati_pdf(temp_path)
        
        # Rimuovo il file temp subito dopo l'analisi per la preview
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        dati = []
        for r in righe_uniche:
            dati.append({
                "data": metadata.get("data", ""),
                "paziente": metadata.get("paziente", ""),
                "esame": r.get("esame", ""),
                "risultato": r.get("risultato", ""),
                "um": r.get("um", ""),
                "rif": r.get("rif", ""),
                "anomalia": r.get("anomalia", 0),
                "archiviato": r.get("archiviato", False),
                "idx": r.get("idx", -1),
                "linea": r.get("linea", "")
            })
            
        img_b64 = None
        if img_bytes:
            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
            
        return jsonify({
            "success": True, 
            "dati": dati, 
            "image": img_b64, 
            "metadata": metadata
        })
    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        return jsonify({"success": False, "message": f"Errore server: {str(e)}"}), 500

if __name__ == '__main__':
    # Avvio server
    print(f"[BACKEND] Server avviato. Cartella dati: {database.DB_FOLDER}")
    app.run(host='127.0.0.1', port=5000)