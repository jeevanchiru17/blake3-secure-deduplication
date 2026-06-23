from src.hashing.blake3_hasher import Blake3Hasher


def test_hash_bytes():
    data = b"Hello World"

    h1 = Blake3Hasher.hash_bytes(data)
    h2 = Blake3Hasher.hash_bytes(data)

    assert h1 == h2