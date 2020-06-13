from hashlib import sha256

from hubitatmaker import Hub

_token_hashes = {}


def get_token_hash(token: str) -> str:
    if token not in _token_hashes:
        hasher = sha256()
        hasher.update(token.encode("utf-8"))
        _token_hashes[token] = hasher.hexdigest()
    return _token_hashes[token]


def get_hub_short_id(hub: Hub) -> str:
    return hub.token[:8]
