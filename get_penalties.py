import argparse
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime, date
from getpass import getpass

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


# ================== HAUPTLOGIK =============================

def main():
    args = parse_args()

    if not args.cookie and not args.user:
        raise SystemExit("Entweder --cookie ODER --user angeben.")

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
        password = getpass("Passwort für player.plus: ")
        session = login_with_credentials(args.user, password)

    alle_eintraege = []
    gesehene_keys = set()

    for page in range(1, args.max_pages + 1):
        url = index_url_template.format(page=page)
        print(f"Seite {page} laden: {url}")

        resp = session.get(url)
        # Wenn die Session abgelaufen ist oder Login nötig ist:
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

            # Spielername
            label_el = item.select_one(".list-label")
            spieler = label_el.get_text(strip=True) if label_el else None

            # Datum + Beschreibung
            sublabel_el = item.select_one(".list-sublabel")
            sublabel_text = sublabel_el.get_text(" ", strip=True) if sublabel_el else ""

            # Datum im <b>...</b> in der list-sublabel
            date_el = sublabel_el.find("b") if sublabel_el else None
            datum_str = date_el.get_text(strip=True) if date_el else None

            # Betrag: zuerst in list-value, falls vorhanden
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

    if df_filtered.empty:
        print("Keine Strafen im angegebenen Zeitraum gefunden.")
        df.to_csv("strafen_alle_eintraege_gesamt.csv", index=False, encoding="utf-8")
        print("Gesamtliste gespeichert als strafen_alle_eintraege_gesamt.csv")
        return

    summen = (
        df_filtered.groupby("Spieler", as_index=False)["Betrag"]
        .sum()
        .rename(columns={"Betrag": "Summe"})
        .sort_values("Summe", ascending=False)
    )

    print("\nStrafensumme pro Spieler (gefiltert):")
    print(summen)

    df_filtered.to_csv("strafen_alle_eintraege_gefiltert.csv", index=False, encoding="utf-8")
    summen.to_csv("strafen_pro_spieler_gefiltert.csv", index=False, encoding="utf-8")

    print("\nDateien erstellt (gefiltert nach Zeitraum):")
    print("  - strafen_alle_eintraege_gefiltert.csv")
    print("  - strafen_pro_spieler_gefiltert.csv")


if __name__ == "__main__":
    main()
