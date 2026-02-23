import pdfplumber
import fitz  # PyMuPDF
import re
import os

def estrai_dati_pdf(pdf_path):
    print(f"--- INIZIO PARSING: {pdf_path} ---")
    righe_uniche = []
    metadata = {"paziente": "Sconosciuto", "note": "", "data": "", "accettazione": "SenzaNum"}
    img_bytes = None
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                if page.page_number == 1:
                    lines = text.split('\n')
                    # Estrazione nome paziente e data referto (logica precedente)
                    for line in lines:
                        if re.search(r"accettazione\s*n\.", line, re.IGNORECASE):
                            m_data = re.search(r"del\s*(\d{2}-\d{2}-\d{4})", line)
                            if m_data:
                                metadata["data"] = m_data.group(1)
                        if "Data Nascita" in line and ("sesso M" in line or "sesso F" in line):
                            m_paz = re.search(r"sesso [MF] (.+)$", line)
                            if m_paz:
                                metadata["paziente"] = m_paz.group(1).strip()
                lines = text.split('\n')
                for idx, line in enumerate(lines):
                    line_orig = line
                    line = line.strip()
                    if not line: continue
                    parole_ignorate = ["Pag.", "Direttore", "Riferimento:", "Accettazione N.", "Campione del", "Data Nascita", "Reparto", "Modalità", "Descrizione Esame", "Int.rif"]
                    if any(x in line for x in parole_ignorate): continue
                    anomalia = 0
                    if "**" in line:
                        anomalia = 2
                        line = line.replace("**", " ")
                    elif "*" in line:
                        anomalia = 1
                        line = line.replace("*", " ")
                    line_clean = " ".join(line.split())
                    esame = None
                    risultato = None
                    um = ""
                    rif = ""
                    match_trovato = False
                    pat_std = r"^(.*?) ([\d\.,<>]+) ([^\[\s]+) (\[.*)$"
                    match = re.search(pat_std, line_clean)
                    if match:
                        esame, risultato, um, rif = match.group(1).strip(), match.group(2).strip(), match.group(3).strip(), match.group(4).strip()
                        match_trovato = True
                    if not match_trovato:
                        pat_no_um = r"^(.*?) ([\d\.,<>]+) (\[.*)$"
                        match = re.search(pat_no_um, line_clean)
                        if match:
                            esame, risultato, um, rif = match.group(1).strip(), match.group(2).strip(), "", match.group(3).strip()
                            match_trovato = True
                    if not match_trovato:
                        pat_ele = r"^(.*?)\s+([\d\.,]+)\s+(\[.*?\])\s+([\d\.,]+)\s+(\[.*?\])$"
                        match = re.search(pat_ele, line_clean)
                        if match:
                            esame, risultato, um, rif = match.group(1).strip(), match.group(2).strip(), "%", match.group(3).strip()
                            match_trovato = True
                    if match_trovato and esame and risultato:
                        if um in ["1", "l"]: um = "L"
                        # Estrazione range da rif
                        anomalia_calc = anomalia
                        try:
                            if rif and re.match(r"\[.*\]", rif):
                                range_match = re.search(r"\[(\d+[\.,]?\d*)-(\d+[\.,]?\d*)\]", rif)
                                if range_match:
                                    min_val = float(range_match.group(1).replace(',', '.'))
                                    max_val = float(range_match.group(2).replace(',', '.'))
                                    val = float(risultato.replace(',', '.'))
                                    if min_val <= val <= max_val:
                                        anomalia_calc = 0
                                    else:
                                        anomalia_calc = 1
                        except Exception:
                            pass
                        righe_uniche.append({
                            "esame": esame,
                            "risultato": risultato,
                            "um": um,
                            "rif": rif,
                            "anomalia": anomalia_calc,
                            "archiviato": True,
                            "idx": idx,
                            "linea": line_orig
                        })
                    else:
                        # anche le righe scartate vanno in lista, archiviato: false
                        righe_uniche.append({
                            "esame": line_orig,
                            "risultato": "",
                            "um": "",
                            "rif": "",
                            "anomalia": 0,
                            "archiviato": False,
                            "idx": idx,
                            "linea": line_orig
                        })
            # Nessun controllo: il valore verrà assegnato dopo
    except Exception as e_text:
        print(f"ERRORE LETTURA TESTO: {e_text}")
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            text = page.get_text()
            if "ELETTROFORESI" in text and "Capillarys" in text:
                rect = fitz.Rect(0, 150, page.rect.width, page.rect.height / 2 + 100)
                pix = page.get_pixmap(clip=rect, dpi=150)
                img_bytes = pix.tobytes("png")
                break
        doc.close()
    except Exception as e_img:
        print(f"Errore estrazione immagine: {e_img}")
    # Nuova logica: assegna accettazione solo dalla quinta riga della tabella temporanea
    if len(righe_uniche) >= 5 and "esame" in righe_uniche[4]:
        acc_raw = righe_uniche[4]["esame"]
        acc_clean = acc_raw.replace("*", "").strip()
        metadata["accettazione"] = acc_clean
        print(f"Numero accettazione assegnato: {metadata['accettazione']}")
    else:
        metadata["accettazione"] = "SenzaNum"
        print("Numero accettazione non trovato, assegnato 'SenzaNum'")
    print(f"--- FINE PARSING: {len(righe_uniche)} righe totali ---")
    print(f"Referto n. {metadata['accettazione']} acquisito")
    if not metadata["paziente"]: metadata["paziente"] = "Sconosciuto"
    if not metadata["accettazione"]: metadata["accettazione"] = "NO_NUM_" + os.path.basename(pdf_path)
    if not metadata["data"]: metadata["data"] = "00-00-0000"
    # Restituisci tutte le righe per la visualizzazione/anteprima
    return metadata, righe_uniche, img_bytes