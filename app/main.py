# app/main.py
"""
Flask REST API for secure Python script execution.

This module provides the HTTP interface for script execution requests.
It handles request validation, delegates to the executor, and formats responses.

Endpoints:
    POST /execute - Execute a Python script
    GET /health - Health check endpoint
"""

from flask import Flask, request, jsonify
from typing import Dict, Tuple
import logging
import sys

from app.executor import ScriptExecutor, ScriptExecutionError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize executor (singleton)
try:
    executor = ScriptExecutor()
    logger.info("ScriptExecutor initialized successfully")
except ScriptExecutionError as e:
    logger.error(f"Failed to initialize ScriptExecutor: {e}")
    # In production, you might want to exit here
    executor = None


@app.route('/health', methods=['GET'])
def health_check() -> Tuple[Dict, int]:
    """
    Health check endpoint.
    
    Returns:
        JSON response with health status
        
    Example:
        GET /health
        Response: {"status": "healthy", "service": "python-executor"}
    """
    if executor is None:
        return jsonify({
            'status': 'unhealthy',
            'service': 'python-executor',
            'error': 'Executor not initialized'
        }), 503
    
    return jsonify({
        'status': 'healthy',
        'service': 'python-executor'
    }), 200


@app.route('/execute', methods=['POST'])
def execute_script() -> Tuple[Dict, int]:
    """
    Execute a Python script in a sandboxed environment.
    
    Request Body:
        {
            "script": "def main():\\n    return {'result': 'value'}"
        }
    
    Response (Success):
        {
            "result": <json_object>,
            "stdout": <string>
        }
    
    Response (Error):
        {
            "error": <error_message>,
            "details": <optional_details>
        }
    
    Status Codes:
        200 - Success
        400 - Bad request (validation error)
        500 - Internal server error
        503 - Service unavailable (executor not initialized)
    
    Example:
        POST /execute
        {
            "script": "def main():\\n    print('Hello')\\n    return {'status': 'ok'}"
        }
        
        Response:
        {
            "result": {"status": "ok"},
            "stdout": "Hello\\n"
        }
    """
    logger.info("Received execution request")
    
    # Check if executor is initialized
    if executor is None:
        logger.error("Executor not initialized")
        return jsonify({
            'error': 'Service unavailable: executor not initialized'
        }), 503
    
    # Validate request has JSON content type
    if not request.is_json:
        logger.warning("Request missing JSON content type")
        return jsonify({
            'error': 'Content-Type must be application/json'
        }), 400
    
    # Get request data
    try:
        data = request.get_json()
    except Exception as e:
        logger.warning(f"Failed to parse JSON: {e}")
        return jsonify({
            'error': 'Invalid JSON in request body',
            'details': str(e)
        }), 400
    
    # Validate 'script' field exists
    if not data:
        logger.warning("Empty request body")
        return jsonify({
            'error': 'Request body cannot be empty'
        }), 400
    
    if 'script' not in data:
        logger.warning("Missing 'script' field in request")
        return jsonify({
            'error': 'Missing required field: "script"'
        }), 400
    
    script = data.get('script')
    
    # Validate script is a string
    if not isinstance(script, str):
        logger.warning(f"Invalid script type: {type(script)}")
        return jsonify({
            'error': 'Field "script" must be a string',
            'details': f'Got {type(script).__name__} instead'
        }), 400
    
    # Log script length (not content for security)
    logger.info(f"Executing script ({len(script)} bytes)")
    
    # Execute script
    try:
        result = executor.execute(script)
        
        # Check if execution resulted in error
        if 'error' in result:
            logger.info(f"Execution failed: {result['error']}")
            return jsonify(result), 400
        
        # Success
        logger.info("Execution successful")
        return jsonify(result), 200
        
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error during execution: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'details': 'An unexpected error occurred during script execution'
        }), 500


@app.errorhandler(404)
def not_found(error) -> Tuple[Dict, int]:
    """Handle 404 errors."""
    return jsonify({
        'error': 'Not found',
        'message': 'The requested endpoint does not exist. Use POST /execute or GET /health'
    }), 404


@app.errorhandler(405)
def method_not_allowed(error) -> Tuple[Dict, int]:
    """Handle 405 errors."""
    return jsonify({
        'error': 'Method not allowed',
        'message': 'Check the HTTP method. /execute requires POST, /health requires GET'
    }), 405


@app.errorhandler(500)
def internal_error(error) -> Tuple[Dict, int]:
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}", exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500


# For local development/testing
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)