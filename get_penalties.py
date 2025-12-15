import argparse
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime, date
from getpass import getpass
import os
import zipfile
from io import StringIO
import sys

# ================== CLI-ARGUMENTE ==========================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Strafen von player.plus auslesen und pro Spieler summieren."
    )

    # Variante 1: Man gibt direkt den Cookie-Header an
    parser.add_argument(
        "--cookie",
        help="Kompletter Cookie-Header aus dem Browser (Alternative zu --user/--password).",
    )

    # Variante 2: Login mit Benutzername + Passwort
    parser.add_argument(
        "--user",
        help="Login-Benutzername/E-Mail für player.plus (Passwort wird sicher abgefragt).",
    )

    parser.add_argument(
        "--startdatum",
        required=True,
        help="Startdatum im Format TT.MM.JJJJ oder YYYY-MM-DD (bis heute wird ausgewertet).",
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=20,
        help="Maximale Anzahl an Seiten, die geladen werden (Standard: 20).",
    )

    parser.add_argument(
        "--with-de",
        action="store_true",
        help="Wenn deine URL /de/ enthält (z.B. /de/punishments/index).",
    )

    return parser.parse_args()


def parse_date_string(s: str) -> date:
    s = s.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError("Ungültiges Datumsformat. Bitte TT.MM.JJJJ oder YYYY-MM-DD verwenden.")


# ================== LOGIN-FUNKTION ==========================

BASE_URL = "https://player.plus"

# Login-URL aus dem Network-Tab übernehmen:
LOGIN_URL = BASE_URL + "/de/site/login"   # <- ggf. anpassen!


def login_with_credentials(username: str, password: str) -> requests.Session:
    """
    Loggt sich bei player.plus ein und gibt eine Session mit gültigen Cookies zurück.
    Nutzt die echten Feldnamen aus deinem HTML.
    """

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X)",
    })

    # 1) Login-Seite laden, um CSRF-Token zu holen
    resp = session.get(LOGIN_URL)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    csrf_input = soup.find("input", {"name": "_csrf"})
    csrf_token = csrf_input["value"] if csrf_input else None

    if not csrf_token:
        raise SystemExit("CSRF-Token nicht gefunden – Login-Seite falsch oder HTML verändert?")

    # 2) POST-Login-Daten
    data = {
        "LoginForm[email]": username,
        "LoginForm[password]": password,
        "_csrf": csrf_token,
        # optional – kannst du setzen, wenn du willst
        "LoginForm[rememberMe]": "1",
    }

    # 3) POST Request absenden
    login_resp = session.post(LOGIN_URL, data=data)
    login_resp.raise_for_status()

    # einfache Login-Prüfung: danach sollte irgendwo "Logout" stehen
   # if "Logout" not in login_resp.text and "Abmelden" not in login_resp.text:
    #    raise SystemExit("Login fehlgeschlagen – Benutzerdaten prüfen.")

    print("Login erfolgreich – Session-Cookies gesetzt.")
    return session


# ================== HILFSFUNKTIONEN ==========================

betrag_regex = re.compile(r"(\d+[.,]?\d*)\s*€")

def extract_amount(*texts):
    """Versucht, die erste 'Zahl + €' aus den gegebenen Texten zu extrahieren."""
    for text in texts:
        if not text:
            continue
        match = betrag_regex.search(text)
        if match:
            return match.group(1)
    return None


def normalize_euro(amount_str):
    """Wandelt '3', '3€', '3,00', '15,00', '0,50' usw. in float um."""
    if amount_str is None:
        return 0.0
    s = str(amount_str)
    s = s.replace("€", "").replace("\xa0", "").strip()
    # Tausenderpunkte entfernen, Komma als Dezimaltrenner in Punkt
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0

# ================== HILFSFUNKTIONEN FÜR FLASK ==========================

