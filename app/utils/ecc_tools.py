#  """
#  Copyright (c) 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-27 16:40:01
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-12-27 16:40:00
#  File: ecc_tools.py
#  Description:
#  """
import binascii

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.concatkdf import ConcatKDFHash
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import json
import os

from app.utils.config import PUBLIC_KEY_PATH, PRIVATE_KEY_PATH


# Generate private and public keys
def generate_keys():
    private_key = ec.generate_private_key(ec.SECP384R1())
    public_key = private_key.public_key()
    return private_key, public_key


# Serialize keys to PEM format
def write_keys(private_key, public_key, private_key_path, public_key_path):
    try:
        pem_private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        pem_public_key = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        with open(private_key_path, 'wb') as f:
            f.write(pem_private_key)

        with open(public_key_path, 'wb') as f:
            f.write(pem_public_key)
        print("Write key succeed")
    except Exception as e:
        print(e)


# Serialize keys to PEM format
def serialize_keys(private_key, public_key):
    try:
        pem_private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        pem_public_key = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem_private_key, pem_public_key
    except Exception as e:
        print(e)


def load_keys(private_key_path, public_key_path):
    try:
        with open(private_key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(f.read(), None, None)
        with open(public_key_path, 'rb') as f:
            public_key = serialization.load_pem_public_key(f.read(), None)
        print("Load key succeed")
        return private_key, public_key
    except Exception as e:
        print(e)


# Encrypt data
def encrypt_data(public_key, data):
    serialized_data = json.dumps(data).encode()

    # Generate a symmetric key using ECDH
    symmetric_key = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    kdf = ConcatKDFHash(algorithm=hashes.SHA256(), length=32, otherinfo=None)
    derived_key = kdf.derive(symmetric_key)

    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(derived_key), modes.CFB(iv))
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(serialized_data) + encryptor.finalize()
    encrypted_data_hex = binascii.hexlify(encrypted_data).decode()
    iv_hex = binascii.hexlify(iv).decode()
    return encrypted_data_hex, iv_hex


# Decrypt data
def decrypt_data(private_key, encrypted_data_hex, iv_hex):
    # Generate the same symmetric key using ECDH
    encrypted_data = binascii.unhexlify(encrypted_data_hex)
    iv = binascii.unhexlify(iv_hex)
    symmetric_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    kdf = ConcatKDFHash(algorithm=hashes.SHA256(), length=32, otherinfo=None)
    derived_key = kdf.derive(symmetric_key)

    cipher = Cipher(algorithms.AES(derived_key), modes.CFB(iv))
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

    return json.loads(decrypted_data.decode())


# be carefully!!!
# write key from root directory please
private_key, public_key = generate_keys()
write_keys(private_key=private_key, public_key=public_key, private_key_path=PRIVATE_KEY_PATH,
           public_key_path=PUBLIC_KEY_PATH)

# and then load key
pem_private_key, pem_public_key = load_keys(public_key_path=PUBLIC_KEY_PATH, private_key_path=PRIVATE_KEY_PATH)

# pem_private_key, pem_public_key = serialize_keys(private_key, public_key)
# print(f"private key: {pem_private_key.decode()} public key: {pem_public_key.decode()}")

data = {
    "dev_id": "device123",
    "dev_code": "ABC123",
    "usr_id": "user123",
    "exp": "2024-12-31 23:59:59"
}

encrypted_data, iv = encrypt_data(public_key, data)
decrypted_data = decrypt_data(private_key, encrypted_data, iv)

print("Original Data:", data)
print("Encrypted Data (hex):", encrypted_data)
print("Length of Encrypted Data (in hex):", len(encrypted_data))
print("Decrypted Data:", decrypted_data)
