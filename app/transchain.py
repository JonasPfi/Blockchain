from datetime import datetime
import hashlib
import requests
from models import Transaction, TransactionChain
from rsa_utils import *

class Transchain:
    def __init__(self, AUTHORITY_NODES):
        """
        Initialize the Transchain with a genesis transaction and an empty list for authority public keys.
        """
        self.transaction_chain = TransactionChain(transactions=[self.create_genesis_transaction()])
        self.authority_public_keys = []
        self.AUTHORITY_NODES = AUTHORITY_NODES


    def create_genesis_transaction(self) -> Transaction:
        """
        Create the genesis transaction for the blockchain.
        This transaction does not have previous data and serves as the first block.
        
        Returns:
            Transaction: The genesis transaction data.
        """
        transaction_data = {
            'index': 0,
            'sender': 'Genesis',
            'recipient': 'Genesis',
            'amount': 0.0,
            'expiration': None,
            'previous_hash': None,
            'sender_signature': None,
            'recipient_signature': None,
            'timestamp': str(datetime.utcnow()),
            'authority_signature': None
        }
        transaction_data['current_hash'] = self.calculate_hash(transaction_data)

        return Transaction(**transaction_data)


    def fetch_authority_public_keys(self):
        """
        Fetches public keys from all authority nodes and stores them in the list.
        """
        for node_url in self.AUTHORITY_NODES:
            try:
                print(f"Fetching public key from {node_url}")
                response = requests.get(f"{node_url}/public_key")
                if response.status_code == 200:
                    public_key = response.json().get("public_key")
                    self.authority_public_keys.append(public_key)
            except Exception as e:
                print(f"Error fetching public key from {node_url}: {e}")


    def calculate_hash(self, data: dict) -> str:
        """
        Calculates the hash of a given block/transaction data.

        Args:
            data (dict): The data for which the hash needs to be calculated.

        Returns:
            str: The SHA-256 hash of the concatenated string representation of the data.
        """
        # Define the order and keys to be used for hashing
        keywords = ["index", "sender", "recipient", "amount", "previous_hash", "expiration"]
        string_to_hash = ''.join(str(data.get(keyword, '')) for keyword in keywords)

        return hashlib.sha256(string_to_hash.encode('utf-8')).hexdigest()


    def verify_transchain(self, transchain_to_check) -> bool:
        """
        Verifies the entire transaction chain for consistency and integrity.

        Returns:
            bool: True if the chain is valid, False otherwise.
        """
        self.fetch_authority_public_keys()
        transchain_to_check = [transaction.dict() for transaction in transchain_to_check.transactions]
        for i in range(1, len(transchain_to_check)):
            current_transaction = transchain_to_check[i]
            previous_transaction = transchain_to_check[i - 1]

            # Verify the current hash
            if current_transaction['current_hash'] != self.calculate_hash(transchain_to_check[i]):
                print(f"Invalid hash at index {i}")
                return False

            # Verify the chaining
            if current_transaction['previous_hash'] != previous_transaction['current_hash']:
                return False

            # Verify sender signature
            sender_public_key = self.get_public_key_from_node(current_transaction['sender'])
            if not verify_signature(sender_public_key, current_transaction['sender_signature'], current_transaction['current_hash']):
                print(f"Invalid sender signature at index {i}")
                return False

            # Verify recipient signature
            recipient_public_key = self.get_public_key_from_node(current_transaction['recipient'])
            if not verify_signature(recipient_public_key, current_transaction['recipient_signature'], current_transaction['current_hash']):
                print(f"Invalid recipient signature at index {i}")
                return False

            # Verify authority signature - At least one must be valid
            valid_authority_signature = False
            for authority_public_key in self.authority_public_keys:
                if verify_signature(authority_public_key, current_transaction['authority_signature'], current_transaction['current_hash']):
                    valid_authority_signature = True
                    break 

            if not valid_authority_signature:
                print(f"Invalid authority signature at index {i}")
                return False

        return True



    def get_public_key_from_node(self, node: str) -> str:
        """
        Fetches the public key of a given node.

        Args:
            node (str): The node from which to fetch the public key.

        Returns:
            str: The public key in PEM format.
        """
        try:
            response = requests.get(f"http://{node}:8000/public_key")
            response.raise_for_status()
            return response.json().get('public_key')
        except requests.RequestException as e:
            print(f"Error fetching public key from {node}: {e}")
            return ""
    

    def verify_transaction(self, transaction_data, PRIVATE_KEY_FILE) -> bool:
        """
        Verifies the transaction by checking its hash, signatures, and other validation criteria.
        
        - **transaction_data**: Type !Dict!.
        - **PRIVATE_KEY_FILE**: Path to the private key file for signing.
        
        Returns:
            - `bool`: `True` if the transaction is valid and updated, `False` otherwise.
            - If valid, the updated transaction data is returned; otherwise, `False`.
        """
        transaction_hash = self.calculate_hash(transaction_data)
        # Check if the current hash matches
        if transaction_hash != transaction_data["current_hash"]:
            return False
        # Check if the previous hash matches the last transaction's current hash
        if transaction_data["previous_hash"] != self.transaction_chain.transactions[-1].current_hash:
            return False
        # Check if the transaction index matches the length of the chain
        print("g")
        if transaction_data["index"] != len(self.transaction_chain.transactions):
            return False
        try:
            # Get sender's public key
            sender_response = requests.get(f"http://{transaction_data['sender']}:8000/public_key")
            sender_response.raise_for_status()
            sender_public_key_pem = sender_response.json()['public_key']
            
            # Get recipient's public key
            recipient_response = requests.get(f"http://{transaction_data['recipient']}:8000/public_key")
            recipient_response.raise_for_status()
            recipient_public_key_pem = recipient_response.json()['public_key']
        
        except requests.RequestException as e:
            print(f"Error retrieving public keys: {e}")
            return False
        
        # Verify sender's and recipient's signatures
        if not verify_signature(sender_public_key_pem, transaction_data['sender_signature'], transaction_hash):
            print("Invalid sender signature")
            return False
        
        if not verify_signature(recipient_public_key_pem, transaction_data['recipient_signature'], transaction_hash):
            print("Invalid recipient signature")
            return False
        return True
    

    def verify_auth_transaction(self, transaction_data):
        """
        Verifies the transaction by checking its hash, signatures, and other validation criteria.
        
        - **transaction**: The transaction to verify.
        
        Returns:
            - `bool`: `True` if the transaction is valid and updated, `False` otherwise.
            - If valid, the updated transaction data is returned; otherwise, `False`.
        """
        self.fetch_authority_public_keys()

        transaction_hash = self.calculate_hash(transaction_data)

        # Check if the current hash matches
        if transaction_hash != transaction_data["current_hash"]:
            return False

        # Check if the previous hash matches the last transaction's current hash
        if transaction_data["previous_hash"] != self.transaction_chain.transactions[-1].current_hash:
            return False

        # Check if the transaction index matches the length of the chain
        if transaction_data["index"] != len(self.transaction_chain.transactions):
            return False
        valid_authority_signature = False
        for authority_public_key in self.authority_public_keys:
            if verify_signature(authority_public_key, transaction_data['authority_signature'], transaction_data['current_hash']):
                valid_authority_signature = True
                break 
        if not valid_authority_signature:
            return False
        return True


    def synchronize(self, transchain):
        if not self.verify_transchain(transchain):
            return "Transchain not valid"
        if len(transchain.transactions) > len(self.transaction_chain.transactions):
            self.transaction_chain = transchain 
        return "Synchronized"
    
    def calculate_balance(self, node_name: str):
        balance = 0
        for transaction in self.transaction_chain.transactions:
            if transaction.sender == transaction.recipient == node_name:
                balance += transaction.amount
                continue
            if transaction.sender == node_name:
                balance -= transaction.amount
            if transaction.recipient == node_name:
                balance += transaction.amount
        return balance
    
    def validate_deposit(self, transaction: Transaction, container_name: str) -> bool:
        transaction_data = transaction.model_dump() if not isinstance(transaction, dict) else transaction

        # Check if the sender and recipient are the same as the container name
        if transaction_data['sender'] != container_name:
            return False
        if transaction_data['recipient'] != container_name:
            return False
        
        # Retrieve the public key of the container
        public_key_pem = self.get_public_key_from_node(container_name)
        
        # Validate the sender's signature
        if not verify_signature(public_key_pem, transaction_data['sender_signature'], transaction_data['current_hash']):
            return False
        
        # Validate the recipient's signature
        if not verify_signature(public_key_pem, transaction_data['recipient_signature'], transaction_data['current_hash']):
            return False
        
        # If all checks passed, return True
        return True
