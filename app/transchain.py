from datetime import datetime
import hashlib
import requests
from models import Transaction
from rsa_utils import *

class Transchain:
    def __init__(self, AUTHORITY_NODES):
        """
        Initialize the Transchain with a genesis transaction and an empty list for authority public keys.
        """
        self.transactions = [self.create_genesis_transaction()]
        self.authority_public_keys = []
        self.AUTHORITY_NODES = AUTHORITY_NODES

    def create_genesis_transaction(self) -> dict:
        """
        Create the genesis transaction for the blockchain.
        This transaction does not have previous data and serves as the first block.
        
        Returns:
            dict: The genesis transaction data.
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

        return transaction_data

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

    def get_transactions(self) -> list[dict]:
        """
        Retrieve the list of transactions.

        Returns:
            list: The list of transactions in the blockchain.
        """
        return self.transactions

    def verify_transchain(self) -> bool:
        """
        Verifies the entire transaction chain for consistency and integrity.

        Returns:
            bool: True if the chain is valid, False otherwise.
        """
        self.fetch_authority_public_keys()

        for i in range(1, len(self.transactions)):
            current_transaction = self.transactions[i]
            previous_transaction = self.transactions[i - 1]

            # Verify the current hash
            if current_transaction['current_hash'] != self.calculate_hash(self.transactions[i]):
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