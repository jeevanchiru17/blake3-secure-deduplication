# Secure Chunk-Based Deduplication System with Convergent Encryption

This project implements a secure, chunk-based file deduplication system featuring **BLAKE3 hashing**, **AES-GCM convergent encryption**, and client-side **ECDSA signatures** for ownership proof. It includes a FastAPI backend, a dynamic glassmorphic web dashboard with real-time statistics, and a benchmarking suite.

---

## 📋 Command Sheet: How to Run the Project

### 1. Installation

First, install the required dependencies:
```bash
pip install -r requirements.txt
```

### 2. Start the Backend Server

Start the FastAPI application. Uvicorn will automatically watch for changes and reload the server:
```bash
python3 -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Open the Web Dashboard

Open your web browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

> [!IMPORTANT]
> Make sure to use `localhost:8000` instead of `0.0.0.0:8000` or `127.0.0.1:8000`. Browsers disable the native Web Crypto APIs (`window.crypto.subtle`) on insecure contexts. Localhost is automatically trusted as a secure context.

### 4. Run the Benchmarks (Thesis Results)

To generate throughput, performance, and deduplication statistics for your thesis paper, run the benchmarking script:
```bash
python3 benchmarks/run_benchmarks.py
```
This will automatically generate unique and duplicate files of varying sizes (1MB, 5MB, 10MB) and print a neatly formatted Markdown table of the results.

---

## 🛠️ Project Architecture & Components

1. **`src/chunking/`**: Handles file chunking dynamically (splits files into fixed 1MB chunks).
2. **`src/hashing/`**: Uses `BLAKE3` for hashing chunks rapidly.
3. **`src/crypto/`**:
   - **`aes_gcm.py`**: Derived keys from the chunk's BLAKE3 hash are used to encrypt chunks under AES-GCM-256 (Convergent Encryption).
   - **`ecdsa_signer.py`**: Verifies ECDSA signatures sent by the client.
4. **`src/database/`**: Manages the SQLite database metadata (`files`, `chunks`, `file_chunks`, `users`, `user_files`).
5. **`src/api/`**: Contains the FastAPI server (`main.py`) and static web dashboard assets (`index.html`, `app.js`, `styles.css`).

---

## 🌍 Real-World Use Cases

This project combines chunk-based deduplication, AES-GCM convergent encryption, BLAKE3 hashing, and ECDSA ownership proofs to address several high-value scenarios:

1. **Secure Cloud Storage (Dropbox/Google Drive Style)**: Identifies and deduplicates duplicate chunks across users. Convergent encryption ensures chunks are encrypted yet deduplicated (same plaintext produces the same ciphertext key). ECDSA signatures prove ownership without re-uploading.
2. **Healthcare/Medical Imaging Archives (DICOM Files)**: Patient records and scans share similar regions. Deduplication cuts storage costs while AES-GCM ensures HIPAA-level confidentiality, and ECDSA provides audit trails.
3. **Incremental Backup Systems (Veeam/Restic Style)**: Backups share substantial data day-to-day. BLAKE3 fingerprinting identifies changed chunks rapidly, minimizing required storage.
4. **Video/Media CDN & Streaming Platforms**: Transcoding pipelines produce similar video chunks at different quality tiers. Deduplication saves storage and CDN bandwidth.
5. **Enterprise File Sync & Share (EMC/SharePoint)**: Collapses redundant files/folders across departmental shares. ECDSA proof-of-ownership allows multiple users access to the same chunks safely.

### Technical Advantages
- **BLAKE3 Hashing**: Fast cryptographic hashing (10–15x faster than SHA-256).
- **Convergent Encryption**: Deduplication across users while preserving data privacy.
- **ECDSA Ownership Proof**: Quick verification of file ownership without transmitting the file again.

