from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from datetime import datetime, timedelta
import requests
from typing import List
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.exceptions import InvalidSignature
import time
import os
from models import Transaction, SendTransactionRequest, AcceptTransactionRequest
from transchain import Transchain
from rsa_utils import * 
from rsa_utils import verify_signature

app = FastAPI()

container_name = os.getenv("CONTAINERNAME")

AUTHORITY_NODES = ["http://fastapi_app_2:8000/"]
AUTHORITY_PUBLIC_KEYS = []  # Public keys fetched from authority nodes

transaction_requests = []

PRIVATE_KEY_FILE = "private_key.pem"
PUBLIC_KEY_FILE = "public_key.pem"

generate_rsa_keys(PRIVATE_KEY_FILE, PUBLIC_KEY_FILE)


# Create Ledger
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
    public_key = load_public_key(PUBLIC_KEY_FILE)
    return {"public_key": public_key}



@app.post("/send_transaction/")
def send_transaction(request: SendTransactionRequest):
    # Extract the port and amount from the request body
    recipient_container = request.container
    amount = request.amount

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
    signature = sign_data(PRIVATE_KEY_FILE, transaction_hash)

    # Update the transaction with the signature
    transaction = {
        **transaction_data,
        "current_hash": transaction_hash,
        "sender_signature": signature,
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
    private_key = load_private_key(PRIVATE_KEY_FILE)
    # Define the current time
    current_time = datetime.utcnow().isoformat()

    # Calculate the transaction hash
    transaction_hash = transchain.calculate_hash(transaction_request)

    if transaction_hash != transaction_request["current_hash"]:
        return {"error": "transaction was manipulated"}


    # Sign the transaction hash
    signature = sign_data(PRIVATE_KEY_FILE, transaction_hash)

    # Update the transaction with the recipient's signature
    transaction_request['recipient_signature'] = signature

    # Send the signed transaction to the authority node
    authority_url = f"{AUTHORITY_NODES[0]}verify_transaction/"
    print(authority_url)
    response = requests.post(authority_url, json=transaction_request)
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
        sender_response = requests.get(f"http://{transaction_data['sender']}:8000/public_key")
        sender_response.raise_for_status()
        sender_public_key_pem = sender_response.json()['public_key']
        
        recipient_response = requests.get(f"http://{transaction_data['recipient']}:8000/public_key")
        recipient_response.raise_for_status()
        recipient_public_key_pem = recipient_response.json()['public_key']
    
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=e)
    
    if not verify_signature(sender_public_key_pem, transaction_data['sender_signature'], transaction_hash):
        raise HTTPException(status_code=400, detail="Invalid sender signature")
    
    if not verify_signature(recipient_public_key_pem, transaction_data['recipient_signature'], transaction_hash):
         raise HTTPException(status_code=400, detail="Invalid recipient signature")
    
    try:
        signature = sign_data(PRIVATE_KEY_FILE, transaction_hash)
        transaction_data["authority_signature"] = signature
        transaction_data["timestamp"] = str(datetime.utcnow())
        transchain.transactions.append(transaction_data)

        print("Transaction added to the chain")
        return {"message": "Transaction verified and added to the chain"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error signing transaction: {e}")