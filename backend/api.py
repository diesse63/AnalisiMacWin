def delete_referto(id_referto):
    try:
        success, msg = database.cancella_referto_completo(id_referto)
        return jsonify({"success": success, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
import sys
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import database
import pdf_parser
import base64

app = Flask(__name__)
CORS(app)


# SETUP PERCORSI: il database e i PDF sono sempre nella cartella 'db' nella root dell'applicazione
database.init_db()


@app.route('/referti/<int:id_referto>', methods=['DELETE'])
def delete_referto(id_referto):
    try:
        success, msg = database.cancella_referto_completo(id_referto)
        return jsonify({"success": success, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "ok", "db": database.DB_PATH})

@app.route('/upload', methods=['POST'])
def upload_referto():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Nessun file inviato"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "Nome file vuoto"}), 400

    # Usa la cartella definita nel database
    temp_path = os.path.join(database.DB_FOLDER, "temp_upload.pdf")
    

    try:
        file.save(temp_path)

        righe_json = request.form.get('righe')
        if righe_json:
            import json
            righe_esami = json.loads(righe_json)
            # Recupera i dati principali dal PDF per metadata
            metadata, _, img_bytes = pdf_parser.estrai_dati_pdf(temp_path)
        else:
            metadata, righe_esami, img_bytes = pdf_parser.estrai_dati_pdf(temp_path)

        note_val = request.form.get('note', '')
        metadata['note'] = note_val

        if not righe_esami:
            return jsonify({"success": False, "message": "Nessun dato trovato nel PDF."})

        accettazione = metadata.get('accettazione', 'unknown').replace('/', '_')
        if database.verifica_esistenza_referto(accettazione):
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({
                "success": False,
                "message": f"Referto N. {accettazione} già presente in archivio. Per modificare i dati è necessario eliminare il referto esistente e reinserirlo."
            })

        final_pdf_name = f"{accettazione}.pdf"
        final_pdf_path = os.path.join(database.DB_FOLDER, final_pdf_name)

        if os.path.exists(final_pdf_path):
            os.remove(final_pdf_path)
        os.replace(temp_path, final_pdf_path)

        success, msg = database.salva_referto(metadata, righe_esami, final_pdf_path, img_bytes)

        return jsonify({"success": success, "message": msg})
        success, msg = database.salva_referto(metadata, righe_esami, final_pdf_path, img_bytes)

        return jsonify({"success": success, "message": msg})

    except Exception as e:
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
        return jsonify({"success": True, "dati": dati, "image": img_b64, "metadata": metadata})
    except Exception as e:
        return jsonify({"success": False, "message": f"Errore server: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)