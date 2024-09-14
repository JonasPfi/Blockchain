from fastapi import FastAPI, HTTPException, Request
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
import random
import traceback
app = FastAPI()

container_name = os.getenv("CONTAINERNAME")
blocked_index = None
AUTHORITY_NODES = ["http://fastapi_app_2:8000/", "http://fastapi_app_3:8000", "http://fastapi_app_4:8000"]
transaction_requests: List[Transaction] = []

PRIVATE_KEY_FILE = "private_key.pem"
PUBLIC_KEY_FILE = "public_key.pem"

generate_rsa_keys(PRIVATE_KEY_FILE, PUBLIC_KEY_FILE)
synchronization_needed = False
votes_cast = {}
# Initialize transaction chain
transchain = Transchain(AUTHORITY_NODES)

@app.get("/")
def read_root():
    """Returns a welcome message."""
    return {"message": "Hello from FastAPI!"}

@app.get("/transactions")
def get_transactions():
    """Returns the list of transactions in the blockchain."""
    return {"transactions": transchain.get_transactions()}

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

    # Retry in case a authority is down
    for _ in range(0, 3):
        random_authority = random.randint(0, len(AUTHORITY_NODES)-1)
        print("random auth", random_authority)
        response = requests.post(f'{AUTHORITY_NODES[random_authority]}/verify_transaction', json=transaction_request)
        if response.status_code == 200:  # API returned OK
            print(f"Transaction verification process initiated")
            break  # Exit loop if verification is successful
    return {"message": response.json()}

"""
Authority Routes
"""
@app.post("/verify_transaction/")
def verify_transaction(transaction: Transaction):
    """
    Verifies the transaction by checking its hash and signatures, then adds it to the chain.
    
    - **transaction**: The transaction to verify and add.
    """
    transaction_data = transaction.dict()
    global container_name
    if not transchain.verify_transaction(transaction_data, PRIVATE_KEY_FILE):
        return {"message": "transaction is not valid"}
    
    try:
        signature = sign_data(PRIVATE_KEY_FILE, transaction_data["current_hash"])
        transaction_data["authority_signature"] = signature
        transaction_data["timestamp"] = str(datetime.utcnow())
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error signing transaction: {e}")

    approvals = len(AUTHORITY_NODES) - 1  # Quorum
    successful_approvals = 0
    global synchronization_needed
    try:
        for authority_node in AUTHORITY_NODES:
            authority_url = f"{authority_node}/prepare_transaction/"
            
            # Send the request to the authority node
            response = requests.post(authority_url, json=transaction.dict())


            # Check if the response is OK (successful approval)
            if response.ok:
                response_data = response.json()
                if response_data.get("status") == "accepted":
                    print(f"Transaction approved by {authority_node}")
                    successful_approvals += 1  # Increment successful approvals
                elif response_data.get("message") == "we have to synchronize...":
                    print(f"Synchronization required by {authority_node}")
                    synchronization_needed = True
                    # You can add additional synchronization logic here if needed
                    break  # Break out of the loop to handle synchronization
                elif response_data.get("message") == "sorry transaction is already going":
                    print(f"Transaction blocked by {authority_node} (already in process)")
                else:
                    print(f"Unknown response from {authority_node}: {response_data}")
            else:
                print(f"Transaction approval failed from {authority_node}: {response.status_code}")

            # If the response is None or failed, adjust the approvals
            if not response:
                approvals -= 1  # Reduce required approvals for quorum

            # Check if quorum (enough approvals) has been reached
            if successful_approvals >= approvals:
                print("Consensus reached, transaction can be committed.")
                break  # Break out of the loop as we have enough approvals

    except Exception as e:
        print(e) 

    if synchronization_needed:
        print("Starting blockchain synchronization process...")

    if successful_approvals >= approvals:
        for authority_node in AUTHORITY_NODES:
            try:
                response = requests.post(f'{authority_node}/add_to_chain', json=transaction_data)
            except Exception as e:
                print(e)
        return {"message": "transaction accepted"}
    else:
        initiaze_lock_release(transaction_data['index'])
        print("Transaction failed to reach consensus.")

