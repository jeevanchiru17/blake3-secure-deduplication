import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path: str = "data/dedup.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Files table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    total_chunks INTEGER NOT NULL,
                    total_size INTEGER NOT NULL,
                    upload_date TIMESTAMP NOT NULL
                )
            ''')
            
            # Chunks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_hash TEXT UNIQUE NOT NULL,
                    size INTEGER NOT NULL,
                    storage_path TEXT NOT NULL,
                    ref_count INTEGER DEFAULT 1
                )
            ''')
            
            # File-Chunks mapping table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_chunks (
                    file_id INTEGER NOT NULL,
                    chunk_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    FOREIGN KEY (file_id) REFERENCES files (id),
                    FOREIGN KEY (chunk_id) REFERENCES chunks (id),
                    PRIMARY KEY (file_id, chunk_index)
                )
            ''')
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    public_key TEXT NOT NULL
                )
            ''')
            
            # User-Files table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_files (
                    user_id INTEGER NOT NULL,
                    file_id INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (file_id) REFERENCES files (id),
                    PRIMARY KEY (user_id, file_id)
                )
            ''')
            
            conn.commit()

    def chunk_exists(self, chunk_hash: str) -> dict:
        """Returns chunk info if it exists, otherwise None."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, storage_path, ref_count FROM chunks WHERE chunk_hash = ?", (chunk_hash,))
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "storage_path": row[1], "ref_count": row[2]}
            return None

    def add_chunk(self, chunk_hash: str, size: int, storage_path: str) -> int:
        """Adds a new chunk and returns its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chunks (chunk_hash, size, storage_path, ref_count)
                VALUES (?, ?, ?, 1)
            ''', (chunk_hash, size, storage_path))
            conn.commit()
            return cursor.lastrowid

    def increment_chunk_ref(self, chunk_hash: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE chunks SET ref_count = ref_count + 1 WHERE chunk_hash = ?", (chunk_hash,))
            conn.commit()

    def add_file(self, filename: str, file_hash: str, total_chunks: int, total_size: int) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO files (filename, file_hash, total_chunks, total_size, upload_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (filename, file_hash, total_chunks, total_size, datetime.now()))
            conn.commit()
            return cursor.lastrowid

    def link_file_chunk(self, file_id: int, chunk_id: int, chunk_index: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO file_chunks (file_id, chunk_id, chunk_index)
                VALUES (?, ?, ?)
            ''', (file_id, chunk_id, chunk_index))
            conn.commit()

    def get_or_create_user(self, username: str, public_key: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, public_key FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                if row[1] != public_key:
                    cursor.execute("UPDATE users SET public_key = ? WHERE id = ?", (public_key, row[0]))
                    conn.commit()
                return row[0]
            
            cursor.execute("INSERT INTO users (username, public_key) VALUES (?, ?)", (username, public_key))
            conn.commit()
            return cursor.lastrowid

    def link_user_file(self, user_id: int, file_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO user_files (user_id, file_id) VALUES (?, ?)", (user_id, file_id))
            conn.commit()
            
    def get_user_files(self, username: str) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT f.id, f.filename, f.total_size, f.upload_date 
                FROM files f
                JOIN user_files uf ON f.id = uf.file_id
                JOIN users u ON uf.user_id = u.id
                WHERE u.username = ?
                ORDER BY f.id DESC
            ''', (username,))
            rows = cursor.fetchall()
            files = []
            for row in rows:
                files.append({
                    "id": row[0],
                    "filename": row[1],
                    "total_size": row[2],
                    "upload_date": row[3]
                })
            return files

    def get_user_public_key(self, username: str) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT public_key FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return row[0] if row else None
            
    def user_owns_file(self, username: str, file_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM user_files uf
                JOIN users u ON uf.user_id = u.id
                WHERE u.username = ? AND uf.file_id = ?
            ''', (username, file_id))
            return cursor.fetchone() is not None
