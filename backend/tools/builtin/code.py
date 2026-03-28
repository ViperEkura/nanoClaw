"""Safe code execution tool with sandboxing and strictness levels"""
import ast
import subprocess
import sys
import tempfile
import textwrap
from typing import Dict, List, Set

from backend.tools.factory import tool
from backend.config import config


# Strictness profiles configuration
# - lenient: no restrictions at all
# - standard: allowlist based, only safe modules permitted
# - strict: minimal allowlist, only pure computation modules
STRICTNESS_PROFILES: Dict[str, dict] = {
    "lenient": {
        "timeout": 30,
        "description": "No restrictions, all modules and builtins allowed",
        "allowlist_modules": None,  # None means all allowed
        "blocked_builtins": set(),
    },

    "standard": {
        "timeout": 10,
        "description": "Allowlist based, only safe modules and builtins permitted",
        "allowlist_modules": {
            # Data types & serialization
            "json", "csv", "re", "typing",
            # Data structures
            "collections", "itertools", "functools", "operator", "heapq", "bisect",
            "array", "copy", "pprint", "enum",
            # Math & numbers
            "math", "cmath", "statistics", "random", "fractions", "decimal", "numbers",
            # Date & time
            "datetime", "time", "calendar",
            # Text processing
            "string", "textwrap", "unicodedata", "difflib",
            # Data formats
            "base64", "binascii", "quopri", "uu", "html", "xml.etree.ElementTree",
            # Functional & concurrency helpers
            "dataclasses", "hashlib", "hmac",
            # Common utilities
            "abc", "contextlib", "warnings", "logging",
        },
        "blocked_builtins": {
            "eval", "exec", "compile", "__import__",
            "open", "input", "globals", "locals", "vars",
            "breakpoint", "exit", "quit",
            "memoryview", "bytearray",
            "getattr", "setattr", "delattr",
        },
    },

    "strict": {
        "timeout": 5,
        "description": "Minimal allowlist, only pure computation modules",
        "allowlist_modules": {
            # Pure data structures
            "collections", "itertools", "functools", "operator",
            "array", "copy", "enum",
            # Pure math
            "math", "cmath", "numbers", "fractions", "decimal",
            "random", "statistics",
            # Pure text
            "string", "textwrap", "unicodedata",
            # Type hints
            "typing",
            # Utilities (no I/O)
            "dataclasses", "abc", "contextlib",
        },
        "blocked_builtins": {
            "eval", "exec", "compile", "__import__",
            "open", "input", "globals", "locals", "vars",
            "breakpoint", "exit", "quit",
            "memoryview", "bytearray",
            "dir", "hasattr", "getattr", "setattr", "delattr",
            "type", "isinstance", "issubclass",
        },
    },
}


def register_extra_modules(strictness: str, modules: Set[str] | List[str]) -> None:
    """Register additional modules to a strictness level's allowlist.

    Args:
        strictness: One of "lenient", "standard", "strict".
        modules: Module names to add to the allowlist.
    """
    if strictness not in STRICTNESS_PROFILES:
        raise ValueError(f"Invalid strictness level: {strictness}. Must be one of: {', '.join(STRICTNESS_PROFILES.keys())}")

    profile = STRICTNESS_PROFILES[strictness]
    if profile.get("allowlist_modules") is None:
        return  # lenient mode allows everything, nothing to add

    profile["allowlist_modules"].update(modules)


# Apply extra modules from config.yml on module load
for _level, _mods in config.code_execution.extra_allowed_modules.items():
    if isinstance(_mods, list) and _mods:
        register_extra_modules(_level, _mods)


