from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import tempfile
import shutil
import os
from src.database.db_manager import DatabaseManager
from src.dedup.dedup_engine import DedupEngine
from src.crypto.ecdsa_signer import EcdsaSigner
from src.hashing.blake3_hasher import Blake3Hasher

app = FastAPI(title="Secure Deduplication System")

# Ensure directories exist
os.makedirs("data/uploads", exist_ok=True)
os.makedirs("data/storage", exist_ok=True)

db_manager = DatabaseManager("data/dedup.db")
dedup_engine = DedupEngine(db_manager, "data/storage")

# Make static directory if it doesn't exist so mounting doesn't fail
os.makedirs("src/api/static", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="src/api/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("src/api/static/index.html")

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    username: str = Form(...),
    public_key: str = Form(...),
    signature: str = Form(...)
):
    temp_path = os.path.join("data/uploads", file.filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Verify signature before processing (over manifest: filename:size)
    # The client signs the string "filename:size"
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    manifest = f"{file.filename}:{file_size}".encode('utf-8')
    is_valid = EcdsaSigner.verify_signature(public_key, signature, manifest)
    
    if not is_valid:
        os.remove(temp_path)
        raise HTTPException(status_code=401, detail="Invalid ECDSA signature")
        
    stats = dedup_engine.process_file(temp_path, file.filename)
    os.remove(temp_path) 
    
    # Link file to user
    user_id = db_manager.get_or_create_user(username, public_key)
    db_manager.link_user_file(user_id, stats["file_id"])
    
    return stats

@app.get("/system-stats")
def get_stats():
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_size), 0) FROM files")
        total_files, raw_total_size = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(size), 0) FROM chunks")
        total_unique_chunks, unique_storage_used = cursor.fetchone()
        
        bytes_saved = raw_total_size - unique_storage_used
        storage_saved_percent = (bytes_saved / raw_total_size * 100) if raw_total_size > 0 else 0
        
        return {
            "total_files": total_files,
            "raw_total_size": raw_total_size,
            "unique_chunks": total_unique_chunks,
            "unique_storage_used": unique_storage_used,
            "bytes_saved": bytes_saved,
            "storage_saved_percent": round(storage_saved_percent, 2)
        }

@app.get("/files")
def get_files(username: str):
    if not username:
        return []
    return db_manager.get_user_files(username)

@app.get("/download/{file_id}")
def download_file(file_id: int, username: str):
    if not db_manager.user_owns_file(username, file_id):
        raise HTTPException(status_code=403, detail="Unauthorized: User does not own this file")
    # Get filename
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="File not found")
        filename = row[0]

    # Reconstruct file
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, filename)
    
    success = dedup_engine.reconstruct_file(file_id, output_path)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reconstruct file")
        
    return FileResponse(output_path, filename=filename)
