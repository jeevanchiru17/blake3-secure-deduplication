import os
from src.chunking.chunker import Chunker
from src.database.db_manager import DatabaseManager
from src.hashing.blake3_hasher import Blake3Hasher
from src.crypto.aes_gcm import AesGcmCipher
class DedupEngine:
    def __init__(self, db_manager: DatabaseManager, storage_dir: str = "data/storage"):
        self.db_manager = db_manager
        self.storage_dir = storage_dir
        self.chunker = Chunker()
        os.makedirs(self.storage_dir, exist_ok=True)

    def process_file(self, file_path: str, filename: str) -> dict:
        """
        Processes a file: chunks it, hashes chunks, deduplicates, and saves.
        Returns statistics about the process.
        """
        # Step 1: Overall file hash
        file_hash = Blake3Hasher.hash_file(file_path)
        
        # We need total file size for stats
        total_size = os.path.getsize(file_path)
        
        stats = {
            "filename": filename,
            "total_size": total_size,
            "chunks_processed": 0,
            "duplicate_chunks": 0,
            "bytes_saved": 0,
            "file_hash": file_hash
        }

        # Step 2: Add file to database (we will update total_chunks later if needed, 
        # or we can count chunks on the fly and update)
        # Actually let's chunk it first, keeping track of chunks.
        chunks_info = []
        for index, chunk_data in enumerate(self.chunker.chunk_file(file_path)):
            stats["chunks_processed"] += 1
            chunk_hash = Blake3Hasher.hash_bytes(chunk_data)
            
            chunk_db_info = self.db_manager.chunk_exists(chunk_hash)
            
            if chunk_db_info:
                # Duplicate found
                self.db_manager.increment_chunk_ref(chunk_hash)
                stats["duplicate_chunks"] += 1
                stats["bytes_saved"] += len(chunk_data)
                chunks_info.append(chunk_db_info["id"])
            else:
                # New chunk
                chunk_filename = f"{chunk_hash}.chunk"
                chunk_storage_path = os.path.join(self.storage_dir, chunk_filename)
                
                # Encrypt chunk using its hash as the key
                aes_key = bytes.fromhex(chunk_hash)
                encrypted_chunk = AesGcmCipher.encrypt(chunk_data, aes_key)
                
                # Save encrypted chunk to disk
                with open(chunk_storage_path, "wb") as f:
                    f.write(encrypted_chunk)
                
                # Add to DB
                chunk_id = self.db_manager.add_chunk(chunk_hash, len(chunk_data), chunk_storage_path)
                chunks_info.append(chunk_id)
                
        # Step 3: Save file metadata and mapping
        file_id = self.db_manager.add_file(filename, file_hash, stats["chunks_processed"], total_size)
        
        for idx, chunk_id in enumerate(chunks_info):
            self.db_manager.link_file_chunk(file_id, chunk_id, idx)
            
        stats["storage_saved_percent"] = (stats["bytes_saved"] / total_size * 100) if total_size > 0 else 0
        stats["file_id"] = file_id
        
        return stats

    def reconstruct_file(self, file_id: int, output_path: str) -> bool:
        """
        Reconstructs a file from its encrypted chunks.
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.chunk_hash, c.storage_path 
                FROM file_chunks fc
                JOIN chunks c ON fc.chunk_id = c.id
                WHERE fc.file_id = ?
                ORDER BY fc.chunk_index ASC
            ''', (file_id,))
            rows = cursor.fetchall()

        if not rows:
            return False
            
        with open(output_path, "wb") as out_f:
            for chunk_hash, storage_path in rows:
                with open(storage_path, "rb") as in_f:
                    encrypted_data = in_f.read()
                
                aes_key = bytes.fromhex(chunk_hash)
                plaintext = AesGcmCipher.decrypt(encrypted_data, aes_key)
                out_f.write(plaintext)
                
        return True
