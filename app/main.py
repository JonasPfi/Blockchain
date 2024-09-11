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

app = FastAPI()

AUTHORITY_NODES = ["http://localhost:8001", "http://localhost:8002"]
AUTHORITY_PUBLIC_KEYS = []  # Public keys fetched from authority nodes

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
        
class Transaction(BaseModel):
    sender: str
    sender_signature: str
    recipient: str
    recipient_signature: str
    amount: float
    previous_hash: str = None
    authority_signature: str


class Transchain:
    def __init__(self):
        self.transactions = [self.create_genesis_transaction()]
        self.fetch_authority_public_keys()  # Fetch the public keys from authority nodes

    def create_genesis_transaction(self) -> dict:
        # Genesis-Transaktion ist der Startpunkt der Blockchain
        return {
            'index': 0,
            'timestamp': str(datetime.utcnow()),
            'sender': 'Genesis',
            'sender_signature': None,
            'recipient': 'Genesis',
            'recipient_signature': None,
            'amount': 0.0,
            'previous_hash': None,
            'authority_signature': None
        }

    def fetch_authority_public_keys(self):
        """
        Fetches public keys from all authority nodes and stores them.
        """
        global AUTHORITY_PUBLIC_KEYS
        for node_url in AUTHORITY_NODES:
            try:
                response = requests.get(f"{node_url}/getPublicKey")
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
        for i in range(1, len(self.transactions)):  # Start from 1 since genesis doesn't have a previous_hash
            current_transaction = self.transactions[i]
            previous_transaction = self.transactions[i - 1]

            # Verify the hash of the current transaction
            transaction_data = {
                'sender': current_transaction['sender'],
                'recipient': current_transaction['recipient'],
                'amount': current_transaction['amount'],
                'previous_hash': current_transaction['previous_hash']
            }
            calculated_hash = self.calculate_hash(transaction_data)
            if calculated_hash != current_transaction['hash']:
                return False  # Hash mismatch

            # Verify the previous_hash points to the previous transaction
            if current_transaction['previous_hash'] != previous_transaction['hash']:
                return False  # Previous hash mismatch

            # Verify authority_signature
            authority_signature_bytes = bytes.fromhex(current_transaction['authority_signature'])
            for pub_key_pem in AUTHORITY_PUBLIC_KEYS:
                try:
                    # Load the public key from PEM format
                    public_key = load_pem_public_key(pub_key_pem.encode("utf-8"))

                    # Verify the authority signature
                    public_key.verify(
                        authority_signature_bytes,
                        calculated_hash.encode(),  # Data being verified
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
