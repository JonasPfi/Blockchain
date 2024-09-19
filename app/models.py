from pydantic import BaseModel
from typing import Optional, List

class Transaction(BaseModel):
    index: int
    sender: str
    recipient: str
    amount: float
    expiration: Optional[str] = None
    previous_hash: Optional[str] = None
    current_hash: Optional[str] = None
    sender_signature: Optional[str] = None
    recipient_signature: Optional[str] = None
    timestamp: str
    authority_signature: Optional[str] = None

class TransactionChain(BaseModel):
    transactions: List[Transaction]

class PrepareTransaction(BaseModel):
    index: int
    sender: str
    recipient: str
    amount: float
    expiration: str
    previous_hash: Optional[str] = None
    current_hash: Optional[str] = None
    sender_signature: Optional[str] = None
    recipient_signature: Optional[str] = None
    timestamp: str
    authority_signature: Optional[str] = None
    container_name: str

class SendTransactionRequest(BaseModel):
    container: str
    amount: float

class AcceptTransactionRequest(BaseModel):
    number: int

class ContainerName(BaseModel):
    name: str