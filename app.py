# app.py

from flask import Flask, render_template, request, send_file
import os
import io
import shutil

# Importiere die Logik aus deinem Skript. 
# WICHTIG: Die main-Funktion muss so angepasst werden, dass sie die Argumente direkt als dictionary/objekt annimmt!
# Wir simulieren hier die Übergabe der Argumente.
from get_penalties import process_penalties, LOGIN_URL 

app = Flask(__name__)
# Ordner für temporäre Dateien
UPLOAD_FOLDER = 'temp_results'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Flask braucht ein Objekt, das die Argumente des Benutzers simuliert
class UserArgs:
    def __init__(self, data):
        self.cookie = data.get('cookie') or None
        self.user = data.get('user') or None
        self.password = data.get('password') # Wird in der Logik mit getpass/direkt genutzt
        self.startdatum = data.get('startdatum')
        self.max_pages = int(data.get('max_pages', 20))
        self.with_de = data.get('with_de') == 'on'

# ================== ROUTEN ==========================

@app.route("/", methods=["GET"])
def index():
    """Zeigt das Eingabeformular an."""
    return render_template("index.html", login_url=LOGIN_URL)

@app.route("/", methods=["POST"])
def run_script():
    """Verarbeitet das Formular und führt die Hauptlogik aus."""
    data = request.form
    
    # 1. Argumente zusammenstellen
    args = UserArgs(data)
    
    # 2. Passwort separat behandeln
    password = data.get('password')

    try:
        # 3. Hauptlogik ausführen
        # Die Funktion gibt jetzt den Dateipfad des erstellten ZIP-Archivs zurück (s. u.)
        zip_filepath, log_output = process_penalties(args, password)
        
        # 4. ZIP-Datei an den Benutzer senden
        return send_file(
            zip_filepath,
            mimetype='application/zip',
            as_attachment=True,
            download_name='playerplus_strafen_ergebnis.zip'
        )
    
    except SystemExit as e:
        # Fehler der Hauptlogik abfangen
        error_message = f"Fehler bei der Verarbeitung: {str(e)}"
        if log_output:
            error_message += f"\n\nDetails:\n{log_output}"
        
        return render_template("index.html", error=error_message, login_url=LOGIN_URL), 400
    
    except Exception as e:
        return render_template("index.html", error=f"Ein unerwarteter Fehler ist aufgetreten: {e}", login_url=LOGIN_URL), 500

# ================== START ==========================

if __name__ == "__main__":
    app.run(debug=True)