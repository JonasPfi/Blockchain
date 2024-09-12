from datetime import datetime
import hashlib
import requests
from models import Transaction

class Transchain:
    def __init__(self):
        """
        Initialize the Transchain with a genesis transaction and an empty list for authority public keys.
        """
        self.transactions = [self.create_genesis_transaction()]
        self.authority_public_keys = []

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
        for node_url in AUTHORITY_NODES:
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
