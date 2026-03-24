"""File operation tools"""
import os
import json
from pathlib import Path
from typing import Optional
from backend.tools.factory import tool


# Base directory for file operations (sandbox)
# Set to None to allow any path, or set a specific directory for security
BASE_DIR = Path(__file__).parent.parent.parent.parent  # project root


def _resolve_path(path: str) -> Path:
    """Resolve path and ensure it's within allowed directory"""
    p = Path(path)
    if not p.is_absolute():
        p = BASE_DIR / p
    p = p.resolve()
    
    # Security check: ensure path is within BASE_DIR
    if BASE_DIR:
        try:
            p.relative_to(BASE_DIR.resolve())
        except ValueError:
            raise ValueError(f"Path '{path}' is outside allowed directory")
    
    return p


@tool(
    name="file_read",
    description="Read content from a file. Use when you need to read file content.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to read (relative to project root or absolute)"
            },
            "encoding": {
                "type": "string",
                "description": "File encoding, default utf-8",
                "default": "utf-8"
            }
        },
        "required": ["path"]
    },
    category="file"
)
def file_read(arguments: dict) -> dict:
    """
    Read file tool

    Args:
        arguments: {
            "path": "file.txt",
            "encoding": "utf-8"
        }

    Returns:
        {"content": "...", "size": 100}
    """
    try:
        path = _resolve_path(arguments["path"])
        encoding = arguments.get("encoding", "utf-8")
        
        if not path.exists():
            return {"error": f"File not found: {path}"}
        
        if not path.is_file():
            return {"error": f"Path is not a file: {path}"}
        
        content = path.read_text(encoding=encoding)
        return {
            "content": content,
            "size": len(content),
            "path": str(path)
        }
    except Exception as e:
        return {"error": str(e)}


@tool(
    name="file_write",
    description="Write content to a file. Creates the file if it doesn't exist, overwrites if it does. Use when you need to create or update a file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to write (relative to project root or absolute)"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            },
            "encoding": {
                "type": "string",
                "description": "File encoding, default utf-8",
                "default": "utf-8"
            },
            "mode": {
                "type": "string",
                "description": "Write mode: 'write' (overwrite) or 'append'",
                "enum": ["write", "append"],
                "default": "write"
            }
        },
        "required": ["path", "content"]
    },
    category="file"
)
def file_write(arguments: dict) -> dict:
    """
    Write file tool

    Args:
        arguments: {
            "path": "file.txt",
            "content": "Hello World",
            "encoding": "utf-8",
            "mode": "write"
        }

    Returns:
        {"success": true, "size": 11}
    """
    try:
        path = _resolve_path(arguments["path"])
        content = arguments["content"]
        encoding = arguments.get("encoding", "utf-8")
        mode = arguments.get("mode", "write")
        
        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write or append
        if mode == "append":
            with open(path, "a", encoding=encoding) as f:
                f.write(content)
        else:
            path.write_text(content, encoding=encoding)
        
        return {
            "success": True,
            "size": len(content),
            "path": str(path),
            "mode": mode
        }
    except Exception as e:
        return {"error": str(e)}


@tool(
    name="file_delete",
    description="Delete a file. Use when you need to remove a file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to delete (relative to project root or absolute)"
            }
        },
        "required": ["path"]
    },
    category="file"
)
def file_delete(arguments: dict) -> dict:
    """
    Delete file tool

    Args:
        arguments: {
            "path": "file.txt"
        }

    Returns:
        {"success": true}
    """
    try:
        path = _resolve_path(arguments["path"])
        
        if not path.exists():
            return {"error": f"File not found: {path}"}
        
        if not path.is_file():
            return {"error": f"Path is not a file: {path}"}
        
        path.unlink()
        return {"success": True, "path": str(path)}
    except Exception as e:
        return {"error": str(e)}


@tool(
    name="file_list",
    description="List files and directories in a directory. Use when you need to see what files exist.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to list (relative to project root or absolute)",
                "default": "."
            },
            "pattern": {
                "type": "string",
                "description": "Glob pattern to filter files, e.g. '*.py'",
                "default": "*"
            }
        },
        "required": []
    },
    category="file"
)
def file_list(arguments: dict) -> dict:
    """
    List directory contents

    Args:
        arguments: {
            "path": ".",
            "pattern": "*"
        }

    Returns:
        {"files": [...], "directories": [...]}
    """
    try:
        path = _resolve_path(arguments.get("path", "."))
        pattern = arguments.get("pattern", "*")
        
        if not path.exists():
            return {"error": f"Directory not found: {path}"}
        
        if not path.is_dir():
            return {"error": f"Path is not a directory: {path}"}
        
        files = []
        directories = []
        
        for item in path.glob(pattern):
            if item.is_file():
                files.append({
                    "name": item.name,
                    "size": item.stat().st_size,
                    "path": str(item.relative_to(BASE_DIR)) if BASE_DIR else str(item)
                })
            elif item.is_dir():
                directories.append({
                    "name": item.name,
                    "path": str(item.relative_to(BASE_DIR)) if BASE_DIR else str(item)
                })
        
        return {
            "path": str(path),
            "files": files,
            "directories": directories,
            "total_files": len(files),
            "total_dirs": len(directories)
        }
    except Exception as e:
        return {"error": str(e)}


@tool(
    name="file_exists",
    description="Check if a file or directory exists. Use when you need to verify file existence.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to check (relative to project root or absolute)"
            }
        },
        "required": ["path"]
    },
    category="file"
)
def file_exists(arguments: dict) -> dict:
    """
    Check if file/directory exists

    Args:
        arguments: {
            "path": "file.txt"
        }

    Returns:
        {"exists": true, "type": "file"}
    """
    try:
        path = _resolve_path(arguments["path"])
        
        if not path.exists():
            return {"exists": False, "path": str(path)}
        
        if path.is_file():
            return {
                "exists": True,
                "type": "file",
                "path": str(path),
                "size": path.stat().st_size
            }
        elif path.is_dir():
            return {
                "exists": True,
                "type": "directory",
                "path": str(path)
            }
        else:
            return {
                "exists": True,
                "type": "other",
                "path": str(path)
            }
    except Exception as e:
        return {"error": str(e)}


@tool(
    name="file_mkdir",
    description="Create a directory. Creates parent directories if needed. Use when you need to create a folder.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to create (relative to project root or absolute)"
            }
        },
        "required": ["path"]
    },
    category="file"
)
def file_mkdir(arguments: dict) -> dict:
    """
    Create directory

    Args:
        arguments: {
            "path": "new/folder"
        }

    Returns:
        {"success": true}
    """
    try:
        path = _resolve_path(arguments["path"])
        path.mkdir(parents=True, exist_ok=True)
        return {
            "success": True,
            "path": str(path),
            "created": not path.exists() or path.is_dir()
        }
    except Exception as e:
        return {"error": str(e)}