@app.post('/prepare_transaction')
def prepare_transaction(transaction: Transaction):
    global blocked_index
    transaction_data = transaction.dict()
    transaction_data_index = transaction_data['index']  
    # Überprüfe, ob der Index der Transaktion mit der aktuellen Länge der Blockchain übereinstimmt
    if transaction_data_index != len(transchain.transactions):
        # Falls nicht, synchronisieren und den Index der lokalen Blockchain zurückgeben
        blocked_index = transaction_data_index
        return {
            'message': 'We need to synchronize...', 
            'current_index': len(transchain.transactions),  
            'suggestion': 'Please use the longer chain as the source of truth.'
        }
    
    if transaction_data_index == blocked_index:
        return {'message': 'Sorry, transaction is already in process.'}
    
    else:
        return {'message': 'Transaction is good to go.', 'status': 'accepted'}

@app.post("/lock_release_vote/")
def receive_lock_release_vote(request: AcceptTransactionRequest):
    global container_name
    global vote_cast
    # Use await to get the JSON data from the request
    request_data = request.dict()

    transaction_index = request_data['number']
    if transaction_index is None:
        raise HTTPException(status_code=400, detail="Missing transaction_index")

    # If no vote has been cast for this transaction yet, accept this vote
    if transaction_index not in votes_cast:
        votes_cast[transaction_index] = container_name
        return {"message": "Vote accepted", "voted_for": container_name}
    # If a vote has already been cast, reject the request
    return {"message": "Vote rejected, already voted for", "voted_for": votes_cast[transaction_index]}


@app.post("/unlock_transaction/")
def unlock_transaction(request):
    request_data = request.json()
    transaction_index = request_data['transaction_index']
    winner_node = request_data['winner_node']

    # Break the lock for the transaction index
    # Reset state or handle synchronization as needed
    print(f"Unlocking transaction {transaction_index} as directed by {winner_node}.")
    return {"message": f"Transaction {transaction_index} unlocked."}
@app.post("/add_to_chain/")
def accept_transaction(transaction: Transaction):
    transaction_data = transaction.dict()
    if transchain.verify_auth_transaction(transaction_data):
        transchain.transactions.append(transaction_data)
        return {"Message": "transaction added"}
    return {"message": "transaction not added"}
def initiaze_lock_release(transaction_index):
    votes_received = 0
    try:
        for authority_node in AUTHORITY_NODES:
            if authority_node != container_name:
                release_request_url = f"{authority_node}/lock_release_vote/"
                release_data = {'number': int(transaction_index)}
                response = requests.post(release_request_url, json=release_data)

                if response.ok:
                    votes_received += 1
                else:
                    print(f"{authority_node} did not approve the lock release.")

        return votes_received

    except Exception as e:
        print(f"An error occurred during lock release voting: {e}")
        return 0


def finalize_lock_release(transaction_index, container_name, votes_received):
    # Determine if this node won the vote
    if votes_received > (len(AUTHORITY_NODES) / 2):  # Majority wins
        print(f"{container_name} won the vote with {votes_received} votes.")
        broadcast_unlock(transaction_index, container_name)
    else:
        print(f"{container_name} lost the vote with only {votes_received} votes.")

def broadcast_unlock(transaction_index, container_name):
    try:
        for authority_node in AUTHORITY_NODES:
            unlock_url = f"{authority_node}/unlock_transaction/"
            unlock_data = {'transaction_index': transaction_index, 'winner_node': container_name}
            response = requests.post(unlock_url, json=unlock_data)

            if response.ok:
                print(f"Transaction {transaction_index} unlocked at {authority_node}.")
            else:
                print(f"Failed to unlock transaction {transaction_index} at {authority_node}.")

    except Exception as e:
        print(f"An error occurred during broadcast unlock: {e}")
