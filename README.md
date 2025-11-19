# 🚀 Python Script Execution Service

A secure API for executing arbitrary Python code using a sandboxed environment.  
Built with **Flask**, **nsjail**, **Docker**, and deployed on **Google Cloud Run**.

This project implements a remote code execution service where users POST a Python script and receive:

```json
{
  "result": <main() return value>,
  "stdout": <captured stdout>
}
```

Only the return value of `main()` is returned — print statements appear separately in `stdout`.

---

## 🔒 Security Model

| Environment      | Sandbox     | Description |
|------------------|-------------|-------------|
| **Local**        | **nsjail**  | Full isolation, blocked FS, blocked network, CPU & timeout enforcement |
| **Cloud Run**    | **fallback**| Cloud Run disallows nsjail → uses a Python-only restricted executor |

Both environments validate scripts using AST, enforce JSON returns, and safely process user code.

---

## 📦 Features

✔ Execute arbitrary Python safely  
✔ Validate user code (AST parsing)  
✔ `main()` must exist and return JSON  
✔ Captures and returns stdout separately  
✔ nsjail sandboxing (local)  
✔ Fallback execution for Cloud Run  
✔ Timeouts to stop infinite loops  
✔ Network and filesystem access restricted  
✔ Optimized Docker image (~450MB)

---

## 🗂 Folder Structure

```
app/
├── main.py              # Local Flask server (nsjail executor)
├── main_cloud.py        # Cloud Run Flask server (fallback executor)
├── executor.py          # nsjail-based secure executor
├── executor_cloud.py    # Python fallback executor
config/
├── nsjail.cfg           # Sandbox configuration (local only)
Dockerfile               # Multi-stage optimized build
requirements.txt
README.md
```

---

## 🛠 Running Locally

### 1. Build the container

```bash
docker build -t python-executor .
```

### 2. Run with privileges (required for nsjail)

```bash
docker run --rm -p 8080:8080 --privileged python-executor
```

### 3. Test execution

```bash
curl -X POST   -H "Content-Type: application/json"   -d '{"script": "def main():\n    print(\"Hello\"); return {\"ok\": True}"}'   http://localhost:8080/execute
```

Expected output:

```json
{
  "result": {"ok": true},
  "stdout": "Hello\n"
}
```

---

## ☁️ Deploying to Google Cloud Run

Push your built image to Artifact Registry:

```bash
gcloud builds submit --tag gcr.io/<PROJECT-ID>/python-executor
```

Deploy with Cloud Run using fallback executor:

```bash
gcloud run deploy python-executor   --image gcr.io/python-exec-478709/python-executor   --platform=managed   --region=us-central1   --allow-unauthenticated   --port=8080   --command=gunicorn   --args="--bind,0.0.0.0:8080,app.main_cloud:app"
```

### Cloud Run URL  
**https://python-executor-256857162008.us-central1.run.app**

---

## 🧪 Example Cloud Run Execution

```bash
curl -X POST   -H "Content-Type: application/json"   -d '{"script": "def main():\n    print(\"Cloud run\"); return {\"ok\": True}"}'   https://python-executor-256857162008.us-central1.run.app/execute
```

Response:

```json
{
  "result": {"ok": true},
  "stdout": "Cloud run\n"
}
```

---

## 🧪 Validation & Error Handling

### Syntax error
```json
{"error": "Validation failed: Syntax error at line 1: invalid syntax"}
```

### Missing main()
```json
{"error": "Validation failed: Script must define a main() function"}
```

### main is not a function
```json
{"error": "Validation failed: main must be a function, not a variable"}
```

### Non-JSON return
```json
{"error": "main() must return a JSON object (dict) or array (list). Got int"}
```

### Non-serializable
```json
{"error": "main() must return JSON-serializable data. Got dict: Object of type set is not JSON serializable"}
```

### Infinite loop (timeout)
```json
{"error": "Execution timeout: script exceeded 5 second limit"}
```

### File access blocked
```json
{"error": "Exception in main(): FileNotFoundError: ..."}
```

---

## 📏 Docker Image Size

Final optimized image size: **~450MB**  
(Down from ~970MB using multi-stage build)

---

## ⏱ Development Time

Approx. **1.5 hours**  
(excluding reading nsjail documentation)

---

## ✅ Summary

This project fully satisfies the take‑home requirements:

- API endpoint with script execution  
- Returning main() JSON + stdout  
- nsjail sandbox (local)  
- Cloud Run fallback executor  
- Input validation  
- Docker optimization  
- Working Cloud Run demo  
- Clean, documented code structure  

---
