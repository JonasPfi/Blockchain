
# Blockchain mit Proof-of-Authority (PoA) und Konsensmechanismus

Dieses Projekt implementiert eine einfache Blockchain mit einem Proof-of-Authority (PoA)-Konsensmechanismus. Es nutzt Flask als API und Docker zur Bereitstellung mehrerer Knoten in einer verteilten Umgebung. 

## Inhaltsverzeichnis
- [Projektübersicht](#projektübersicht)
- [Voraussetzungen](#voraussetzungen)
- [Installation und Setup](#installation-und-setup)
  - [Schritt 1: Klonen des Repositories](#schritt-1-klonen-des-repositories)
  - [Schritt 2: Installieren der Abhängigkeiten](#schritt-2-installieren-der-abhängigkeiten)
  - [Schritt 3: Docker-Container starten](#schritt-3-docker-container-starten)
  - [Schritt 4: Knoten registrieren](#schritt-4-knoten-registrieren)
  - [Schritt 5: Validatoren registrieren](#schritt-5-validatoren-registrieren)
- [API-Endpunkte](#api-endpunkte)
- [Problemlösung](#problemlösung)
- [Lizenz](#lizenz)

## Projektübersicht

Dieses Projekt bietet:
- Eine einfache Blockchain mit einem Proof-of-Authority (PoA)-Mechanismus.
- Mehrere Knoten, die in einer Docker-Umgebung ausgeführt werden.
- Konsens-Mechanismus, um sicherzustellen, dass alle Knoten die längste, gültige Kette akzeptieren.

## Voraussetzungen

- **Docker**: Stelle sicher, dass Docker und Docker Compose auf deinem System installiert sind.
- **Python 3.8+**: Falls du das Projekt ohne Docker betreiben möchtest.
- **curl oder Postman**: Um die API-Endpunkte zu testen.

## Installation und Setup

### Schritt 1: Klonen des Repositories

Klonen des Projekts auf dein lokales System:

```bash
git clone https://github.com/dein-repo/blockchain-poa.git
cd blockchain-poa
```

### Schritt 2: Installieren der Abhängigkeiten

Falls du das Projekt ohne Docker laufen lassen möchtest, installiere die Abhängigkeiten:

```bash
pip install -r requirements.txt
```

### Schritt 3: Docker-Container starten

Um die Knoten mit Docker Compose zu starten, führe den folgenden Befehl aus:

```bash
docker-compose up --build
```

Dieser Befehl erstellt und startet die vier Knoten, die im Netzwerk miteinander kommunizieren können.

### Schritt 4: Knoten registrieren

Nach dem Start der Knoten müssen diese untereinander registriert werden. Nutze dafür den folgenden `curl`-Befehl, um Node 2, Node 3 und Node 4 bei Node 1 zu registrieren:

```bash
Invoke-WebRequest -Uri http://localhost:5001/nodes/register `
    -Method POST `
    -ContentType "application/json" `
    -Body '{"nodes": ["http://node2:5000", "http://node3:5000", "http://node4:5000"]}'
```

### Schritt 5: Validatoren registrieren

Registriere alle vier Knoten als Validatoren, sodass sie Blöcke minen dürfen. Beispiel für Node 1:

```bash
Invoke-WebRequest -Uri http://localhost:5001/validators/register `
    -Method POST `
    -ContentType "application/json" `
    -Body '{"validator": "node1"}'
```

Wiederhole dies für die anderen Knoten (`node2`, `node3`, `node4`).

## API-Endpunkte

Hier sind die verfügbaren Endpunkte der Blockchain:

- **`/mine`** (POST): Ermöglicht das Mining eines neuen Blocks durch einen Validator.
  ```bash
  curl -X POST -H "Content-Type: application/json" -d '{"validator": "node1"}' http://localhost:5001/mine
  ```

- **`/transactions/new`** (POST): Fügt eine neue Transaktion zur Blockchain hinzu.
  ```bash
  curl -X POST -H "Content-Type: application/json" -d '{"sender": "address1", "recipient": "address2", "amount": 100}' http://localhost:5001/transactions/new
  ```

- **`/chain`** (GET): Zeigt die gesamte Blockchain an.
  ```bash
  curl http://localhost:5001/chain
  ```

- **`/nodes/register`** (POST): Registriert neue Knoten im Netzwerk.
  ```bash
  curl -X POST -H "Content-Type: application/json" -d '{"nodes": ["http://node2:5000", "http://node3:5000"]}' http://localhost:5001/nodes/register
  ```

- **`/validators/register`** (POST): Registriert einen Validator.
  ```bash
  curl -X POST -H "Content-Type: application/json" -d '{"validator": "node1"}' http://localhost:5001/validators/register
  ```

- **`/nodes/resolve`** (GET): Führt den Konsensmechanismus aus, um die längste gültige Kette im Netzwerk zu übernehmen.
  ```bash
  curl http://localhost:5001/nodes/resolve
  ```

## Problemlösung

- **ImportError: cannot import name 'url_quote'**:
  Falls dieser Fehler auftritt, liegt es an einer inkompatiblen Version von Werkzeug. Stelle sicher, dass du die richtige Version von Werkzeug in deiner `requirements.txt` Datei hast:
  ```txt
  Werkzeug==2.0.3
  ```

- **Fehler bei der Registrierung von Knoten in PowerShell**:
  Stelle sicher, dass du den richtigen `Invoke-WebRequest` Befehl in PowerShell verwendest und die richtigen Header übergibst.

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert.
