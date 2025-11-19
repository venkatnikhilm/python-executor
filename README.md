# Python Script Execution Service

A secure API for executing arbitrary Python code inside a controlled sandbox.  
Built with **Flask**, **nsjail**, **Docker**, and deployed on **Google Cloud Run**.

---

## 🚀 Overview

This service exposes a `/execute` endpoint that accepts a Python script, validates it, securely executes it, and returns:

```json
{
  "result": <main() return value>,
  "stdout": "<captured stdout>"
}
```

Scripts **must define**:

```python
def main():
    ...
    return {...}   # Must be JSON-serializable
```

---

## 🔒 Security Model

| Environment | Sandbox | Description |
|------------|----------|-------------|
| **Local** | nsjail | Full OS-level sandbox: filesystem blocked, network blocked, time-limited, CPU restricted, isolated namespaces |
| **Cloud Run** | Python fallback executor | Cloud Run prohibits privileged operations required for nsjail → safe AST validation + restricted Python exec |

Both environments enforce:

- AST-based validation  
- No arbitrary imports beyond Python stdlib  
- JSON-only return values  
- Captured stdout  
- 5s execution timeout  
- No network access  
- No file access outside ephemeral `/tmp`

---

## ⚠️ Why nsjail Cannot Run on Cloud Run

Google Cloud Run containers run as a **non-root**, **unprivileged**, **non-namespaced** execution environment.

nsjail requires:

- `--privileged` or `CAP_SYS_ADMIN`
- Mounting `/proc`, `/dev`, tmpfs, bind-mounts
- Cloning new namespaces (PID, NET, NS, IPC)
- Writing cgroups

Cloud Run **blocks all of these** → nsjail instantly fails with errors like:

```
Couldn't mount '/proc'
prctl(PR_SET_SECUREBITS) failed
clone_newuser not permitted
Operation not permitted
```

Therefore the service automatically falls back to:

### ✔ A restricted Python-level executor (`executor_cloud.py`)  
which still enforces:

- AST linting  
- No builtins modification  
- No filesystem or network  
- Timeouts  
- JSON serialization rules  

---

## 📦 Features

- Execute arbitrary Python safely  
- Validate user code via AST  
- `main()` function required  
- Captures `stdout` separately  
- JSON-only return values  
- Blocks file system access  
- Blocks external HTTP/network requests  
- Execution timeout (5 seconds)  
- Docker multi-stage image (~450MB → optimized)  
- Fully working Cloud Run deployment  

---

## 🗂 Folder Structure

```
app/
├── main.py              # Local Flask server using nsjail
├── main_cloud.py        # Cloud Run Flask server (fallback executor)
├── executor.py          # Local nsjail sandbox executor
├── executor_cloud.py    # Safe Python fallback executor
config/
├── nsjail.cfg           # nsjail configuration (LOCAL ONLY)
Dockerfile               # Multi‑stage optimized build
requirements.txt
README.md
```

---

## 🛠 Running Locally (nsjail enabled)

### 1️⃣ Build the container

```bash
docker build -t python-executor .
```

### 2️⃣ Run **with privileged mode**  
(required for nsjail)

```bash
docker run --rm -p 8080:8080 --privileged python-executor
```

### 3️⃣ Test

```bash
curl -X POST   -H "Content-Type: application/json"   -d '{"script": "def main(): print("Hello"); return {"ok": True}"}'   http://localhost:8080/execute
```

## 🛠️ Local Setup (Auto Script)

To simplify local development, the project includes a **helper script** that automatically builds the **Docker image**, ensures no conflicting container is running, and starts the sandboxed executor with `nsjail` enabled.

---

### Run the setup script

Use the following commands in your terminal to run the setup script:

```bash
chmod +x setup_local.sh
./setup_local.sh

---

## ☁️ Deploying to Google Cloud Run

### Build & push:

```bash
gcloud builds submit --tag gcr.io/<PROJECT-ID>/python-executor
```

### Deploy with Cloud Run using fallback executor:

```bash
gcloud run deploy python-executor   --image gcr.io/python-exec-478709/python-executor   --platform=managed   --region=us-central1   --allow-unauthenticated   --port=8080   --command=gunicorn   --args="--bind,0.0.0.0:8080,app.main_cloud:app"
```

### Cloud Run URL

```
https://python-executor-256857162008.us-central1.run.app
```

---

## 🧪 Example Cloud Run Execution

```bash
curl -X POST   -H "Content-Type: application/json"   -d '{"script":"def main(): print("Cloud run"); return {"ok": True}"}'   https://python-executor-256857162008.us-central1.run.app/execute
```

Response:

```json
{
  "result": {"ok": true},
  "stdout": "Cloud run
"
}
```

---

## 🧪 Security Tests Performed

| Test | Expected | Result |
|------|----------|--------|
| Syntax error | Reject | ✔ Passed |
| Missing main() | Reject | ✔ Passed |
| main not callable | Reject | ✔ Passed |
| Return int | Reject | ✔ Passed |
| Return non‑serializable object | Reject | ✔ Passed |
| Infinite loop | Timeout | ✔ Passed |
| File access (`/etc/passwd`) | Blocked | ✔ Passed |
| Network (`urllib`) | Blocked | ✔ Passed |
| Large CPU loop | Local rejects (nsjail CPU limit) • Cloud allows | ✔ As expected |

---

## 🧠 Architecture Overview

```
┌────────────┐     POST /execute      ┌─────────────────────┐
│   Client   │ ─────────────────────▶ │   Flask API Server  │
└────────────┘                        │ (main/main_cloud)   │
                                      └─────────┬───────────┘
                                                │
                                ┌───────────────┴─────────────────┐
                                │ Environment Detection Logic       │
                                └───────────────┬─────────────────┘
                                                │
       ┌────────────────────────────────────────┴────────────────────────────────────┐
       │ LOCAL EXECUTION (Docker + nsjail)                                           │
       │ - true OS sandbox                                                           │
       │ - mounts tmpfs                                                               │
       │ - blocks FS, network, spawns isolated namespaces                             │
       │ - enforces CPU + timeout                                                     │
       └──────────────────────────────────────────────────────────────────────────────┘

       ┌────────────────────────────────────────┴────────────────────────────────────┐
       │ CLOUD RUN EXECUTION (fallback Python sandbox)                               │
       │ - Cloud Run does not allow nsjail                                           │
       │ - AST validation + restricted globals                                        │
       │ - Timeout enforced                                                           │
       │ - No filesystem / network                                                    │
       └──────────────────────────────────────────────────────────────────────────────┘
```

---

## 📏 Docker Image Size

- **Previous:** ~970MB  
- **Optimized Multi-stage:** **~450MB**

Techniques used:

- Compile nsjail in separate builder stage  
- Drop build dependencies  
- Remove `.pyc`, `.a`, `.o` artifacts  
- Use `python:3.11-slim`

---

## ⏱ Development Time

- ~1.5 hours coding  
- + time spent understanding nsjail constraints & Cloud Run restrictions  

---