import base64
import codecs
import uuid
from hashlib import sha256


def percentage_of(a, b):
    return int((a / 100) * b)


def obfuscate(d: bytes, k: bytes) -> bytes:
    return bytes(c ^ k[i % len(k)] for i, c in enumerate(d))


def get_unique() -> bytes:
    return sha256(uuid.UUID(int=uuid.getnode()).bytes).digest()


def get_key(d: str) -> bytes:
    return sha256(obfuscate(codecs.encode(d, 'rot13').encode('utf-8'), get_unique())).digest()


def read_obfuscation(k: str, d: str) -> str:
    return obfuscate(base64.b64decode(d), get_key(k)).decode('utf-8')


def write_obfuscation(k: str, d: str) -> str:
    return base64.b64encode(obfuscate(d.encode('utf-8'), get_key(k))).decode('utf-8')
