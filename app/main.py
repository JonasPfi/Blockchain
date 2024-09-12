from fastapi import FastAPI
from pydantic import BaseModel
import hashlib
import json
from datetime import datetime
import requests
from typing import List
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.exceptions import InvalidSignature
import time
import os
from datetime import datetime, timedelta
app = FastAPI()

container_name = os.getenv("CONTAINERNAME")

AUTHORITY_NODES = ["http://fastapi_app_2:8000/"]
AUTHORITY_PUBLIC_KEYS = []  # Public keys fetched from authority nodes

transaction_requests = []
PRIVATE_KEY_FILE = "private_key.pem"
PUBLIC_KEY_FILE = "public_key.pem"

def generate_rsa_keys():
    """
    Generate RSA keypairs
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()
    
    with open(PRIVATE_KEY_FILE, "wb") as private_key_file:
        private_key_file.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
        )

    with open(PUBLIC_KEY_FILE, "wb") as public_key_file:
        public_key_file.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        )

generate_rsa_keys()

def load_public_key():
    """
    Load the public key from the file.
    """
    with open(PUBLIC_KEY_FILE, "rb") as public_key_file:
        return public_key_file.read().decode()

class SendTransactionRequest(BaseModel):
    container: str
    amount: float

class AcceptTransactionRequest(BaseModel):
    number: int

class Transaction(BaseModel):
    index: int
    sender: str
    recipient: str
    amount: float
    expiration: str
    previous_hash: str = None
    current_hash: str = None
    sender_signature: str = None
    recipient_signature: str = None
    timestamp: str
    authority_signature: str
    


class Transchain:
    def __init__(self):
        self.transactions = [self.create_genesis_transaction()]
        self.authority_public_keys = []
    def create_genesis_transaction(self) -> dict:
        # Define transaction components
        index = 0
        sender = 'Genesis'
        recipient = 'Genesis'
        amount = 0.0
        expiration = None
        previous_hash = None
        sender_signature = None
        recipient_signature = None
        timestamp = str(datetime.utcnow())
        authority_signature = None

        # Create a string representation of the transaction data
        transaction_string = f"{index}{sender}{recipient}{amount}{expiration}{previous_hash}"
        
        # Calculate the hash
        current_hash = hashlib.sha256(transaction_string.encode()).hexdigest()

        return {
            'index': index,
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'expiration': expiration,
            'previous_hash': previous_hash,
            'current_hash': current_hash,
            'sender_signature': sender_signature,
            'recipient_signature': recipient_signature,
            'timestamp': timestamp,
            'authority_signature': authority_signature
        }

    def fetch_authority_public_keys(self):
        """
        Fetches public keys from all authority nodes and stores them.
        """
        for node_url in AUTHORITY_NODES:
            try:
                print(f"Fetching public key from {node_url}")
                response = requests.get(f"{node_url}public_key")
                if response.status_code == 200:
                    public_key = response.json().get("public_key")
                    self.authority_public_key.append(public_key)
            except Exception as e:
                print(f"Error fetching public key from {node_url}: {e}")


    def calculate_hash(self, data: dict) -> str:
        """
        Calculates the hash of a given block/transaction data
        """
        keywords = ["index", "sender", "recipient", "amount", "previous_hash", "expiration",]
        string_to_hash = ""
        for keyword in keywords:
           string_to_hash += str(data[keyword]) 

        return hashlib.sha256(string_to_hash.encode('utf-8')).hexdigest()


    def verify_transchain(self) -> bool:
        """
        Verifies the entire chain by checking:
        1. Each transaction's hash matches its calculated hash.
        2. The previous_hash of each transaction matches the hash of the previous transaction.
        3. Each transaction's authority_signature is valid using the public keys.
        """
        self.fetch_authority_public_keys()
        for i in range(1, len(self.transactions)):  # Start from 1 since genesis doesn't have a previous_hash
            current_transaction = self.transactions[i]
            previous_transaction = self.transactions[i - 1]

            transaction_data = {
                'sender': current_transaction['sender'],
                'recipient': current_transaction['recipient'],
                'amount': current_transaction['amount'],
                'previous_hash': current_transaction['previous_hash']
            }
            calculated_hash = self.calculate_hash(transaction_data)
            if calculated_hash != current_transaction['hash']:
                return False  

            # Verify the previous_hash points to the previous transaction
            if current_transaction['previous_hash'] != previous_transaction['hash']:
                return False  

            # Verify authority_signature
            authority_signature_bytes = bytes.fromhex(current_transaction['authority_signature'])
            for pub_key_pem in AUTHORITY_PUBLIC_KEYS:
                try:
                    # Load the public key from PEM format
                    public_key = load_pem_public_key(pub_key_pem.encode("utf-8"))

                    # Verify the authority signature
                    public_key.verify(
                        authority_signature_bytes,
                        calculated_hash.encode(), 
                        padding.PKCS1v15(),
                        hashes.SHA256()
                    )
                    break  # Signature verified, no need to check further public keys
                except InvalidSignature:
                    continue  # Try the next public key

            else:
                return False  # Authority signature verification failed

        return True  # If all checks pass

    def get_transactions(self):
        return self.transactions


# Create a Transchain instance
transchain = Transchain()


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}


@app.get("/transactions")
def get_transactions():
    return {"transactions": transchain.get_transactions()}


@app.post("/add_transaction/")
def add_transaction(transaction: Transaction):
    transchain.transactions.append(transaction.dict())
    return {"message": "Transaction added", "transactions": transchain.get_transactions()}


@app.get("/verify_chain")
def verify_chain():
    if transchain.verify_transchain():
        return {"message": "Chain is valid"}
    else:
        return {"error": "Chain verification failed"}

@app.get("/public_key")
def get_public_key():
    """
    Endpoint to get the public key of this FastAPI application.
    """
    public_key = load_public_key()
    return {"public_key": public_key}



@app.post("/send_transaction/")
def send_transaction(request: SendTransactionRequest):
    # Extract the port and amount from the request body
    recipient_container = request.container
    amount = request.amount

    # Load sender's private key
    with open(PRIVATE_KEY_FILE, "rb") as private_key_file:
        private_key = serialization.load_pem_private_key(
            private_key_file.read(),
            password=None
        )

    # Define the current time and expiration time
    current_time = str(datetime.utcnow())
    expiration_time = str(datetime.utcnow() + timedelta(minutes=10))  

    # Create the transaction data (excluding the signature fields)
    transaction_data = {
        "index": transchain.transactions[-1]["index"] + 1,
        "sender": container_name,  
        "recipient": f"{recipient_container}",  
        "amount": amount,
        "previous_hash": transchain.transactions[-1]["current_hash"],  
        "expiration": expiration_time
    }

    # Convert transaction data to a string representation

    transaction_hash = transchain.calculate_hash(transaction_data)

    # Sign the previous hash
    signature = private_key.sign(
        transaction_hash.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    # Update the transaction with the signature
    transaction = {
        **transaction_data,
        "current_hash": transaction_hash,
        "sender_signature": signature.hex(),
        "recipient_signature": "",  # To be filled later by the recipient
        "timestamp": "",
        "authority_signature": "",
    }
    print(transaction)
    # Send the transaction to the recipient
    response = requests.post(f"http://{recipient_container}:8000/receive_transaction/", json=transaction)
    return {"message": "Transaction sent", "response": response.json()}


@app.post("/receive_transaction/")
def receive_transaction(transaction: Transaction):
    global transaction_requests
    transaction_requests.append(transaction)
    print('neee')
    return {"message": transaction_requests }

@app.get("/show_transactions")
def show_transaction():
    return {"transactions": transaction_requests}

@app.post("/accept_transaction/")
def accept_transaction(request: AcceptTransactionRequest):
    index_of_request = request.number

    # Validate the index of the transaction request
    if index_of_request < 0 or index_of_request >= len(transaction_requests):
        raise HTTPException(status_code=400, detail="Invalid transaction index")

    transaction_request = transaction_requests[index_of_request].dict()

    # Load recipient's private key
    with open(PRIVATE_KEY_FILE, "rb") as private_key_file:
        private_key = serialization.load_pem_private_key(
            private_key_file.read(),
            password=None
        )

    # Define the current time
    current_time = datetime.utcnow().isoformat()

    # Calculate the transaction hash
    transaction_hash = transchain.calculate_hash(transaction_request)

    if transaction_hash != transaction_request["current_hash"]:
        print( "wrong")
    print("true")

    # Sign the transaction hash
    signature = private_key.sign(
        transaction_hash.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    # Update the transaction with the recipient's signature
    transaction_request['recipient_signature'] = signature.hex()

    # Send the signed transaction to the authority node
    authority_url = f"{AUTHORITY_NODES[0]}verify_transaction/"
    print(authority_url)
    response = requests.post(authority_url, json=transaction_request)
    print("OOKKKK")
    return {"message": response.json()}

@app.post("/verify_transaction/")
def verify_transaction(transaction: Transaction):
    # Bereite die Transaktionsdaten vor
    transaction_data = transaction.dict()

    # Berechne den Hash der Transaktion
    transaction_hash = transchain.calculate_hash(transaction_data)
    
    # Überprüfe, ob der Hash mit dem aktuellen Hash der Transaktion übereinstimmt
    if transaction_hash != transaction.current_hash:
        return {"error": "manipulated transaction"}
    
    print("Hash verified")
    
    # Abrufen der öffentlichen Schlüssel des Senders und Empfängers
    try:
        sender_response = requests.get(f"http://{transaction.sender}:8000/public_key")
        sender_response.raise_for_status()
        sender_public_key_pem = sender_response.json()['public_key']
        
        recipient_response = requests.get(f"http://{transaction.recipient}:8000/public_key")
        recipient_response.raise_for_status()
        recipient_public_key_pem = recipient_response.json()['public_key']
    
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail="Error fetching public keys")
    
    # Verifizieren der Sender-Signatur
    try:
        sender_public_key = load_pem_public_key(sender_public_key_pem.encode("utf-8"))
        sender_signature = bytes.fromhex(transaction.sender_signature)
        sender_public_key.verify(
            sender_signature,
            transaction_hash.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
    except InvalidSignature:
        raise HTTPException(status_code=400, detail="Invalid sender signature")
    
    print("Sender signature verified")
    
    # Verifizieren der Empfänger-Signatur
    try:
        recipient_public_key = load_pem_public_key(recipient_public_key_pem.encode("utf-8"))
        recipient_signature = bytes.fromhex(transaction.recipient_signature)
        recipient_public_key.verify(
            recipient_signature,
            transaction_hash.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
    except InvalidSignature:
        raise HTTPException(status_code=400, detail="Invalid recipient signature")
    
    print("Recipient signature verified")
    print("Hallo") 
    # Signieren der Transaktion durch den Authority-Knoten
    try:
        with open("private_key.pem", "rb") as key_file:
            private_key = load_pem_private_key(key_file.read(), password=None)
        
        signature = private_key.sign(
            transaction_hash.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        print("Hallo2")
        transaction_data["authority_signature"] = signature.hex()
        print(transaction_data)
        print("Hallo3")
        transchain.transactions.append(transaction_data)
        print("Hallo4")
        print("Transaction added to the chain")
        return {"message": "Transaction verified and added to the chain"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error signing transaction: {e}")