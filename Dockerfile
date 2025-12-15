# Start von einem offiziellen Python-Image
FROM python:3.10-slim

# Setze Umgebungsvariable, um Ausgaben direkt in das Terminal zu leiten
ENV PYTHONUNBUFFERED 1

# Setze das Arbeitsverzeichnis
WORKDIR /app

# Kopiere die Anforderungen und installiere sie (Caching-Vorteil)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den Rest deiner Anwendung (inkl. app.py, get_penalties.py und templates/)
COPY . .

# Der Container macht Port 5000 für Flask verfügbar
EXPOSE 5000

# Starte die Flask-Anwendung
# Nutze gunicorn oder Waitress für Produktion, hier einfacher Start mit Flask
CMD ["flask", "run", "--host=0.0.0.0"]