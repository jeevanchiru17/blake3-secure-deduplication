import os
import time
import requests
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

API_URL = "http://127.0.0.1:8000"

def generate_keys():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    
    public_key_der = public_key.public_bytes(
        encoding=Encoding.DER,
        format=PublicFormat.SubjectPublicKeyInfo
    )
    public_key_b64 = base64.b64encode(public_key_der).decode()
    
    return private_key, public_key_b64

def sign_manifest(private_key, filename, file_size):
    manifest = f"{filename}:{file_size}".encode('utf-8')
    der_signature = private_key.sign(manifest, ec.ECDSA(hashes.SHA256()))
    
    r, s = decode_dss_signature(der_signature)
    raw_signature = r.to_bytes(32, 'big') + s.to_bytes(32, 'big')
    
    return base64.b64encode(raw_signature).decode()

def run_benchmark():
    os.makedirs("benchmarks/data", exist_ok=True)
    results = []
    
    print("Generating keys...")
    private_key, public_key_b64 = generate_keys()
    
    sizes_mb = [1, 5, 10]
    
    print("Starting benchmarks...\n")
    for size in sizes_mb:
        filename = f"bench_{size}MB.dat"
        filepath = f"benchmarks/data/{filename}"
        
        # Generate random file
        with open(filepath, "wb") as f:
            f.write(os.urandom(size * 1024 * 1024))
            
        file_size = os.path.getsize(filepath)
        
        # 1. Upload Unique File
        signature = sign_manifest(private_key, filename, file_size)
        
        with open(filepath, "rb") as f:
            files = {'file': (filename, f)}
            data = {
                'username': 'BenchmarkUser',
                'public_key': public_key_b64,
                'signature': signature
            }
            start_time = time.time()
            resp = requests.post(f"{API_URL}/upload", files=files, data=data)
            if resp.status_code != 200:
                print(f"Error uploading {filename}: {resp.text}")
                continue
            duration = time.time() - start_time
            
        throughput = size / duration
        res = resp.json()
        
        results.append({
            "File": filename,
            "Size (MB)": size,
            "Type": "Unique",
            "Time (s)": round(duration, 3),
            "Throughput (MB/s)": round(throughput, 2),
            "Savings (%)": res.get("storage_saved_percent", 0)
        })
        
        # 2. Upload Exact Duplicate
        dup_filename = f"dup_{filename}"
        signature_dup = sign_manifest(private_key, dup_filename, file_size)
        
        with open(filepath, "rb") as f:
            files = {'file': (dup_filename, f)}
            data = {
                'username': 'BenchmarkUser',
                'public_key': public_key_b64,
                'signature': signature_dup
            }
            start_time = time.time()
            resp = requests.post(f"{API_URL}/upload", files=files, data=data)
            duration = time.time() - start_time
            
        throughput = size / duration
        res = resp.json()
        
        results.append({
            "File": dup_filename,
            "Size (MB)": size,
            "Type": "100% Duplicate",
            "Time (s)": round(duration, 3),
            "Throughput (MB/s)": round(throughput, 2),
            "Savings (%)": res.get("storage_saved_percent", 0)
        })

    print("### Thesis Benchmark Results\n")
    print("| File | Size (MB) | Type | Time (s) | Throughput (MB/s) | Savings (%) |")
    print("|---|---|---|---|---|---|")
    for r in results:
        print(f"| {r['File']} | {r['Size (MB)']} | {r['Type']} | {r['Time (s)']} | {r['Throughput (MB/s)']} | {r['Savings (%)']} |")

if __name__ == "__main__":
    run_benchmark()