@tool(
    name="execute_python",
    description="Execute Python code in a sandboxed environment with configurable strictness levels (lenient/standard/strict). "
                "Default: 'standard' mode - balances security and flexibility with 10s timeout. "
                "Use 'lenient' for data processing tasks (30s timeout, more modules allowed). "
                "Use 'strict' for basic calculations only (5s timeout, minimal module access).",
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute. Available modules depend on strictness level."
            },
            "strictness": {
                "type": "string",
                "enum": ["lenient", "standard", "strict"],
                "description": "Optional. Security strictness level (default: standard). "
                              "lenient: 30s timeout, most modules allowed; "
                              "standard: 10s timeout, balanced security; "
                              "strict: 5s timeout, minimal permissions."
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
    1. Lenient mode: no restrictions
    2. Standard/strict mode: allowlist based module restrictions
    3. Configurable blocked builtins based on strictness level
    4. Timeout limit (5s/10s/30s based on strictness)
    5. Subprocess isolation
    """
    code = arguments["code"]
    strictness = arguments.get("strictness", config.code_execution.default_strictness)
    
    # Validate strictness level
    if strictness not in STRICTNESS_PROFILES:
        return {
            "success": False,
            "error": f"Invalid strictness level: {strictness}. Must be one of: {', '.join(STRICTNESS_PROFILES.keys())}"
        }
    
    # Get profile configuration
    profile = STRICTNESS_PROFILES[strictness]
    allowlist_modules = profile.get("allowlist_modules")
    blocked_builtins = profile["blocked_builtins"]
    timeout = profile["timeout"]

    # Parse and validate code syntax first
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"success": False, "error": f"Syntax error in code: {e}"}

    # Security check: detect disallowed imports
    disallowed_imports = _check_disallowed_imports(tree, allowlist_modules)
    if disallowed_imports:
        return {
            "success": False,
            "error": f"Blocked imports: {', '.join(disallowed_imports)}. These modules are not allowed in '{strictness}' mode."
        }

    # Security check: detect dangerous function calls (skip if no restrictions)
    if blocked_builtins:
        dangerous_calls = _check_dangerous_calls(tree, blocked_builtins)
        if dangerous_calls:
            return {
                "success": False,
                "error": f"Blocked functions: {', '.join(dangerous_calls)}. These functions are not allowed in '{strictness}' mode."
            }

    # Execute in isolated subprocess
    try:
        result = subprocess.run(
            [sys.executable, "-c", _build_safe_code(code, blocked_builtins, allowlist_modules)],
            capture_output=True,
            timeout=timeout,
            cwd=tempfile.gettempdir(),
            encoding="utf-8",
            env={  # Clear environment variables
                "PYTHONIOENCODING": "utf-8",
            }
        )

        if result.returncode == 0:
            return {
                "success": True,
                "output": result.stdout,
                "strictness": strictness,
                "timeout": timeout
            }
        else:
            return {"success": False, "error": result.stderr or "Execution failed"}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Execution timeout ({timeout}s limit in '{strictness}' mode)"}
    except Exception as e:
        return {"success": False, "error": f"Execution error: {str(e)}"}


def _build_safe_code(code: str, blocked_builtins: Set[str],
                     allowlist_modules: Set[str] | None = None) -> str:
    """Build sandboxed code with restricted globals and runtime import hook."""
    allowlist_repr = "None" if allowlist_modules is None else repr(allowlist_modules)
    template = textwrap.dedent('''
        import builtins

        # Block dangerous builtins
        _BLOCKED = %r
        _safe_builtins = {k: getattr(builtins, k) for k in dir(builtins) if k not in _BLOCKED}

        # Runtime import hook for allowlist enforcement
        _ALLOWLIST = %s
        if _ALLOWLIST is not None:
            _original_import = builtins.__import__
            def _restricted_import(name, *args, **kwargs):
                top_level = name.split(".")[0]
                if top_level not in _ALLOWLIST:
                    raise ImportError(
                        f"'{top_level}' is not allowed in the current strictness mode"
                    )
                return _original_import(name, *args, **kwargs)
            builtins.__import__ = _restricted_import
            _safe_builtins["__import__"] = _restricted_import

        # Create safe namespace
        _safe_globals = {
            "__builtins__": _safe_builtins,
            "__name__": "__main__",
        }

        # Execute code
        exec(%r, _safe_globals)
    ''').strip()

    return template % (blocked_builtins, allowlist_repr, code)


def _check_disallowed_imports(tree: ast.AST, allowlist_modules: Set[str] | None) -> List[str]:
    """Check for imports not in allowlist. None allowlist means everything is allowed."""
    if allowlist_modules is None:
        return []

    disallowed = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if module not in allowlist_modules:
                    disallowed.append(module)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split(".")[0]
                if module not in allowlist_modules:
                    disallowed.append(module)

    return list(dict.fromkeys(disallowed))  # deduplicate while preserving order


def _check_dangerous_calls(tree: ast.AST, blocked_builtins: Set[str]) -> List[str]:
    """Check for blocked function calls including attribute access patterns."""
    dangerous = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                # Direct call: eval("...")
                if node.func.id in blocked_builtins:
                    dangerous.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                # Attribute call: builtins.open(...) or os.system(...)
                attr_name = node.func.attr
                if attr_name in blocked_builtins:
                    dangerous.append(attr_name)

    return list(dict.fromkeys(dangerous))
