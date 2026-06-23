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
