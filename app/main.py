from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
import requests
import os
from models import Transaction, SendTransactionRequest, AcceptTransactionRequest, PrepareTransaction, ContainerName, TransactionChain, SendMoney
from transchain import Transchain
from rsa_utils import generate_rsa_keys, sign_data, load_public_key, load_private_key
import random
import asyncio
from lru_cache import LRUCache
app = FastAPI()
 
container_name = os.getenv("CONTAINERNAME")
blocker_set_time = None
heartbeat_interval = timedelta(seconds=5)
blocker = None 
list_of_blockers = []
AUTHORITY_NODES = ["http://fastapi_app_2:8000/", "http://fastapi_app_3:8000/", "http://fastapi_app_4:8000/"]
transaction_requests = TransactionChain(transactions=[])
transaction_cache = LRUCache(100)
connected_nodes = [] 

PRIVATE_KEY_FILE = "private_key.pem"
PUBLIC_KEY_FILE = "public_key.pem"

generate_rsa_keys(PRIVATE_KEY_FILE, PUBLIC_KEY_FILE)
synchronization_needed = False
votes_cast = {}

# Initialize transaction chain
transchain = Transchain(AUTHORITY_NODES)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(heartbeat_check())

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}

@app.get("/transactions")
def get_transactions():
    return transchain.transaction_chain.model_dump()

@app.get("/public_key")
def get_public_key():
    public_key = load_public_key(PUBLIC_KEY_FILE)
    return {"public_key": public_key}


@app.post("/send_transaction/")
def send_transaction(request: SendTransactionRequest):
    """
    Sends a transaction to a recipient container
    
    - **request**: Contains the recipient container and amount to be transferred
    """
    global container_name

    recipient_container = request.container
    amount = request.amount

    current_time = datetime.utcnow()
    expiration_time = current_time + timedelta(minutes=10)

    transaction_data = {
        "index": transchain.transaction_chain.transactions[-1].index + 1,
        "sender": container_name,
        "recipient": recipient_container,
        "amount": amount,
        "previous_hash": transchain.transaction_chain.transactions[-1].current_hash,
        "expiration": expiration_time.isoformat(),
        # Placeholders
        "current_hash": "", # Will be updated
        "sender_signature": "", # Will be updated
        "recipient_signature": "",
        "timestamp": "", # Will be updated 
        "authority_signature": ""
    }

    transaction_hash = transchain.calculate_hash(transaction_data)
    transaction_data["current_hash"] = transaction_hash
    transaction_data["sender_signature"] = sign_data(PRIVATE_KEY_FILE, transaction_hash)
    transaction_data["timestamp"] = datetime.utcnow().isoformat()
    
    transaction = Transaction(**transaction_data)

    response = requests.post(f"http://{recipient_container}:8000/receive_transaction/", json=transaction.model_dump())
    return {"message": "Transaction sent", "response": response.json()}


@app.post("/receive_transaction/")
def receive_transaction(transaction: Transaction):
    """
    Receives a transaction and appends it to the local list of transaction requests
    
    - **transaction**: The transaction to be received
    """
    global transaction_requests
    transaction_requests.transactions.append(transaction)
    return {"message": "Transaction received"}


@app.get("/show_transactions")
def show_transactions():
    return {"transaction requests": transaction_requests}


@app.post("/accept_transaction/")
def accept_transaction(request: AcceptTransactionRequest):
    """
    Accepts a transaction request, signs it, and sends it to an authority node
    
    - **request**: Contains the index of the transaction request to accept
    """
    index_of_request = request.number

    if index_of_request < 0 or index_of_request >= len(transaction_requests.transactions):
        raise HTTPException(status_code=400, detail="Invalid transaction index")

    transaction_request = transaction_requests.transactions[index_of_request].model_dump()
    transaction_hash = transchain.calculate_hash(transaction_request)

    if transaction_hash != transaction_request["current_hash"]:
        return {"error": "Transaction was manipulated"}

    signature = sign_data(PRIVATE_KEY_FILE, transaction_hash)
    transaction_request['recipient_signature'] = signature

    # Retry in case a authority is down
    for _ in range(0, 3):
        random_authority = random.randint(0, len(AUTHORITY_NODES)-1)
        response = requests.post(f'{AUTHORITY_NODES[random_authority]}/verify_transaction/', json=transaction_request)
        if response.status_code == 200:  # API returned OK
            print(f"Transaction verification process initiated")
            break  # Exit loop if verification is successful
    return {"message": response.json()}

@app.get("/get_balance")
def get_balance():
    return {"balance": transchain.calculate_balance(container_name)}
    
