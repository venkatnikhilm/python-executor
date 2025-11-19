import ast
import json
import os
import subprocess
import tempfile
import traceback
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class CloudScriptExecutor:
    PYTHON_BIN = "/usr/local/bin/python3"
    EXECUTION_TIMEOUT = 5
    MAX_SCRIPT_SIZE = 1024 * 100  # 100KB

    RESULT_START_MARKER = "<<<RESULT_START>>>"
    RESULT_END_MARKER = "<<<RESULT_END>>>"

    # ----------------------------
    # VALIDATION LOGIC (copied from executor.py)
    # ----------------------------
    @staticmethod
    def validate_script(script: str) -> Tuple[bool, str]:
        if not script or not script.strip():
            return False, "Script cannot be empty"

        if len(script) > CloudScriptExecutor.MAX_SCRIPT_SIZE:
            return False, f"Script too large (max {CloudScriptExecutor.MAX_SCRIPT_SIZE} bytes)"

        try:
            tree = ast.parse(script)
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Failed to parse script: {str(e)}"

        has_main = False
        main_is_function = False

        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                has_main = True
                main_is_function = True
                break
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "main":
                        has_main = True
                        main_is_function = False

        if not has_main:
            return False, "Script must define a main() function"

        if not main_is_function:
            return False, "main must be a function, not a variable"

        return True, ""

    # ----------------------------
    # WRAPPER SCRIPT LOGIC (unchanged)
    # ----------------------------
    @staticmethod
    def create_wrapper_script(script_path: str) -> str:
        wrapper = f'''#!/usr/bin/env python3
import sys
import json
import traceback

def main_wrapper():
    try:
        with open('{script_path}', 'r', encoding='utf-8') as f:
            user_code = f.read()

        namespace = {{
            '__name__': '__main__',
            '__builtins__': __builtins__,
        }}

        exec(user_code, namespace)

        if 'main' not in namespace:
            print("ERROR: Script must define a main() function", file=sys.stderr)
            return False

        if not callable(namespace['main']):
            print("ERROR: main must be a function, not a variable", file=sys.stderr)
            return False

        try:
            result = namespace['main']()
        except Exception as e:
            print(f"ERROR: Exception in main(): {{type(e).__name__}}: {{str(e)}}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return False

        if not isinstance(result, (dict, list)):
            print(f"ERROR: main() must return a JSON object (dict) or array (list). Got {{type(result).__name__}}", file=sys.stderr)
            return False

        try:
            json_result = json.dumps(result)
        except Exception as e:
            print(f"ERROR: main() must return JSON-serializable data: {{str(e)}}", file=sys.stderr)
            return False

        print("{CloudScriptExecutor.RESULT_START_MARKER}", file=sys.stderr)
        print(json_result, file=sys.stderr)
        print("{CloudScriptExecutor.RESULT_END_MARKER}", file=sys.stderr)

        return True
    except Exception as e:
        print(f"ERROR: Wrapper execution failed: {{str(e)}}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False

if __name__ == "__main__":
    success = main_wrapper()
    sys.exit(0 if success else 1)
'''
        return wrapper

    # ----------------------------
    # ERROR PARSING (copied)
    # ----------------------------
    def _parse_execution_output(self, stdout: str, stderr: str, returncode: int) -> Dict:

        if self.RESULT_START_MARKER in stderr and self.RESULT_END_MARKER in stderr:
            try:
                start = stderr.find(self.RESULT_START_MARKER) + len(self.RESULT_START_MARKER)
                end = stderr.find(self.RESULT_END_MARKER)
                result_json = stderr[start:end].strip()
                result = json.loads(result_json)

                return {
                    "result": result,
                    "stdout": stdout
                }
            except json.JSONDecodeError as e:
                return {"error": "Failed to parse JSON result", "details": str(e)}

        if 'ERROR:' in stderr:
            first_error = [l for l in stderr.split("\n") if l.startswith("ERROR:")]
            if first_error:
                msg = first_error[0].replace("ERROR:", "").strip()
                return {"error": msg, "details": self._get_error_details(msg, stderr)}

        if returncode != 0:
            return {"error": f"Script execution failed with return code {returncode}", "details": stderr}

        return {"error": "Unknown execution error", "details": stderr}

    # ----------------------------
    # ERROR DETAILS (same logic)
    # ----------------------------
    def _get_error_details(self, msg: str, stderr: str) -> str:
        l = msg.lower()

        if "memoryerror" in l:
            return "Script exceeded memory limits."
        if "urlerror" in l or "name resolution" in l:
            return "Network access is blocked."
        if "filenotfounderror" in l:
            return "File system access restricted."
        if "permission" in l:
            return "Permission denied inside sandbox."
        if "importerror" in l:
            return "Module not found. Only numpy/pandas/os available."
        return stderr.strip()

    # ----------------------------
    # CLOUD EXECUTION (no nsjail)
    # ----------------------------
    def execute(self, script: str) -> Dict:
        is_valid, error = self.validate_script(script)
        if not is_valid:
            return {"error": f"Validation failed: {error}"}

        with tempfile.TemporaryDirectory(prefix="sandbox_") as tmpdir:

            script_path = os.path.join(tmpdir, "user_script.py")
            wrapper_path = os.path.join(tmpdir, "wrapper.py")

            with open(script_path, "w") as f:
                f.write(script)

            wrapper_code = self.create_wrapper_script(script_path)
            with open(wrapper_path, "w") as f:
                f.write(wrapper_code)

            cmd = [self.PYTHON_BIN, wrapper_path]

            try:
                p = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.EXECUTION_TIMEOUT,
                    cwd=tmpdir
                )
            except subprocess.TimeoutExpired:
                return {"error": "Execution timeout", "details": "Script exceeded time limit"}

            return self._parse_execution_output(p.stdout, p.stderr, p.returncode)