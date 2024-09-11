
# Blockchain API mit curl testen

Dieses Dokument beschreibt, wie du die API-Endpunkte deiner Blockchain mithilfe von `curl` testen kannst. Du kannst mit `curl` Transaktionen hinzufügen, Blöcke minen und die Blockchain anzeigen lassen.

## Voraussetzungen

- **curl** muss auf deinem System installiert sein.
  - **Linux/macOS**: Normalerweise vorinstalliert.
  - **Windows**: Wenn `curl` nicht vorinstalliert ist, kannst du es [hier herunterladen](https://curl.se/windows/).

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

### 3. **Die gesamte Blockchain anzeigen**

Verwende den `/chain`-Endpunkt, um die gesamte Blockchain anzeigen zu lassen.

#### Beispiel:

```bash
curl -X GET http://localhost:5004/chain
```

- **Methode**: `GET`
- **URL**: `http://localhost:5004/chain`
- **Erwartete Antwort**: Die vollständige Blockchain als JSON-Objekt.

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

### 5. **Konsens erreichen**

Verwende den `/nodes/resolve`-Endpunkt, um den Konsensmechanismus auszuführen und sicherzustellen, dass die Blockchain auf allen Knoten konsistent ist.

#### Beispiel:

```bash
curl -X GET http://localhost:5004/nodes/resolve
```

- **Methode**: `GET`
- **URL**: `http://localhost:5004/nodes/resolve`
- **Erwartete Antwort**: Gibt an, ob die Kette ersetzt wurde und zeigt die endgültige, autoritative Blockchain.

## Häufige Probleme

1. **Method Not Allowed (405)**: Dies tritt auf, wenn du die falsche HTTP-Methode (z.B. `GET` statt `POST`) verwendest. Überprüfe, ob du die richtige Methode für den jeweiligen Endpunkt nutzt.

2. **Connection Refused**: Stelle sicher, dass der Server läuft und du die richtige URL (einschließlich des Ports) verwendest.

## Weitere Informationen

Weitere Details zur Funktionsweise der Blockchain und zu den Endpunkten findest du in der Projektdokumentation.