@app.post("/deposit_money")
def deposit_money(request: SendMoney):
    for authority_node in AUTHORITY_NODES:
        auth_deposit_money_url = f"{authority_node}/auth_deposit_money/"
        try:
            response = requests.post(auth_deposit_money_url, json=request.model_dump())
            if response.ok:
                return {"message": response.json()}
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to deposit money")
        except Exception as e:
            print(f"Error in contacting {authority_node}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error during deposit")

@app.post("/sign_money_deposit")
def sign_money_deposit(transaction: Transaction):
    global container_name
    transaction_data = transaction.model_dump()
    current_hash = transchain.calculate_hash(transaction_data)
    signature = sign_data(PRIVATE_KEY_FILE, current_hash)
    
    transaction_data["current_hash"] = current_hash
    
    if transaction.sender != container_name or transaction.recipient != container_name:
        return {"message": "error", "detail": "Invalid sender or recipient"}

    # Sign the transaction
    transaction_data["sender_signature"] = signature
    transaction_data["recipient_signature"] = signature

    return {"message": "ok", "transaction": transaction_data}


"""
Authority Routes
"""
@app.post("/auth_deposit_money")
def auth_deposit_money(request: SendMoney):
    current_time = datetime.utcnow()
    expiration_time = current_time + timedelta(minutes=10)
    
    # Create a transaction dictionary
    transaction_data = {
        "index": transchain.transaction_chain.transactions[-1].index + 1,
        "sender": request.name,
        "recipient": request.name,
        "amount": request.amount,
        "previous_hash": transchain.transaction_chain.transactions[-1].current_hash,
        "expiration": expiration_time.isoformat(),
        "current_hash": "",
        "sender_signature": "",
        "recipient_signature": "",
        "timestamp": "", 
        "authority_signature": ""
    }
    
    transaction = Transaction(**transaction_data)
    
    try:
        response = requests.post(f"http://{transaction_data['sender']}:8000/sign_money_deposit", json=transaction.model_dump())
        if response.status_code == 200:
            transaction = response.json()["transaction"]

            if transchain.validate_deposit(transaction, request.name):
                current_hash = transchain.calculate_hash(transaction)
                if current_hash != transaction["current_hash"]:
                    return {"message": "Deposit validation failed"}
                signature = sign_data(PRIVATE_KEY_FILE, current_hash)
                transaction["authority_signature"] = signature
                current_time = datetime.utcnow().isoformat()
                transaction["timestamp"] = current_time
                requests.post(f"http://{container_name}:8000/verify_transaction/", json=transaction)
                return {"message": "Deposit validated successfully"}
            else:
                return {"message": "Deposit validation failed"}
        else:
            raise HTTPException(status_code=response.status_code, detail="Signing failed")
    except Exception as e:
        print(f"Error signing transaction: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during signing")

@app.post("/verify_transaction/")
def verify_transaction(transaction: Transaction):
    """
    Verifies the transaction by checking its hash and signatures, then adds it to the chain.
    
    - **transaction**: The transaction to verify and add.
    """
    def reset_blocker():
        global blocker
        blocker = None
    global blocker 
    global container_name
    global list_of_blockers
    global blocker_set_time

    if blocker is not None:
        return {"message": "try again"}
    
    blocker = container_name
    blocker_set_time = datetime.utcnow() 
    transaction_data = transaction.model_dump()

    """
    If the sender and recipient is equal
    it is a deposit and was already verified
    (signed)
    """
    if transaction_data["sender"] == transaction_data["recipient"]:
        if not transaction_data["authority_signature"] and not transchain.verify_transaction(transaction_data):
            reset_blocker()
            return {"message": "transaction is not valid"}
    else:      
        sender_balance = transchain.calculate_balance(transaction_data["sender"])

        if sender_balance < transaction_data["amount"]:
            reset_blocker()
            return {"message": "Insufficient balance"}
        if not transchain.verify_transaction(transaction_data):
            reset_blocker()
            return {"message": "transaction is not valid"}
        
        try:
            signature = sign_data(PRIVATE_KEY_FILE, transaction_data["current_hash"])
            transaction_data["authority_signature"] = signature
            transaction_data["timestamp"] = str(datetime.utcnow())
        
        except Exception as e:
            reset_blocker()
            raise HTTPException(status_code=500, detail=f"Error signing transaction: {e}")

    approvals = len(AUTHORITY_NODES) - 1  # Quorum
    successful_approvals = 0
    prepare_transaction = transaction_data
    prepare_transaction['container_name'] = container_name

    global synchronization_needed
    try:
        for authority_node in AUTHORITY_NODES:
            authority_url = f"{authority_node}/prepare_transaction/"
            
            # Send the request to the authority node
            response = requests.post(authority_url, json=prepare_transaction)


            # Check if the response is OK (successful approval)
            if response.ok:
                response_data = response.json()
                if response_data.get("status") == "accepted":
                    print(f"Transaction approved by {authority_node}")
                    successful_approvals += 1  # Increment successful approvals
                elif response_data.get("message") == "we have to synchronize...":
                    print(f"Synchronization required by {authority_node}")
                    synchronization_needed = True
                    break  
                elif response_data.get("message") == "Sorry, transaction is already in process.":
                    list_of_blockers.append(response_data.get("blocker"))
                else:
                    print(f"Unknown response from {authority_node}: {response_data}")
            else:
                print(f"Transaction approval failed from {authority_node}: {response.status_code}")

            # If the response is None or failed, adjust the approvals
            if not response:
                approvals -= 1 

            # Check if quorum (enough approvals) has been reached
            if successful_approvals >= approvals:
                print("Consensus reached, transaction can be committed.")
                break 

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
        initiaze_lock_release()
        return {"message": "retry transaction"}


