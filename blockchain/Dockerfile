# Wählen Sie das Basis-Image
FROM python:3.8-slim

# Arbeitsverzeichnis festlegen
WORKDIR /app

# Abhängigkeiten kopieren
COPY requirements.txt requirements.txt

# Abhängigkeiten installieren
RUN pip install -r requirements.txt

# App-Dateien kopieren
COPY . .

# Flask App starten
CMD ["python", "app.py"]
