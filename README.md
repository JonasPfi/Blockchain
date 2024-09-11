
# Blockchain API mit curl oder Postman testen 

Dieses Dokument beschreibt, wie du die API-Endpunkte deiner Blockchain mithilfe von `curl` oder Postman testen kannst. Du kannst mit `curl` Transaktionen hinzufügen, Blöcke minen und die Blockchain anzeigen lassen.

## Voraussetzungen

- **curl** muss auf deinem System installiert sein.
  - **Linux/macOS**: Normalerweise vorinstalliert.
  - **Windows**: Wenn `curl` nicht vorinstalliert ist, kannst du es [hier herunterladen](https://curl.se/windows/).
  
- **Postman** kann ebenfalls als API-Testtool verwendet werden.
  - [Postman herunterladen](https://www.postman.com/downloads/)

## API-Endpunkte

### 1. **Transaktion hinzufügen**

Verwende den `/transactions/new`-Endpunkt, um eine neue Transaktion zur Blockchain hinzuzufügen.

#### Beispiel:

```bash
curl -X POST -H "Content-Type: application/json" \
    -d '{"sender": "address1", "recipient": "address2", "amount": 100}' \
    http://localhost:5004/transactions/new
```

- **Methode**: `POST`
- **URL**: `http://localhost:5004/transactions/new`
- **Daten**: JSON-Format
  ```json
  {
    "sender": "address1",
    "recipient": "address2",
    "amount": 100
  }
  ```
- **Erwartete Antwort**: Eine Bestätigung, dass die Transaktion zum Block hinzugefügt wurde.

---

### 2. **Mining eines neuen Blocks**

Verwende den `/mine`-Endpunkt, um einen neuen Block zu minen. Hierbei muss der Validator angegeben werden, der den Block mined.

#### Beispiel:

```bash
curl -X POST -H "Content-Type: application/json" \
    -d '{"validator": "node1"}' \
    http://localhost:5004/mine
```

- **Methode**: `POST`
- **URL**: `http://localhost:5004/mine`
- **Daten**: JSON-Format
  ```json
  {
    "validator": "node1"
  }
  ```
- **Erwartete Antwort**: Details zum neuen Block.

---

### 3. **Die gesamte Blockchain anzeigen**

Verwende den `/chain`-Endpunkt, um die gesamte Blockchain anzeigen zu lassen.

#### Beispiel:

```bash
curl -X GET http://localhost:5004/chain
```

- **Methode**: `GET`
- **URL**: `http://localhost:5004/chain`
- **Erwartete Antwort**: Die vollständige Blockchain als JSON-Objekt.

---

### 4. **Neue Knoten registrieren**

Verwende den `/nodes/register`-Endpunkt, um neue Knoten zum Blockchain-Netzwerk hinzuzufügen.

#### Beispiel:

```bash
curl -X POST -H "Content-Type: application/json" \
    -d '{"nodes": ["http://node2:5000", "http://node3:5000"]}' \
    http://localhost:5004/nodes/register
```

- **Methode**: `POST`
- **URL**: `http://localhost:5004/nodes/register`
- **Daten**: JSON-Format
  ```json
  {
    "nodes": ["http://node2:5000", "http://node3:5000"]
  }
  ```
- **Erwartete Antwort**: Eine Bestätigung, dass die Knoten zum Netzwerk hinzugefügt wurden.

---

### 5. **Konsens erreichen**

Verwende den `/nodes/resolve`-Endpunkt, um den Konsensmechanismus auszuführen und sicherzustellen, dass die Blockchain auf allen Knoten konsistent ist.

#### Beispiel:

```bash
curl -X GET http://localhost:5004/nodes/resolve
```

- **Methode**: `GET`
- **URL**: `http://localhost:5004/nodes/resolve`
- **Erwartete Antwort**: Gibt an, ob die Kette ersetzt wurde und zeigt die endgültige, autoritative Blockchain.

---

## Zusätzliche Anweisungen zur manuellen Registrierung von Knoten und Validatoren:

### 1. **Manuelle Registrierung der Knoten**

Verwende den `/nodes/register`-Endpunkt, um neue Knoten zum Blockchain-Netzwerk hinzuzufügen.

#### Beispiel:

```bash
curl -X POST -H "Content-Type: application/json" -d '{"nodes": ["http://node2:5000", "http://node3:5000"]}' http://localhost:5001/nodes/register
```

---

### 2. **Manuelle Registrierung von Validatoren**

Verwende den `/validators/register`-Endpunkt, um einen Validator zu registrieren.

#### Beispiel:

```bash
curl -X POST -H "Content-Type: application/json" -d '{"validator": "node1"}' http://localhost:5001/validators/register
```

---

### 3. **Konsens ausführen**

Um den Konsens zwischen den Knoten herzustellen, kannst du den `/nodes/resolve`-Endpunkt manuell aufrufen.

#### Beispiel:

```bash
curl -X GET http://localhost:5001/nodes/resolve
```

Dieser Befehl führt den Konsensmechanismus aus und vergleicht die Kette von `node1` mit den anderen Knoten im Netzwerk.

---

## Zusammenfassung:

- **Knoten registrieren**: `/nodes/register`
- **Validatoren registrieren**: `/validators/register`
- **Konsens herstellen**: `/nodes/resolve`

Verwende diese Endpunkte, um die Knoten im Netzwerk manuell zu synchronisieren und sicherzustellen, dass die Blockchain auf allen Knoten einheitlich ist.
