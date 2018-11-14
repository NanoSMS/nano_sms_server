import hashlib
import random
import logging

from base64 import b64encode, b32encode, b16encode

from modules.settings import config

secret_api = config.secret_api


# Small task resolver
def int_to_bytes(x):
    return x.to_bytes((x.bit_length() + 7) // 8, "big")


# Computes hash of the hashed part
def get_hash(key: str, signing_key: str):
    # Uses Blake2s for a small total size. Alternative is blake2b.
    hash_index = hashlib.blake2s()
    hash_index.update(key.encode())
    hash_index.update(signing_key.encode())

    return hash_index.copy()


# Generates an API key
def generate(key=None, signing_key=None):
    # Key is a value to hash for to get a complete.
    if not key:
        rand_bytes = int_to_bytes(random.SystemRandom().getrandbits(44))
        key = b64encode(rand_bytes).decode()
    # What to append to the key to get a non-reproducable value.
    if not signing_key:
        signing_key = secret_api

    # Uses Blake2s for a small total size. Alternative is blake2b.
    hash_index = get_hash(key, signing_key)

    hashed_part = b64encode(hash_index.digest()).decode()

    return f"{hashed_part}!{key}"


# Validates an API key
def verify(secret, signing_key=None):
    if not signing_key:
        signing_key = secret_api

    hashed_part, key = secret.split("!")

    hash_index = get_hash(key, signing_key)

    control_hash = b64encode(hash_index.digest()).decode()

    if control_hash == hashed_part:
        return True
    return False


# Testing if it works
secret_key = generate()

if not verify(secret_key):
    logging.CRITICAL("Secret module not working")


if __name__ == "__main__":

    print(secret_key)
