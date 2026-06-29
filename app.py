import uvicorn

if __name__ == "__main__":
    print("\n==========================================================")
    print(" Starting Secure Deduplication Server")
    print(" Access Dashboard UI at: 👉 http://localhost:8000/")
    print("==========================================================\n")
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)

