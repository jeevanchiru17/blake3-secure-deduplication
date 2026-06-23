import os
from typing import Iterator

class Chunker:
    """Utility class for splitting files into chunks."""

    def __init__(self, chunk_size: int = 1024 * 1024):
        self.chunk_size = chunk_size

    def chunk_file(self, file_path: str) -> Iterator[bytes]:
        """
        Yields chunks of the file incrementally to avoid loading
        the entire file into memory.
        """
        with open(file_path, "rb") as f:
            while chunk := f.read(self.chunk_size):
                yield chunk
