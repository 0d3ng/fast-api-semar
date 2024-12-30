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
import base64
import hashlib
import hmac
import json
import os
import random
import string
import zlib
from datetime import timedelta

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from app.middlewares.auth import create_access_token, verify_token_device
from app.utils.config import PRIVATE_KEY_PATH, PUBLIC_KEY_PATH, ACCESS_TOKEN_EXPIRE_DEVICE_DAYS


def generate_secret(length=32):
    characters = string.ascii_letters + string.digits + string.punctuation
    secret = ''.join(random.choice(characters) for i in range(length))
    return secret


def generate_hmac_token(secret, data):
    message = json.dumps(data)
    hmac_token = hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(hmac_token).decode('utf-8')


def verify_hmac_token(secret, data, token):
    expected_token = generate_hmac_token(secret, data)
    return hmac.compare_digest(expected_token, token)


# Generate private and public keys
def generate_keys():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()
    return private_key, public_key


# Generate a random 256-bit key
def generate_key_cha_cha():
    return base64.urlsafe_b64encode(ChaCha20Poly1305.generate_key()).decode('utf-8')


def encrypt_cha_data(key_base64, data):
    key = base64.urlsafe_b64decode(key_base64.encode('utf-8'))
    chacha = ChaCha20Poly1305(key)
    nonce = os.urandom(12)
    encrypted_data = chacha.encrypt(nonce, json.dumps(data).encode('utf-8'), None)
    return base64.urlsafe_b64encode(nonce + encrypted_data).decode('utf-8')


def decrypt_cha_data(key_base64, encrypted_data_base64):
    key = base64.urlsafe_b64decode(key_base64.encode('utf-8'))
    encrypted_data = base64.urlsafe_b64decode(encrypted_data_base64.encode('utf-8'))
    chacha = ChaCha20Poly1305(key)
    nonce = encrypted_data[:12]
    ciphertext = chacha.decrypt(nonce, encrypted_data[12:], None)
    return json.loads(ciphertext.decode('utf-8'))


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
    compressed_data = zlib.compress(serialized_data)
    encrypted_data = public_key.encrypt(
        compressed_data,
        padding=padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    encrypted_data_base64 = base64.b64encode(encrypted_data).decode('utf-8')
    return encrypted_data_base64


# Decrypt data
def decrypt_data(private_key, encrypted_data_hex):
    encrypted_data = base64.b64decode(encrypted_data_hex)
    decrypted_data = private_key.decrypt(
        encrypted_data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    decompressed_data = zlib.decompress(decrypted_data)
    return json.loads(decompressed_data.decode('utf-8'))


# be carefully!!!
# write key from root directory please
# private_key, public_key = generate_keys()
# write_keys(private_key=private_key, public_key=public_key, private_key_path=PRIVATE_KEY_PATH,
#            public_key_path=PUBLIC_KEY_PATH)

# and then load key
# pem_private_key, pem_public_key = load_keys(public_key_path=PUBLIC_KEY_PATH, private_key_path=PRIVATE_KEY_PATH)

# pem_private_key, pem_public_key = serialize_keys(private_key, public_key)
# print(f"private key: {pem_private_key} public key: {pem_public_key}")

data = {
    "dev_id": "device123",
    "dev_code": "ABC123",
    "usr_id": "user123",
    "exp": "2024-12-31 23:59:59"
}

# encrypted_data = encrypt_data(public_key, data)
# decrypted_data = decrypt_data(private_key, encrypted_data)
#
# print("Original Data:", data)
# print("Encrypted Data (hex):", encrypted_data)
# print("Length of Encrypted Data (in hex):", len(encrypted_data))
# print(f"Decrypted Data: {decrypted_data} dev id: {decrypted_data['dev_id']}")

# secret_key = generate_secret(24)
# print(f"Secret: {secret_key} type: {type(secret_key)}")
# token = generate_hmac_token(secret_key, data)
# print(f"Generated HMAC Token: {token}")
#
# is_valid = verify_hmac_token(secret_key, data, token)
# print(f"Verified HMAC Token: {is_valid}")

secret_key = generate_key_cha_cha()
print(f"Secret: {secret_key} type: {type(secret_key)}")
token = encrypt_cha_data(secret_key, data)
print(f"Generated HMAC Token: {token} length: {len(token)}")

decrypted = decrypt_cha_data(secret_key, token)
print(f"Decrypted: {decrypted} dev_id: {decrypted['dev_id']}")

# token usually
# data = {
#     "dev_id": "device123",
#     "dev_code": "ABC123",
#     "usr_id": "user123"
# }
# exp = timedelta(days=int(ACCESS_TOKEN_EXPIRE_DEVICE_DAYS))
# token = create_access_token(data=data, expires_delta=exp)
# print(f"Token: {token} len: {len(token)}")
# token_dev = verify_token_device(token)
# print(f"token_dev: {token_dev.device_id}")