def create_zip_archive(files_to_zip: list, zip_filename: str):
    """Erstellt ein ZIP-Archiv aus einer Liste von (Dateiname, Inhalt) Paaren."""
    zip_path = os.path.join("temp_results", zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files_to_zip:
            # Speichert den Inhalt in einem io.BytesIO Puffer, um ihn in das ZIP zu schreiben
            # ohne eine temporäre Datei auf der Festplatte zu erstellen
            zf.writestr(filename, content)
            
    return zip_path


# ================== HAUPTLOGIK FÜR FLASK =============================

# Ersetzt die alte main()-Funktion
def process_penalties(args, password_input):
    
    # -----------------------------------------------------------------
    # Um die Konsolenausgaben (Prints) abzufangen, leiten wir stdout um
    # Dies ist hilfreich, um Logs im Flask-Frontend anzuzeigen
    old_stdout = sys.stdout
    sys.stdout = output_capture = StringIO()
    
    # Pfad für das finale ZIP-Archiv
    zip_filename = f"strafen_auswertung_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    try:
        # ------------------ START DER URSPRÜNGLICHEN LOGIK ------------------
        
        if not args.cookie and not args.user:
            raise SystemExit("Entweder --cookie ODER --user angeben.")

        # Datum parsen und ausgeben
        start_date = parse_date_string(args.startdatum)
        today = date.today()
        print(f"Auswertung von {start_date.strftime('%d.%m.%Y')} bis {today.strftime('%d.%m.%Y')}")

        # URL-Template je nach /de/-Variante
        if args.with_de:
            index_url_template = "https://player.plus/de/punishments/index?page={page}&per-page=25"
        else:
            index_url_template = "https://player.plus/punishments/index?page={page}&per-page=25"

        # 1) Session vorbereiten
        if args.cookie:
            # Variante: Cookie-Header direkt verwenden
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X)",
                "Cookie": args.cookie,
            })
        else:
            # Variante: Login mit Username + Passwort
            # HIER WIRD getpass() DURCH DIE ÜBERGABE VON FLASK ERSETZT!
            password = password_input 
            if not password:
                raise SystemExit("Passwort fehlt für Login-Methode.")
            
            session = login_with_credentials(args.user, password)

        # 2) Daten scrapen
        alle_eintraege = []
        gesehene_keys = set()

        for page in range(1, args.max_pages + 1):
            url = index_url_template.format(page=page)
            print(f"Seite {page} laden: {url}")
            
            # ... (Rest der Scraping-Logik bleibt unverändert) ...
            
            resp = session.get(url)
            if resp.status_code == 403 or "Login" in resp.text[:300]:
                raise SystemExit("Keine Berechtigung / Session abgelaufen – Cookie/Login prüfen.")

            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            items = soup.select("div.list-item[data-key]")
            print(f"  -> {len(items)} Einträge gefunden")

            if not items:
                break

            neue_in_dieser_seite = 0

            for item in items:
                key = item.get("data-key")
                if not key:
                    continue
                if key in gesehene_keys:
                    continue
                gesehene_keys.add(key)
                neue_in_dieser_seite += 1

                label_el = item.select_one(".list-label")
                spieler = label_el.get_text(strip=True) if label_el else None

                sublabel_el = item.select_one(".list-sublabel")
                sublabel_text = sublabel_el.get_text(" ", strip=True) if sublabel_el else ""

                date_el = sublabel_el.find("b") if sublabel_el else None
                datum_str = date_el.get_text(strip=True) if date_el else None

                value_el = item.select_one(".list-value")
                value_text = value_el.get_text(" ", strip=True) if value_el else ""

                betrag_raw = extract_amount(value_text, sublabel_text)
                betrag = normalize_euro(betrag_raw)

                alle_eintraege.append(
                    {
                        "Key": key,
                        "Spieler": spieler,
                        "Datum": datum_str,
                        "Beschreibung": sublabel_text,
                        "Betrag_raw": betrag_raw,
                        "Betrag": betrag,
                    }
                )

            print(f"  -> {neue_in_dieser_seite} neue eindeutige Einträge")

            if neue_in_dieser_seite == 0:
                break

        if not alle_eintraege:
            raise SystemExit("Keine Strafen gefunden. Stimmt die URL, sind Rechte vorhanden, ist Login/Cookie gültig?")

        df = pd.DataFrame(alle_eintraege)

        df["Datum_parsed"] = pd.to_datetime(
            df["Datum"], format="%d.%m.%Y", errors="coerce"
        ).dt.date

        maske = (df["Datum_parsed"] >= start_date) & (df["Datum_parsed"] <= today)
        df_filtered = df[maske].copy()

        print(f"\nAnzahl Strafen im gewählten Zeitraum: {len(df_filtered)}")
        
        # 3) Dateierstellung und Zippen

        files_for_zip = []
        
        # DataFrame 1: Gesamtliste (immer speichern, auch wenn leer)
        csv_buffer_all = StringIO()
        df.to_csv(csv_buffer_all, index=False, encoding="utf-8")
        files_for_zip.append(("strafen_alle_eintraege_gesamt.csv", csv_buffer_all.getvalue()))
        print("Gesamtliste gespeichert als strafen_alle_eintraege_gesamt.csv")
        
        if not df_filtered.empty:
            summen = (
                df_filtered.groupby("Spieler", as_index=False)["Betrag"]
                .sum()
                .rename(columns={"Betrag": "Summe"})
                .sort_values("Summe", ascending=False)
            )

            print("\nStrafensumme pro Spieler (gefiltert):")
            print(summen)

            # DataFrame 2: Gefilterte Liste
            csv_buffer_filtered = StringIO()
            df_filtered.to_csv(csv_buffer_filtered, index=False, encoding="utf-8")
            files_for_zip.append(("strafen_alle_eintraege_gefiltert.csv", csv_buffer_filtered.getvalue()))

            # DataFrame 3: Summen
            csv_buffer_summen = StringIO()
            summen.to_csv(csv_buffer_summen, index=False, encoding="utf-8")
            files_for_zip.append(("strafen_pro_spieler_gefiltert.csv", csv_buffer_summen.getvalue()))

            print("\nDateien erstellt (gefiltert nach Zeitraum):")
            print("  - strafen_alle_eintraege_gefiltert.csv")
            print("  - strafen_pro_spieler_gefiltert.csv")


        # ZIP-Archiv erstellen
        zip_filepath = create_zip_archive(files_for_zip, zip_filename)
        print(f"\nAlle Ergebnisse erfolgreich in ZIP-Datei gespeichert: {zip_filepath}")
        
        # ------------------ ENDE DER LOGIK ------------------
        
        # Log-Output wiederherstellen und zurückgeben
        sys.stdout = old_stdout
        return zip_filepath, output_capture.getvalue()

    except Exception as e:
        # Bei Fehlern Log-Output wiederherstellen
        sys.stdout = old_stdout
        raise SystemExit(str(e)) from e



