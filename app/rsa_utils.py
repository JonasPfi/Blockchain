from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key
from cryptography.exceptions import InvalidSignature

def generate_rsa_keys(private_key_file: str, public_key_file: str):
    """
    Generate RSA key pairs and save them to files.

    Args:
        private_key_file (str): Path to the file where the private key will be saved.
        public_key_file (str): Path to the file where the public key will be saved.
    """
    # Generate RSA key pair 
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    public_key = private_key.public_key()
    
    # Save the private key to a file
    with open(private_key_file, "wb") as file:
        file.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
        )

    # Save the public key to a file
    with open(public_key_file, "wb") as file:
        file.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        )

def load_public_key(public_key_file: str) -> str:
    """
    Load the public key from a PEM file.

    Args:
        public_key_file (str): Path to the PEM file containing the public key.

    Returns:
        str: The public key in PEM format as a string.
    """
    with open(public_key_file, "rb") as file:
        return file.read().decode()

def load_private_key(file_path: str):
    """
    Load a private key from a PEM file.

    Args:
        file_path (str): Path to the PEM file containing the private key.

    Returns:
        PrivateKey: The loaded private key object.
    """
    with open(file_path, "rb") as file:
        return serialization.load_pem_private_key(
            file.read(),
            password=None
        )

def sign_data(private_key_file: str, data: str) -> str:
    """
    Sign the given data using the private key from a PEM file.

    Args:
        private_key_file (str): Path to the PEM file containing the private key.
        data (str): The data to be signed.

    Returns:
        str: The signature in hexadecimal format.
    """
    try:
        private_key = load_private_key(private_key_file)

        # Sign the data
        signature = private_key.sign(
            data.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        return signature.hex()
    except Exception as e:
        print(f"Error during data signing: {e}")
        raise

def verify_signature(public_key_pem: str, signature_hex: str, data_hash: str) -> bool:
    """
    Verify the signature of the given data using the provided public key.

    Args:
        public_key_pem (str): The PEM encoded public key as a string.
        signature_hex (str): The signature in hexadecimal format.
        data_hash (str): The hash of the data to verify against.

    Returns:
        bool: True if the signature is valid, False otherwise.
    """
    try:
        public_key = load_pem_public_key(public_key_pem.encode("utf-8"))

        signature = bytes.fromhex(signature_hex)

        # Verify the signature
        public_key.verify(
            signature,
            data_hash.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except InvalidSignature:
        return False
    except Exception as e:
        print(f"Error during signature verification: {e}")
        return False
