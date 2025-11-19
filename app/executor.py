
import ast
import json
import os
import subprocess
import tempfile
import traceback
from typing import Dict, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScriptExecutionError(Exception):
    """Custom exception for script execution errors."""
    pass


class ScriptExecutor:

    
    # Configuration constants
    NSJAIL_BIN = "/usr/bin/nsjail"
    NSJAIL_CFG = "/app/config/nsjail.cfg"
    PYTHON_BIN = "/usr/local/bin/python3"  # python:3.11-slim location
    EXECUTION_TIMEOUT = 5  # seconds
    MAX_SCRIPT_SIZE = 1024 * 100  # 100KB max script size
    
    # Result markers for parsing
    RESULT_START_MARKER = "<<<RESULT_START>>>"
    RESULT_END_MARKER = "<<<RESULT_END>>>"
    
    def __init__(self):
        self._verify_dependencies()
    
    def _verify_dependencies(self) -> None:

        if not os.path.exists(self.NSJAIL_BIN):
            raise ScriptExecutionError(f"nsjail not found at {self.NSJAIL_BIN}")
        
        if not os.path.exists(self.NSJAIL_CFG):
            raise ScriptExecutionError(f"nsjail config not found at {self.NSJAIL_CFG}")
        
        if not os.path.exists(self.PYTHON_BIN):
            raise ScriptExecutionError(f"Python not found at {self.PYTHON_BIN}")
    
    @staticmethod
    def validate_script(script: str) -> Tuple[bool, str]:
        # Check for empty script
        if not script or not script.strip():
            return False, "Script cannot be empty"
        
        # Check script size to prevent DoS
        if len(script) > ScriptExecutor.MAX_SCRIPT_SIZE:
            return False, f"Script too large (max {ScriptExecutor.MAX_SCRIPT_SIZE} bytes)"
        
        # Parse and validate syntax
        try:
            tree = ast.parse(script)
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Failed to parse script: {str(e)}"
        
        # Check for main() function at module level
        has_main = False
        main_is_function = False
        
        for node in tree.body:  # Only check top-level definitions
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                has_main = True
                main_is_function = True
                break
            elif isinstance(node, ast.Assign):
                # Check if someone assigned main = something
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "main":
                        has_main = True
                        main_is_function = False
        
        # if not has_main:
        #     return False, 
        
        # if not main_is_function:
        #     return False,
        if not has_main:
            return False, "Script must define a main() function"

        if not main_is_function:
            return False, "main must be a function, not a variable"
        
        return True, ""
    
    @staticmethod
    def create_wrapper_script(script_path: str) -> str:
        """
        Create a wrapper script that safely executes the user script.
        
        The wrapper:
        - Loads and executes the user script in an isolated namespace
        - Validates that main() exists and is callable
        - Calls main() and captures its return value
        - Validates the return value is JSON-serializable
        - Writes the result to stderr (our control channel)
        - Keeps stdout clean for user print() statements
        
        Args:
            script_path: Absolute path to the user's script file
            
        Returns:
            Wrapper script as string
        """
        # Using triple quotes and explicit escaping for safety
        wrapper = f'''#!/usr/bin/env python3
import sys
import json
import traceback

def main_wrapper():
    """Execute user script and return result."""
    try:
        # Read user script
        with open('{script_path}', 'r', encoding='utf-8') as f:
            user_code = f.read()
        
        # Create isolated namespace for execution
        namespace = {{
            '__name__': '__main__',
            '__builtins__': __builtins__,
        }}
        
        # Execute user code in namespace
        exec(user_code, namespace)
        
        # Verify main() exists
        if 'main' not in namespace:
            print("ERROR: Script must define a main() function", file=sys.stderr)
            return False
        
        # Verify main is callable
        if not callable(namespace['main']):
            print("ERROR: main must be a function, not a variable", file=sys.stderr)
            return False
        
        # Call user's main() function
        try:
            result = namespace['main']()
        except Exception as e:
            print(f"ERROR: Exception in main(): {{type(e).__name__}}: {{str(e)}}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return False

        # Validate result is a JSON object (dict) or array (list)
        if not isinstance(result, (dict, list)):
            print(f"ERROR: main() must return a JSON object (dict) or array (list). Got {{type(result).__name__}}", file=sys.stderr)
            return False
        
        # Validate result is JSON serializable
        try:
            json_result = json.dumps(result)
        except (TypeError, ValueError) as e:
            print(f"ERROR: main() must return JSON-serializable data. Got {{type(result).__name__}}: {{str(e)}}", file=sys.stderr)
            return False
        
        # Write result to stderr (our control channel)
        print("{ScriptExecutor.RESULT_START_MARKER}", file=sys.stderr)
        print(json_result, file=sys.stderr)
        print("{ScriptExecutor.RESULT_END_MARKER}", file=sys.stderr)
        
        return True
        
    except Exception as e:
        print(f"ERROR: Wrapper execution failed: {{type(e).__name__}}: {{str(e)}}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False

if __name__ == "__main__":
    success = main_wrapper()
    sys.exit(0 if success else 1)
'''
        return wrapper
    
    # def _parse_execution_output(self, stdout: str, stderr: str, returncode: int) -> Dict:
    #     """
    #     Parse the output from script execution.
        
    #     Args:
    #         stdout: Standard output from execution
    #         stderr: Standard error from execution
    #         returncode: Process return code
            
    #     Returns:
    #         Dictionary with result/error information
    #     """
    #     # Check if execution was successful by looking for result markers
    #     if self.RESULT_START_MARKER in stderr and self.RESULT_END_MARKER in stderr:
    #         try:
    #             # Extract JSON result from stderr
    #             result_start = stderr.find(self.RESULT_START_MARKER) + len(self.RESULT_START_MARKER)
    #             result_end = stderr.find(self.RESULT_END_MARKER)
    #             result_json = stderr[result_start:result_end].strip()
                
    #             # Parse JSON
    #             result = json.loads(result_json)
                
    #             return {
    #                 'result': result,
    #                 'stdout': stdout
    #             }
    #         except json.JSONDecodeError as e:
    #             logger.error(f"Failed to parse result JSON: {e}")
    #             return {
    #                 'error': 'Failed to parse execution result as JSON',
    #                 'details': f"JSON decode error: {str(e)}"
    #             }
    #     else:
    #         # Execution failed - extract error message
    #         if 'ERROR:' in stderr:
    #             # Extract first ERROR line for cleaner message
    #             error_lines = [line for line in stderr.split('\n') if line.strip().startswith('ERROR:')]
    #             if error_lines:
    #                 error_msg = error_lines[0].replace('ERROR:', '').strip()
    #                 return {'error': error_msg}
            
    #         # Generic failure message
    #         if returncode != 0:
    #             return {
    #                 'error': f'Script execution failed with return code {returncode}',
    #                 'details': stderr.strip() if stderr.strip() else 'No error details available'
    #             }
    #         else:
    #             return {
    #                 'error': 'Script execution failed: no result returned',
    #                 'details': stderr.strip() if stderr.strip() else 'No error details available'
    #             }

    def _parse_execution_output(self, stdout: str, stderr: str, returncode: int) -> Dict:

    # Check if execution was successful by looking for result markers
        if self.RESULT_START_MARKER in stderr and self.RESULT_END_MARKER in stderr:
            try:
                # Extract JSON result from stderr
                result_start = stderr.find(self.RESULT_START_MARKER) + len(self.RESULT_START_MARKER)
                result_end = stderr.find(self.RESULT_END_MARKER)
                result_json = stderr[result_start:result_end].strip()
                
                # Parse JSON
                result = json.loads(result_json)
                
                return {
                    'result': result,
                    'stdout': stdout
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse result JSON: {e}")
                return {
                    'error': 'Failed to parse execution result as JSON',
                    'details': f"JSON decode error: {str(e)}"
                }
        else:
            # Execution failed - extract error message
            if 'ERROR:' in stderr:
                # Extract first ERROR line for main error message
                error_lines = [line for line in stderr.split('\n') if line.strip().startswith('ERROR:')]
                if error_lines:
                    error_msg = error_lines[0].replace('ERROR:', '').strip()
                    
                    # Provide helpful context based on error type
                    details = self._get_error_details(error_msg, stderr)
                    
                    return {
                        'error': error_msg,
                        'details': details
                    }
            
            # Generic failure message
            if returncode != 0:
                return {
                    'error': f'Script execution failed with return code {returncode}',
                    'details': stderr.strip() if stderr.strip() else 'No error details available'
                }
            else:
                return {
                    'error': 'Script execution failed: no result returned',
                    'details': stderr.strip() if stderr.strip() else 'No error details available'
                }

    def _get_error_details(self, error_msg: str, stderr: str) -> str:
  
        error_lower = error_msg.lower()
        
        # Memory errors
        if 'memoryerror' in error_lower:
            return 'Your script exceeded the 512MB memory limit. Consider processing data in smaller chunks or optimizing memory usage.'
        
        # Network/URL errors
        elif 'urlerror' in error_lower or 'name resolution' in error_lower:
            return 'Network access is blocked for security. Scripts cannot make external HTTP requests or access the internet.'
        
        # File not found (security)
        elif 'filenotfounderror' in error_lower or 'no such file' in error_lower:
            return 'File system access is restricted for security. Scripts can only access their own temporary execution directory.'
        
        # Permission denied
        elif 'permissionerror' in error_lower or 'permission denied' in error_lower:
            return 'File system access is restricted for security. Scripts have limited permissions for safety.'
        
        # Import errors
        elif 'importerror' in error_lower or 'modulenotfounderror' in error_lower:
            return 'Module not found. Only os, pandas, and numpy are available. Check your import statements.'
        
        # Syntax errors (shouldn't reach here due to validation, but just in case)
        elif 'syntaxerror' in error_lower:
            return 'Invalid Python syntax. Please check your code for syntax errors.'
        
        # Generic - include traceback if available
        else:
            # Extract just the relevant error info, not the full traceback
            lines = stderr.strip().split('\n')
            # Get last few lines which usually contain the actual error
            relevant_lines = [line for line in lines if line.strip() and not line.startswith('[')]
            if len(relevant_lines) > 3:
                return '\n'.join(relevant_lines[-3:])
            return stderr.strip() if stderr.strip() else 'An error occurred during script execution.'
        
    def execute(self, script: str) -> Dict:
       
        logger.info("Starting script execution")
        
        # Step 1: Validate script
        is_valid, error_msg = self.validate_script(script)
        if not is_valid:
            logger.warning(f"Script validation failed: {error_msg}")
            return {"error": f"Validation failed: {error_msg}"}
        
        # Step 2: Create temporary directory for isolated execution
        # This automatically cleans up when the context exits
        with tempfile.TemporaryDirectory(prefix='sandbox_') as tmpdir:
            try:
                logger.info(f"Created temp directory: {tmpdir}")
                
                # Step 3: Write user script to temp file
                script_path = os.path.join(tmpdir, "user_script.py")
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(script)
                os.chmod(script_path, 0o644)  # Make readable by nsjail user
                
                logger.debug(f"Wrote user script to {script_path}")
                
                # Step 4: Create and write wrapper script
                wrapper_path = os.path.join(tmpdir, "wrapper.py")
                wrapper_code = self.create_wrapper_script(script_path)
                with open(wrapper_path, 'w', encoding='utf-8') as f:
                    f.write(wrapper_code)
                os.chmod(wrapper_path, 0o644)  # Make readable by nsjail user
                os.chmod(tmpdir, 0o755)  # Make temp dir accessible
                
                logger.debug(f"Wrote wrapper script to {wrapper_path}")
                
                # Step 5: Construct nsjail command
                nsjail_cmd = [
                    self.NSJAIL_BIN,
                    '--config', self.NSJAIL_CFG,
                    '--',
                    self.PYTHON_BIN, wrapper_path
                ]
                
                logger.info(f"Executing: {' '.join(nsjail_cmd)}")
                
                # Step 6: Execute with timeout and capture output
                try:
                    process = subprocess.run(
                        nsjail_cmd,
                        capture_output=True,
                        text=True,
                        timeout=self.EXECUTION_TIMEOUT,
                        cwd=tmpdir  # Set working directory to temp dir
                    )
                    
                    stdout = process.stdout
                    stderr = process.stderr
                    returncode = process.returncode
                    
                    logger.info(f"Execution completed with return code {returncode}")
                    logger.debug(f"stdout length: {len(stdout)}, stderr length: {len(stderr)}")
                    
                except subprocess.TimeoutExpired:
                    logger.warning(f"Execution timeout after {self.EXECUTION_TIMEOUT}s")
                    return {
                        'error': f'Execution timeout: script exceeded {self.EXECUTION_TIMEOUT} second limit',
                        'details': 'Your script took too long to execute. Check for infinite loops or heavy computations.'
                    }
                
                # Step 7: Parse and return results
                result = self._parse_execution_output(stdout, stderr, returncode)
                
                if 'error' in result:
                    logger.warning(f"Execution failed: {result['error']}")
                else:
                    logger.info("Execution successful")
                
                return result
                
            except Exception as e:
                logger.error(f"Unexpected error during execution: {str(e)}", exc_info=True)
                return {
                    'error': f'Internal execution error: {type(e).__name__}',
                    'details': str(e)
                }
        
        # Temp directory is automatically cleaned up here


# Convenience function for direct usage
def execute_script(script: str) -> Dict:
    """
    Convenience function to execute a script.
    
    Args:
        script: Python script as string
        
    Returns:
        Execution result dictionary
    """
    executor = ScriptExecutor()
    return executor.execute(script)