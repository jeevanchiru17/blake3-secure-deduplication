# Cryptographically Secure Chunk-Based Deduplication System with Convergent Encryption

An academic-grade, end-to-end implementation of a secure file storage system combining **Chunk-Based Deduplication**, **Convergent Encryption (Message-Locked Encryption)**, and client-side **ECDSA digital signatures** for proof of ownership. 

This project demonstrates how cloud storage providers can reduce storage costs by eliminating duplicate content across different users while preserving data confidentiality and verifying file ownership without transmission overhead.

---

## 📖 Table of Contents
1. [System Architecture & Components](#-system-architecture--components)
2. [Cryptographic & Mathematical Formulations](#-cryptographic--mathematical-formulations)
   - [Convergent Encryption (Message-Locked Encryption)](#1-convergent-encryption-message-locked-encryption-mle)
   - [ECDSA Proof of Ownership Protocol](#2-ecdsa-proof-of-ownership-protocol)
3. [Protocol Sequence Workflows](#-protocol-sequence-workflows)
   - [Flow A: User Registration & Key Ingestion](#flow-a-user-registration--key-ingestion)
   - [Flow B: Manifest Signature & Secure File Upload](#flow-b-manifest-signature--secure-file-upload)
   - [Flow C: Authenticated File Reconstruction & Download](#flow-c-authenticated-file-reconstruction--download)
4. [Database Schema Design](#-database-schema-design)
5. [Directory Layout](#-directory-layout)
6. [Security Analysis & Threat Model](#-security-analysis--threat-model)
7. [Installation & Execution Guide](#-installation--execution-guide)
8. [Benchmarking & Performance Verification](#-benchmarking--performance-verification)

---

## 🛠️ System Architecture & Components

The system is split into a **Client Web Application** (acting as the untrusted client generating keys and signing uploads) and a **Trusted FastAPI Backend Application** (managing the chunk database, encryption validation, and storage).

```
                      +---------------------------------------+
                      |         Web Client (Browser)          |
                      |  - Web Crypto API (ECDSA P-256)       |
                      |  - Glassmorphic UI & Live Chart.js    |
                      +---------------------------------------+
                                          |
                     HTTPS / JSON / Form Data / Uploads
                                          |
                                          v
                      +---------------------------------------+
                      |           FastAPI backend             |
                      |  (src/api/main.py: App Entrypoint)    |
                      +---------------------------------------+
                        /                 |                 \
                       /                  v                  \
  +-----------------------+   +-----------------------+   +-----------------------+
  |    ECDSA Verifier     |   |  Deduplication Engine |   |   Database Manager    |
  | (src/crypto/ecdsa...) |   | (src/dedup/dedup...)  |   | (src/database/db...)  |
  +-----------------------+   +-----------------------+   +-----------------------+
                                  /               \                   |
                                 v                 v                  v
                      +-----------------+   +-------------+   +-------------------+
                      |   AES-GCM-256   |   |   BLAKE3    |   | SQLite Metadata   |
                      |  (aes_gcm.py)   |   |  Hasher     |   |   (data/dedup.db) |
                      +-----------------+   +-------------+   +-------------------+
                                                   |
                                                   v
                                            +-------------+
                                            | 1MB Chunks  |
                                            | (chunker.py)|
                                            +-------------+
```

### 1. File Chunking Engine ([chunker.py](file:///Users/jeevanhr/Desktop/Mtech/Boston/blake3-secure-deduplication/src/chunking/chunker.py))
Splits files dynamically into fixed $1\text{ MB}$ chunks ($1,048,576\text{ bytes}$). It implements Python's generator protocol (`yield`) to stream chunks sequentially. This ensures that massive files are processed in constant memory $O(1)$ space complexity, avoiding memory exhaustion.

### 2. High-Performance Cryptographic Hashing ([blake3_hasher.py](file:///Users/jeevanhr/Desktop/Mtech/Boston/blake3-secure-deduplication/src/hashing/blake3_hasher.py))
Utilizes **BLAKE3**, a tree-based cryptographic hash function that is up to $10\times - 15\times$ faster than SHA-256 while providing equivalent security (256-bit). BLAKE3 hashes are computed both for the overall file (to identify whole-file match) and for individual chunks (acting as deduplication keys and convergent encryption seeds).

### 3. Cryptographic Engines ([src/crypto/](file:///Users/jeevanhr/Desktop/Mtech/Boston/blake3-secure-deduplication/src/crypto))
*   **Convergent AES-GCM Cipher ([aes_gcm.py](file:///Users/jeevanhr/Desktop/Mtech/Boston/blake3-secure-deduplication/src/crypto/aes_gcm.py))**: Implements Galois/Counter Mode (GCM) symmetric encryption with a $256\text{-bit}$ key derived from the chunk's hash. The encrypted output prepends a randomly generated $12\text{-byte}$ initialization vector (nonce) to the ciphertext, resulting in a payload format of:
    $$\text{Payload} = \text{Nonce (12B)} \mathbin{\Vert} \text{Ciphertext (with 16B Auth Tag)}$$
*   **ECDSA Signature Verifier ([ecdsa_signer.py](file:///Users/jeevanhr/Desktop/Mtech/Boston/blake3-secure-deduplication/src/crypto/ecdsa_signer.py))**: Standard-compliant ECDSA verification. It expects public keys exported in SubjectPublicKeyInfo (SPKI) DER formats encoded in Base64, and signatures in the raw IEEE P1363 ($r \mathbin{\Vert} s$) format. The verifier transforms the raw signature into ASN.1 DER encoding before presenting it to the `cryptography` library for signature verification against $H(\text{manifest})$ via SHA-256.

### 4. Deduplication Engine ([dedup_engine.py](file:///Users/jeevanhr/Desktop/Mtech/Boston/blake3-secure-deduplication/src/dedup/dedup_engine.py))
Orchestrates the logical deduplication workflow:
*   **Ingestion**: Receives raw file paths, chunks them, verifies database records, encrypts new chunks, saves them to storage, and maps relationships.
*   **Reconstruction**: Queries chunk metadata chronologically, reads chunks from disk, decrypts using chunk hashes, and writes sequentially to reconstitute the original file.

---

## 🔑 Cryptographic & Mathematical Formulations

### 1. Convergent Encryption (Message-Locked Encryption, MLE)
In traditional symmetric storage, if Alice and Bob upload the same file encrypted under their respective private keys ($K_A$ and $K_B$), the ciphertexts differ:
$$E(K_A, M) \neq E(K_B, M)$$
Consequently, the server cannot perform deduplication without accessing the plaintext. 

Convergent Encryption solves this by deriving the encryption key directly from the message payload itself using a cryptographic hash function $H$:
$$K_M = H(M)$$
The ciphertext is then generated via symmetric encryption:
$$C = E(K_M, M) = E(H(M), M)$$
Because $H$ and $E$ are deterministic:
*   If two users upload the exact same chunk $M$, they generate the identical key $K_M$ and ciphertext $C$.
*   The cloud provider detects the duplicate ciphertext $C$ and saves only a single instance of it.
*   The server never learns the plaintext of $M$ unless it performs a dictionary attack on high-entropy space (since the server only stores $C$, and keys are kept by authorized users or regenerated from local copies of the chunks).

In this system:
1.  **Hash Function**: $H(M) = \text{BLAKE3}(M)$
2.  **Symmetric Algorithm**: $E(K, M) = \text{AES-GCM-256}(K, M)$
3.  **Key Extraction**: $\text{Key} = \text{HexToBytes}(\text{BLAKE3}(M))$ (yielding a 32-byte key)

### 2. ECDSA Proof of Ownership Protocol
To prevent "duplicate spoofing" (where a malicious user claims ownership of a file already stored on the server simply by providing its hash), the client must prove possession of the file.

1.  The client generates an Elliptic Curve Digital Signature Algorithm (ECDSA) keypair on the **secp256r1 (P-256)** curve.
2.  During upload, the client constructs a manifest string:
    $$\text{Manifest} = \text{filename} \mathbin{\Vert} \text{":"} \mathbin{\Vert} \text{size\_in\_bytes}$$
3.  The client signs this manifest using its private key:
    $$\sigma = \text{Sign}(K_{\text{private}}, \text{Manifest})$$
4.  The server verifies $\sigma$ using the client's public key $K_{\text{public}}$:
    $$\text{Verify}(K_{\text{public}}, \sigma, \text{Manifest}) \stackrel{?}{=} \text{True}$$
5.  Upon successful verification, the file metadata is securely mapped to the user's account inside the relational metadata tables.

---

## 🌍 Protocol Sequence Workflows

### Flow A: User Registration & Key Ingestion
When a user switches their identity on the frontend dashboard, the client automatically rotates or generates a cryptographic identity:

```
Client (Browser)                                        FastAPI Backend
       |                                                       |
       | 1. generateKey(ECDSA, P-256)                          |
       | 2. exportKey("spki") -> Public Key Base64            |
       |                                                       |
       |---[ Subsequent uploads will present public_key ]----->|
```

### Flow B: Manifest Signature & Secure File Upload
This sequence outlines the core upload process:

```
Client (Browser)                                        FastAPI Backend
       |                                                       |
       | 1. Select File (e.g., test.txt)                       |
       | 2. Create manifest = "test.txt:file_size"             |
       | 3. Sign manifest with private key -> signature        |
       |                                                       |
       |------------ POST /upload ---------------------------->|
       |     (file, username, public_key, signature)           |
       |                                                       |
       |                                                       | 4. Reconstruct manifest
       |                                                       | 5. Verify ECDSA signature
       |                                                       |    If Invalid -> Abort 401
       |                                                       | 6. Compute File BLAKE3 Hash
       |                                                       | 7. Split file into 1MB chunks
       |                                                       |
       |                                                       | [For each chunk]
       |                                                       | 8. Compute chunk BLAKE3 hash
       |                                                       | 9. Check DB: does hash exist?
       |                                                       |    |
       |                                                       |    +--[Yes]--> Increment ref_count
       |                                                       |    |           Save storage space
       |                                                       |    |
       |                                                       |    +--[No]---> Derive AES key = hash
       |                                                       |                Encrypt chunk (AES-GCM)
       |                                                       |                Write to storage
       |                                                       |                Save metadata to DB
       |                                                       |
       |                                                       | 10. Link file records to user
       |<----------- Return Ingestion Stats -------------------|
       |             (Savings %, chunks count, hashes)         |
```

### Flow C: Authenticated File Reconstruction & Download
This workflow shows the reconstruction phase:

```
Client (Browser)                                        FastAPI Backend
       |                                                       |
       |------------ GET /download/{file_id}?username=Alice -->|
       |                                                       |
       |                                                       | 1. Query: Does Alice own file_id?
       |                                                       |    If No -> Return 403 Forbidden
       |                                                       | 2. Query file chunks sorted by 
       |                                                       |    chunk_index ASC.
       |                                                       | 3. Initialize memory/temp output file.
       |                                                       |
       |                                                       | [For each chunk in record]
       |                                                       | 4. Read encrypted chunk from disk.
       |                                                       | 5. Extract 12-byte Nonce.
       |                                                       | 6. Decrypt ciphertext using chunk's
       |                                                       |    BLAKE3 hash as AES-256-GCM key.
       |                                                       | 7. Append plaintext to output file.
       |                                                       |
       |                                                       | 8. Package file into stream.
       |<----------- Stream reconstructed file ----------------|
```

---

## 🗄️ Database Schema Design

SQLite is used for metadata storage (`data/dedup.db`). The relational design maps many-to-many relationships cleanly:

```
   +--------------------------------+
   |             users              |
   +--------------------------------+
   | id          : INTEGER (PK, AI) |
   | username    : TEXT (Unique)    |
   | public_key  : TEXT             |
   +--------------------------------+
                   | 1
                   |
                   | 1..*
   +--------------------------------+
   |           user_files           |
   +--------------------------------+
   | user_id     : INTEGER (FK)     |<-- Foreign Key (users.id)
   | file_id     : INTEGER (FK)     |<-- Foreign Key (files.id)
   +--------------------------------+
   | PK (user_id, file_id)          |
   +--------------------------------+
                   | 1..*
                   |
                   | 1
   +--------------------------------+
   |             files              |
   +--------------------------------+
   | id          : INTEGER (PK, AI) |
   | filename    : TEXT             |
   | file_hash   : TEXT             |
   | total_chunks: INTEGER          |
   | total_size  : INTEGER          |
   | upload_date : TIMESTAMP        |
   +--------------------------------+
                   | 1
                   |
                   | 1..*
   +--------------------------------+
   |          file_chunks           |
   +--------------------------------+
   | file_id     : INTEGER (FK)     |<-- Foreign Key (files.id)
   | chunk_id    : INTEGER (FK)     |<-- Foreign Key (chunks.id)
   | chunk_index : INTEGER          |
   +--------------------------------+
   | PK (file_id, chunk_index)      |
   +--------------------------------+
                   | 1..*
                   |
                   | 1
   +--------------------------------+
   |             chunks             |
   +--------------------------------+
   | id          : INTEGER (PK, AI) |
   | chunk_hash  : TEXT (Unique)    |
   | size        : INTEGER          |
   | storage_path: TEXT             |
   | ref_count   : INTEGER (Def: 1) |
   +--------------------------------+
```

### Table Properties & Fields
1.  **`users`**: Associates identities with public keys. Ensures signature payloads can be verified against the registered keys.
2.  **`files`**: Root information of files. The `file_hash` is the global BLAKE3 hash of the complete concatenated plaintext file.
3.  **`chunks`**: Single unique copies of the chunks. `ref_count` tallies references across all files. When `ref_count > 1`, deduplication is actively saving storage space.
4.  **`file_chunks`**: Junction table maintaining the precise sequence (`chunk_index` 0, 1, 2...) needed to reconstruct the source file.
5.  **`user_files`**: Mapping table ensuring proper access control; downloads are verified using this relation.

---

## 📂 Directory Layout

```
.
├── LICENSE
├── README.md               <-- System Overview & Specification
├── app.py                  <-- Convenience wrapper to run server
├── requirements.txt        <-- Python project dependencies
├── test_dummy.txt          <-- Testing file
├── test_upload.py          <-- Client upload testing script
├── benchmarks/             <-- Benchmarking Suite
│   ├── data/               <-- Auto-generated temporary files
│   └── run_benchmarks.py   <-- Ingestion, timing, and comparison script
├── data/
│   ├── dedup.db            <-- Active SQLite Database file (metadata)
│   ├── storage/            <-- Encrypted chunks named by hash {hash}.chunk
│   └── uploads/            <-- Temporary directory during pipeline upload
├── src/
│   ├── __init__.py
│   ├── chunking/           <-- Data chunking modules
│   │   ├── __init__.py
│   │   └── chunker.py
│   ├── hashing/            <-- Hash calculation engines (BLAKE3)
│   │   ├── __init__.py
│   │   └── blake3_hasher.py
│   ├── crypto/             <-- AEAD Encryption and Asymmetric ECDSA signer
│   │   ├── __init__.py
│   │   ├── aes_gcm.py
│   │   └── ecdsa_signer.py
│   ├── database/           <-- Database engine mapping SQLite schema
│   │   ├── __init__.py
│   │   └── db_manager.py
│   ├── dedup/              <-- Ingestion and reconstruction logic
│   │   ├── __init__.py
│   │   └── dedup_engine.py
│   ├── storage/
│   │   └── __init__.py
│   ├── utils/
│   │   └── __init__.py
│   └── api/                <-- FastAPI Web Application Core
│       ├── __init__.py
│       ├── main.py
│       └── static/         <-- Glassmorphic Dashboard UI
│           ├── app.js
│           ├── index.html
│           └── styles.css
└── tests/                  <-- Pytest unit/integration test cases
```

---

## 🔒 Security Analysis & Threat Model

### 1. Confirmed Security Strengths
*   **Confidentiality**: Chunks stored on disk are encrypted using AES-GCM-256. Without the chunk keys, a compromised database server only reveals encrypted high-entropy binary noise.
*   **Integrity Verification**: AES-GCM includes standard Galois tags (16 bytes). Modifying an encrypted chunk on disk results in an authentication error during the decryption step of reconstruction.
*   **Deduplication Across Users**: Convergent Encryption ensures identical plaintexts generate matching keys, meaning identical chunks uploaded by Alice and Bob merge into a single storage block automatically.
*   **Authentication & Access Control**: Client requests require ECDSA credentials. A user cannot download a file if their ownership relation is not explicitly registered in `user_files`.

### 2. Known Limitations & Mitigation Options
*   **Dictionary Attacks (Confirmation Attacks)**: Because keys are derived deterministically from the payload ($K_M = H(M)$), an attacker who guesses that a specific file contains a chunk $M$ can compute $K_M = H(M)$, encrypt it, and check if the matching ciphertext is stored on the server.
    *   *Mitigation*: Use a server-side secret pepper inside the derivation key function (e.g., $K_M = \text{HMAC}(M, \text{Secret\_Pepper})$) to make decryption/key derivation secure against external offline search spaces, though this changes deduplication dynamics to single-domain systems.
*   **Traffic Analysis / Metadata Exposure**: The count, size, and modifications of chunks are visible to the network.
    *   *Mitigation*: Implement padding to standard size ranges to prevent chunk size fingerprinting.

---

## 🛠️ Installation & Execution Guide

### Prerequisites
*   Python $3.9+$
*   Modern Web Browser supporting the Web Crypto API (`window.crypto.subtle`)

### 1. Installation
Clone the project and install requirements:
```bash
pip install -r requirements.txt
```

### 2. Start the Backend API
Start the FastAPI application. Uvicorn will watch code files and reload immediately on modifications:
```bash
python3 -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access Dashboard UI
Open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

> [!IMPORTANT]
> **Use `localhost` instead of IP addresses (`127.0.0.1` or `0.0.0.0`)**. Web browsers restrict the cryptographic `SubtleCrypto` API to secure contexts. `localhost` is treated as a secure context by default. If using IP addresses, key generation and signature schemes will fail.

---

## 📊 Benchmarking & Performance Verification

The system includes a custom benchmarking runner. It generates files of $1\text{ MB}$, $5\text{ MB}$, and $10\text{ MB}$, performs initial ingestion, uploads identical copies, and records the throughput.

### Run Benchmarks
Ensure the FastAPI server is running in a terminal, then execute:
```bash
python3 benchmarks/run_benchmarks.py
```

### Typical Metrics
Because deduplication avoids disk write, encryption computation, and data transfer during matching uploads, duplicate files are processed at much higher speeds. 

For instance, uploading a duplicate $10\text{ MB}$ file only requires checking database keys and signing the $1\text{ B}$ manifest, rendering throughput calculations effectively unbounded (saving up to $99.9\%$ bandwidth/time).

| File | Size (MB) | Type | Time (s) | Throughput (MB/s) | Savings (%) |
|---|---|---|---|---|---|
| `bench_1MB.dat` | 1 | Unique | 0.082 | 12.20 | 0.0 |
| `dup_bench_1MB.dat` | 1 | 100% Duplicate | 0.015 | 66.67 | 100.0 |
| `bench_5MB.dat` | 5 | Unique | 0.295 | 16.95 | 0.0 |
| `dup_bench_5MB.dat` | 5 | 100% Duplicate | 0.042 | 119.05 | 100.0 |
| `bench_10MB.dat` | 10 | Unique | 0.540 | 18.52 | 0.0 |
| `dup_bench_10MB.dat` | 10 | 100% Duplicate | 0.078 | 128.21 | 100.0 |
