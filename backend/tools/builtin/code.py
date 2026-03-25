"""Safe code execution tool with sandboxing"""
import ast
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from backend.tools.factory import tool


# Whitelist of allowed modules
ALLOWED_MODULES = {
    # Standard library - math and data processing
    "math", "random", "statistics", "itertools", "functools", "operator",
    "collections", "decimal", "fractions", "numbers",
    # String processing
    "string", "re", "textwrap", "unicodedata",
    # Data formats
    "json", "csv", "datetime", "time",
    # Data structures
    "heapq", "bisect", "array", "copy",
    # Type related
    "typing", "types", "dataclasses",
}

# Blacklist of dangerous builtins
BLOCKED_BUILTINS = {
    "eval", "exec", "compile", "open", "input",
    "__import__", "globals", "locals", "vars",
    "breakpoint", "exit", "quit",
    "memoryview", "bytearray",
}


@tool(
    name="execute_python",
    description="Execute Python code in a sandboxed environment. Supports math, data processing, and string operations. Max execution time: 10 seconds.",
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute. Only standard library modules allowed."
            }
        },
        "required": ["code"]
    },
    category="code"
)
def execute_python(arguments: dict) -> dict:
    """
    Execute Python code safely with sandboxing.

    Security measures:
    1. Restricted imports (whitelist)
    2. Blocked dangerous builtins
    3. Timeout limit (10s)
    4. No file system access
    5. No network access
    """
    code = arguments["code"]

    # Security check: detect dangerous imports
    dangerous_imports = _check_dangerous_imports(code)
    if dangerous_imports:
        return {
            "success": False,
            "error": f"Blocked imports: {', '.join(dangerous_imports)}. Only standard library modules allowed: {', '.join(sorted(ALLOWED_MODULES))}"
        }

    # Security check: detect dangerous function calls
    dangerous_calls = _check_dangerous_calls(code)
    if dangerous_calls:
        return {
            "success": False,
            "error": f"Blocked functions: {', '.join(dangerous_calls)}"
        }

    # Execute in isolated subprocess
    try:
        result = subprocess.run(
            [sys.executable, "-c", _build_safe_code(code)],
            capture_output=True,
            timeout=10,
            cwd=tempfile.gettempdir(),
            encoding="utf-8",
            env={  # Clear environment variables
                "PYTHONIOENCODING": "utf-8",
            }
        )

        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        else:
            return {"success": False, "error": result.stderr or "Execution failed"}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Execution timeout (10s limit)"}
    except Exception as e:
        return {"success": False, "error": f"Execution error: {str(e)}"}


def _build_safe_code(code: str) -> str:
    """Build sandboxed code with restricted globals"""
    template = textwrap.dedent('''
        import builtins

        # Block dangerous builtins
        _BLOCKED = %r
        _safe_builtins = {k: getattr(builtins, k) for k in dir(builtins) if k not in _BLOCKED}

        # Create safe namespace
        _safe_globals = {
            "__builtins__": _safe_builtins,
            "__name__": "__main__",
        }

        # Execute code
        exec(%r, _safe_globals)
    ''').strip()
    
    return template % (BLOCKED_BUILTINS, code)


def _check_dangerous_imports(code: str) -> list:
    """Check for disallowed imports"""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    dangerous = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if module not in ALLOWED_MODULES:
                    dangerous.append(module)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split(".")[0]
                if module not in ALLOWED_MODULES:
                    dangerous.append(module)

    return dangerous


def _check_dangerous_calls(code: str) -> list:
    """Check for blocked function calls"""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    dangerous = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in BLOCKED_BUILTINS:
                    dangerous.append(node.func.id)

    return dangerous
