from pathlib import Path
from blake3 import blake3


class Blake3Hasher:
    """Utility class for generating BLAKE3 hashes."""

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        return blake3(data).hexdigest()

    @staticmethod
    def hash_file(file_path: str, chunk_size: int = 1024 * 1024) -> str:
        hasher = blake3()

        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)

        return hasher.hexdigest()