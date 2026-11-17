
import base64
import json
import os
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

def generate_rsa_keys(private_path, public_path, password):
    private_path, public_path = Path(private_path), Path(public_path)
    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    enc = serialization.BestAvailableEncryption(password.encode("utf-8"))
    private_path.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, enc))
    public_path.write_bytes(private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    return str(private_path), str(public_path)

def load_public_key(path):
    return serialization.load_pem_public_key(Path(path).read_bytes())

def load_private_key(path, password):
    return serialization.load_pem_private_key(Path(path).read_bytes(), password=password.encode("utf-8"))

def _derive_key(password, salt):
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    return kdf.derive(password.encode("utf-8"))

def encrypt_password_payload(data: bytes, password: str) -> bytes:
    salt, nonce = os.urandom(16), os.urandom(12)
    key = _derive_key(password, salt)
    ciphertext = AESGCM(key).encrypt(nonce, data, b"agentic-exam-package-v1")
    return b"AE1" + salt + nonce + ciphertext

def decrypt_password_payload(blob: bytes, password: str) -> bytes:
    if not blob.startswith(b"AE1"):
        raise ValueError("Unsupported or invalid encrypted exam package.")
    salt, nonce, ciphertext = blob[3:19], blob[19:31], blob[31:]
    key = _derive_key(password, salt)
    return AESGCM(key).decrypt(nonce, ciphertext, b"agentic-exam-package-v1")

def encrypt_submission(data: bytes, public_key_path) -> bytes:
    public_key = load_public_key(public_key_path)
    # RSA-OAEP only handles small payloads. Use a random AES key for the actual submission.
    aes_key, nonce = os.urandom(32), os.urandom(12)
    wrapped_key = public_key.encrypt(aes_key, padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(), label=b"agentic-submission-v1"))
    ciphertext = AESGCM(aes_key).encrypt(nonce, data, b"agentic-submission-v1")
    return b"AS1" + len(wrapped_key).to_bytes(2, "big") + wrapped_key + nonce + ciphertext

def decrypt_submission(blob: bytes, private_key) -> bytes:
    if not blob.startswith(b"AS1"):
        raise ValueError("Invalid submission file.")
    n = int.from_bytes(blob[3:5], "big")
    wrapped_key = blob[5:5+n]
    nonce = blob[5+n:17+n]
    ciphertext = blob[17+n:]
    aes_key = private_key.decrypt(wrapped_key, padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(), label=b"agentic-submission-v1"))
    return AESGCM(aes_key).decrypt(nonce, ciphertext, b"agentic-submission-v1")