@app.post('/prepare_transaction')
def prepare_transaction(transaction: PrepareTransaction):
    global container_name
    global blocker

    transchain_len = len(transchain.transaction_chain.transactions)

    if blocker is not None:
        return {'message': 'Sorry, transaction is already in process.', 'blocker': blocker}

    transaction_data = transaction.model_dump()
    transaction_data_index = transaction_data['index']  
    if transaction_data_index != transchain_len:
        return {
            'message': 'We need to synchronize...', 
            'current_index': transchain_len,  
            'suggestion': 'Please use the longer chain as the source of truth.'
        }
    else:
        blocker = container_name
        return {'message': 'Transaction is good to go.', 'status': 'accepted'}


@app.post("/unlock_transaction/")
def unlock_transaction():
    global blocker
    global list_of_blockers
    blocker = None
    list_of_blockers = []
    return {"message": "unlocked"}


@app.post("/join")
def join(container_name: ContainerName):
    global connected_nodes
    container_name_ = str(container_name.name)
    if container_name_ not in connected_nodes:
        connected_nodes.append(container_name_)
    response = requests.post(f'http://{container_name_}:8000/synchronize', json=transchain.transaction_chain.model_dump())
    return {"message": response.text}


@app.post("/synchronize")
def synchronize(transaction_list: TransactionChain):
    if len(transaction_list.transactions) > len(transchain.transaction_chain.transactions):
        transchain.synchronize(transaction_list) 
        return {"message": "synchronized"}
    return {"message": "nothing to synchronize"}

@app.post("/add_to_chain/")

def add_to_chain(transaction: Transaction):
    global blocker
    global list_of_blockers
    global transaction_cache
    global connected_nodes

    transaction_data = transaction.model_dump()
    if transaction_cache.exists(transaction_data):
        return {"message": "transaction was already processed"}

    transaction_cache.add(transaction_data)

    if transchain.verify_auth_transaction(transaction_data):
        transchain.transaction_chain.transactions.append(transaction)
        blocker = None
        list_of_blockers = []
        for node in connected_nodes:
            print("CONNECTED NODES", connected_nodes)
            try:
                response = requests.post(f'http://{node}:8000/add_to_chain/', json=transaction.model_dump())
                if response.status_code == 200 and "transaction" not in response.json().get("message", ""):
                    connected_nodes.remove(node)
            except Exception as e:
                print(f"Error communicating with {node}: {e}")
                connected_nodes.remove(node)
        return {"message": "transaction added"}

    blocker = None
    list_of_blockers = []
    return {"message": "transaction not added"}


def initiaze_lock_release():
    global container_name
    global list_of_blockers
    if container_name == sorted(list_of_blockers)[0]:
        broadcast_unlock()

def broadcast_unlock():
    global container_name
    try:
        for authority_node in AUTHORITY_NODES:
            unlock_url = f"{authority_node}unlock_transaction/"
            response = requests.post(unlock_url)
            if response.ok:
                print(f"Transaction unlocked at {authority_node}.")
            else:
                print(f"Failed to unlock transaction at {authority_node}.")
    except Exception as e:
        print(f"An error occurred during broadcast unlock: {e}")

async def heartbeat_check():
    global blocker
    global blocker_set_time
    global list_of_blockers
    while True:
        now = datetime.utcnow()
        if blocker_set_time and (now - blocker_set_time) > heartbeat_interval:
            print("Deadlock detected. Attempting to unlock...")
            blocker = None
            blocker_set_time = None
            list_of_blockers = []
        await asyncio.sleep(1)

