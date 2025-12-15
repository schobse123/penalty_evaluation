# 💸 Player+ Strafenauswertung – Einfache Anleitung

Dieses Tool liest die Strafen von Player+ aus, filtert sie nach einem bestimmten Datum und summiert die Beträge pro Spieler.

**Voraussetzung:** Sie benötigen lediglich die Anwendung **Docker Desktop** auf Ihrem Computer.

## 🚀 1. Einrichtung (Einmalig)

Da wir Docker verwenden, müssen Sie **kein** Python installieren und sich **nicht** um Abhängigkeiten kümmern.

### A. Docker Desktop installieren

1.  Laden Sie **Docker Desktop** für Ihr Betriebssystem (Windows oder macOS) von der offiziellen Docker-Website herunter.
2.  Installieren Sie die Anwendung und starten Sie sie.
3.  Stellen Sie sicher, dass das **Docker-Symbol** (der Wal) in Ihrer Menüleiste (Mac) oder Taskleiste (Windows) anzeigt, dass es **läuft (Running)**, bevor Sie fortfahren.

### B. Das Projekt vorbereiten

1.  Laden Sie das gesamte Projekt-Verzeichnis (den Ordner mit allen Dateien wie `app.py`, `docker-compose.yml` etc.) von der Quelle herunter.
2.  Speichern Sie den Ordner an einem beliebigen Ort auf Ihrem PC (z.B. auf dem Desktop oder unter `Dokumente`).

## 🛠️ 2. Starten der Anwendung

Die Anwendung wird über die Kommandozeile gestartet, ist aber danach über Ihren Webbrowser bedienbar.

1.  **Terminal/Kommandozeile öffnen:**
    * **Windows:** Drücken Sie `Win + R`, geben Sie `cmd` ein und drücken Sie Enter.
    * **Mac:** Öffnen Sie **Terminal** (unter Programme $\rightarrow$ Dienstprogramme).
2.  **In das Projekt-Verzeichnis wechseln:**
    Wechseln Sie in den Ordner, den Sie in Schritt 1.B gespeichert haben. (Ersetzen Sie den Pfad durch Ihren tatsächlichen Pfad):
    ```bash
    cd [PFAD ZUM PROJEKT-ORDNER, z.B. C:\Users\IhrName\Desktop\penalty_evaluation]
    ```
3.  **App starten:**
    Führen Sie diesen einzigen Befehl aus, um die App zu bauen und zu starten:
    ```bash
    docker compose up --build
    ```
    *Beim allerersten Start kann dies einige Minuten dauern, da das System alle Komponenten vorbereiten muss.*

4.  **Web-Interface aufrufen:**
    Sobald Sie im Terminal die Meldung sehen, dass der Flask-Server läuft, öffnen Sie Ihren Browser und navigieren Sie zu:
    ```
    http://localhost:8080
    ```

## 📋 3. Nutzung im Browser

Das Web-Interface führt Sie durch alle notwendigen Eingaben.

1.  **Zugangsdaten eingeben:**
    * Geben Sie **entweder** Ihren Benutzernamen und Ihr Passwort für Player+ ein (empfohlen).
    * **Oder** den gesamten `Cookie`-Header, falls Sie diese Methode bevorzugen.
2.  **Auswertungs-Parameter eingeben:**
    * **Startdatum:** Geben Sie das Datum ein, ab dem die Strafen ausgewertet werden sollen (Format: JJJJ-MM-TT, z.B. 2024-01-01).
    * **Maximale Seitenanzahl:** Lassen Sie den Standardwert (20), es sei denn, Sie haben sehr viele Strafen.
    * **`/de/` URL-Option:** Aktivieren Sie das Kästchen, wenn die URL zu Ihren Strafen `/de/` enthält.
3.  **Starten:**
    Klicken Sie auf den Button **"Daten abrufen und CSV erstellen"**.
4.  **Download:**
    Nach erfolgreicher Ausführung (die Dauer hängt von der Menge der Daten ab) startet Ihr Browser automatisch den Download einer **ZIP-Datei** mit den folgenden Ergebnis-Dateien:
    * `strafen_alle_eintraege_gefiltert.csv`: Die Liste aller im Zeitraum gefundenen Strafen.
    * `strafen_pro_spieler_gefiltert.csv`: Die finale Tabelle mit der Summe pro Spieler.

## 🛑 4. Beenden der Anwendung

Wenn Sie die Auswertung abgeschlossen haben, stoppen Sie die Anwendung bitte, um Ressourcen freizugeben:

1.  **Gehen Sie zurück** zu Ihrem Terminal-Fenster, in dem die App läuft.
2.  Drücken Sie die Tastenkombination **`Strg + C`** (`Control + C`), um den Prozess zu beenden.
3.  Führen Sie den folgenden Befehl aus, um den Docker-Container zu entfernen und aufzuräumen:
    ```bash
    docker compose down
    ```

Fertig! Sie können nun die erzeugten CSV-Dateien öffnen und analysieren.
