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
from cryptography.exceptions import InvalidSignature
import time
import os
from datetime import datetime, timedelta
app = FastAPI()

container_name = os.getenv("CONTAINERNAME")

AUTHORITY_NODES = ["http://fastapi_app_2:8000/", "http://localhost:8002"]
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
        global AUTHORITY_PUBLIC_KEYS
        for node_url in AUTHORITY_NODES:
            try:
                print(f"Fetching public key from {node_url}")
                response = requests.get(f"{node_url}/public_key")
                if response.status_code == 200:
                    public_key = response.json().get("public_key")
                    AUTHORITY_PUBLIC_KEYS.append(public_key)
            except Exception as e:
                print(f"Error fetching public key from {node_url}: {e}")


    def calculate_hash(self, data: dict) -> str:
        """
        Calculates the hash of a given block/transaction data.
        """
        data_string = json.dumps(data, sort_keys=True).encode()
        return hashlib.sha256(data_string).hexdigest()

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
    transaction_string = f"{transaction_data['index']}{transaction_data['sender']}{transaction_data['recipient']}{transaction_data['amount']}{transaction_data['expiration']}{transaction_data['previous_hash']}"

    # Calculate the transaction hash
    transaction_hash = hashlib.sha256(transaction_string.encode()).hexdigest()

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
    print(index_of_request)

    # Validate the index of the transaction request
    if index_of_request < 0 or index_of_request >= len(transaction_requests):
        raise HTTPException(status_code=400, detail="Invalid transaction index")

    # Retrieve the transaction request
    transaction_request = transaction_requests[index_of_request]

    # Load recipient's private key
    with open(PRIVATE_KEY_FILE, "rb") as private_key_file:
        private_key = serialization.load_pem_private_key(
            private_key_file.read(),
            password=None
        )

    # Define the current time
    current_time = datetime.utcnow().isoformat()

    # Convert the transaction request to a dictionary
    transaction_data = transaction_request.dict()

    # Create the transaction string for hashing
    transaction_string = (
        f"{transaction_data['index']}"
        f"{transaction_data['sender']}"
        f"{transaction_data['recipient']}"
        f"{transaction_data['amount']}"
        f"{transaction_data['expiration']}"
        f"{transaction_data['previous_hash']}"
    )

    # Calculate the transaction hash
    transaction_hash = hashlib.sha256(transaction_string.encode()).hexdigest()

    # Sign the transaction hash
    signature = private_key.sign(
        transaction_hash.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    # Update the transaction with the recipient's signature
    transaction_data['recipient_signature'] = signature.hex()

    # Send the signed transaction to the authority node
    authority_url = "http://localhost:8000/verify_transaction/"
    response = requests.post(authority_url, json=transaction_data)

    if response.status_code == 200:
        return {"message": transaction_data}
    else:
        return {"error": "Failed to send transaction to authority"}

@app.post("/verify_transaction/")
def verify_transaction(transaction: Transaction):
    # Verify the transaction here
    transaction_data = {
        'sender': transaction.sender,
        'recipient': transaction.recipient,
        'amount': transaction.amount,
        'previous_hash': transaction.previous_hash
    }
    transaction_hash = transchain.calculate_hash(transaction_data)

    # Load the public keys and verify the signature
    for pub_key_pem in AUTHORITY_PUBLIC_KEYS:
        try:
            public_key = load_pem_public_key(pub_key_pem.encode("utf-8"))
            signature = bytes.fromhex(transaction.authority_signature)
            public_key.verify(
                signature,
                transaction_hash.encode(),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            # If verification succeeds, add the transaction to the chain
            transchain.transactions.append(transaction.dict())
            return {"message": "Transaction verified and added to the chain"}
        except InvalidSignature:
            continue
    
    return {"error": "Invalid transaction signature"}