from flask import Flask, request, jsonify
import logging
import sys
from app.executor_cloud import CloudScriptExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Use the Cloud Executor (no nsjail)
executor = CloudScriptExecutor()

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "python-executor-cloud"
    }), 200

@app.route("/execute", methods=["POST"])
def execute_script():
    # Validate JSON
    if not request.is_json:
        return jsonify({
            "error": "Content-Type must be application/json"
        }), 400

    data = request.get_json()
    if not data or "script" not in data:
        return jsonify({
            "error": "Missing field 'script'"
        }), 400

    # Execute the script
    result = executor.execute(data["script"])
    is_success = "result" in result

    return jsonify(result), (200 if is_success else 400)

# For local debugging of the cloud version
if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")