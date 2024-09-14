from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
import requests
from typing import List
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
import os
from models import Transaction, SendTransactionRequest, AcceptTransactionRequest
from transchain import Transchain
from rsa_utils import generate_rsa_keys, sign_data, verify_signature, load_public_key, load_private_key

app = FastAPI()

container_name = os.getenv("CONTAINERNAME")

AUTHORITY_NODES = ["http://fastapi_app_2:8000/"]
transaction_requests: List[Transaction] = []

PRIVATE_KEY_FILE = "private_key.pem"
PUBLIC_KEY_FILE = "public_key.pem"

generate_rsa_keys(PRIVATE_KEY_FILE, PUBLIC_KEY_FILE)

# Initialize ledger
transchain = Transchain(AUTHORITY_NODES)

@app.get("/")
def read_root():
    """Returns a welcome message."""
    return {"message": "Hello from FastAPI!"}

@app.get("/transactions")
def get_transactions():
    """Returns the list of transactions in the blockchain."""
    return {"transactions": transchain.get_transactions()}

@app.post("/add_transaction/")
def add_transaction(transaction: Transaction):
    """
    Adds a transaction to the ledger and returns the updated list of transactions.
    
    - **transaction**: The transaction to be added.
    """
    transchain.transactions.append(transaction.dict())
    return {"message": "Transaction added", "transactions": transchain.get_transactions()}

@app.get("/verify_chain")
def verify_chain():
    """Checks if the blockchain is valid and returns the result."""
    if transchain.verify_transchain():
        return {"message": "Chain is valid"}
    return {"error": "Chain verification failed"}

@app.get("/public_key")
def get_public_key():
    """Returns the public key of this FastAPI application."""
    public_key = load_public_key(PUBLIC_KEY_FILE)
    return {"public_key": public_key}

@app.post("/send_transaction/")
def send_transaction(request: SendTransactionRequest):
    """
    Sends a transaction to a recipient container.
    
    - **request**: Contains the recipient container and amount to be transferred.
    """
    recipient_container = request.container
    amount = request.amount

    current_time = datetime.utcnow()
    expiration_time = current_time + timedelta(minutes=10)

    transaction_data = {
        "index": transchain.transactions[-1]["index"] + 1,
        "sender": container_name,
        "recipient": recipient_container,
        "amount": amount,
        "previous_hash": transchain.transactions[-1]["current_hash"],
        "expiration": expiration_time.isoformat()
    }

    transaction_hash = transchain.calculate_hash(transaction_data)
    signature = sign_data(PRIVATE_KEY_FILE, transaction_hash)

    transaction = {
        **transaction_data,
        "current_hash": transaction_hash,
        "sender_signature": signature,
        "recipient_signature": "",
        "timestamp": "",
        "authority_signature": ""
    }
    
    response = requests.post(f"http://{recipient_container}:8000/receive_transaction/", json=transaction)
    return {"message": "Transaction sent", "response": response.json()}

@app.post("/receive_transaction/")
def receive_transaction(transaction: Transaction):
    """
    Receives a transaction and appends it to the local list of transaction requests.
    
    - **transaction**: The transaction to be received.
    """
    transaction_requests.append(transaction)
    return {"message": "Transaction received"}

@app.get("/show_transactions")
def show_transactions():
    """Returns the list of received transactions."""
    return {"transactions": transaction_requests}

@app.post("/accept_transaction/")
def accept_transaction(request: AcceptTransactionRequest):
    """
    Accepts a transaction request, signs it, and sends it to an authority node.
    
    - **request**: Contains the index of the transaction request to accept.
    """
    index_of_request = request.number

    if index_of_request < 0 or index_of_request >= len(transaction_requests):
        raise HTTPException(status_code=400, detail="Invalid transaction index")

    transaction_request = transaction_requests[index_of_request].dict()

    private_key = load_private_key(PRIVATE_KEY_FILE)
    transaction_hash = transchain.calculate_hash(transaction_request)

    if transaction_hash != transaction_request["current_hash"]:
        return {"error": "Transaction was manipulated"}

    signature = sign_data(PRIVATE_KEY_FILE, transaction_hash)
    transaction_request['recipient_signature'] = signature

    # Figuring out what authority node to be used is still in planning
    # for test purposes it is left to the first node
    authority_url = f"{AUTHORITY_NODES[0]}verify_transaction/"
    response = requests.post(authority_url, json=transaction_request)
    return {"message": response.json()}

@app.post("/verify_transaction/")
def verify_transaction(transaction: Transaction):
    """
    Verifies the transaction by checking its hash and signatures, then adds it to the chain.
    
    - **transaction**: The transaction to verify and add.
    """
    transaction_data = transaction.dict()
    transaction_hash = transchain.calculate_hash(transaction_data)

    if transaction_hash != transaction_data["current_hash"]:
        return {"error": "Manipulated transaction"}

    try:
        sender_response = requests.get(f"http://{transaction_data['sender']}:8000/public_key")
        sender_response.raise_for_status()
        sender_public_key_pem = sender_response.json()['public_key']
        
        recipient_response = requests.get(f"http://{transaction_data['recipient']}:8000/public_key")
        recipient_response.raise_for_status()
        recipient_public_key_pem = recipient_response.json()['public_key']
    
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not verify_signature(sender_public_key_pem, transaction_data['sender_signature'], transaction_hash):
        raise HTTPException(status_code=400, detail="Invalid sender signature")
    
    if not verify_signature(recipient_public_key_pem, transaction_data['recipient_signature'], transaction_hash):
        raise HTTPException(status_code=400, detail="Invalid recipient signature")
    
    try:
        signature = sign_data(PRIVATE_KEY_FILE, transaction_hash)
        transaction_data["authority_signature"] = signature
        transaction_data["timestamp"] = str(datetime.utcnow())
        transchain.transactions.append(transaction_data)
        return {"message": "Transaction verified and added to the chain"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error signing transaction: {e}")
