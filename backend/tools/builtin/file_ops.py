"""File operation tools"""
import json
from pathlib import Path
from typing import Tuple
from backend.tools.factory import tool
from backend import db
from backend.models import Project
from backend.utils.workspace import get_project_path, validate_path_in_project


def _resolve_path(path: str, project_id: str = None) -> Tuple[Path, Path]:
    """
    Resolve path and ensure it's within project directory
    
    Args:
        path: File path (relative or absolute)
        project_id: Project ID for workspace isolation
        
    Returns:
        Tuple of (resolved absolute path, project directory)
        
    Raises:
        ValueError: If project_id is missing or path is outside project
    """
    if not project_id:
        raise ValueError("project_id is required for file operations")
    
    # Get project from database
    project = db.session.get(Project, project_id)
    if not project:
        raise ValueError(f"Project not found: {project_id}")
    
    # Get project directory
    project_dir = get_project_path(project.id, project.path)
    
    # Validate and resolve path
    return validate_path_in_project(path, project_dir), project_dir


@tool(
    name="file_read",
    description="Read content from a file within the project workspace. Use when you need to read file content.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to read (relative to project root or absolute within project)"
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
            "project_id": "project-uuid",
            "encoding": "utf-8"
        }

    Returns:
        {"success": true, "content": "...", "size": 100}
    """
    try:
        path, project_dir = _resolve_path(arguments["path"], arguments.get("project_id"))
        encoding = arguments.get("encoding", "utf-8")
        
        if not path.exists():
            return {"success": False, "error": f"File not found: {path}"}
        
        if not path.is_file():
            return {"success": False, "error": f"Path is not a file: {path}"}
        
        content = path.read_text(encoding=encoding)
        
        return {
            "success": True,
            "content": content,
            "size": len(content),
            "path": str(path.relative_to(project_dir))
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="file_write",
    description="Write content to a file within the project workspace. Creates the file if it doesn't exist, overwrites if it does. Use when you need to create or update a file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to write (relative to project root or absolute within project)"
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
            "project_id": "project-uuid",
            "encoding": "utf-8",
            "mode": "write"
        }

    Returns:
        {"success": true, "size": 11}
    """
    try:
        path, project_dir = _resolve_path(arguments["path"], arguments.get("project_id"))
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
            "path": str(path.relative_to(project_dir)),
            "mode": mode
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="file_delete",
    description="Delete a file within the project workspace. Use when you need to remove a file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to delete (relative to project root or absolute within project)"
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
            "path": "file.txt",
            "project_id": "project-uuid"
        }

    Returns:
        {"success": true}
    """
    try:
        path, project_dir = _resolve_path(arguments["path"], arguments.get("project_id"))
        
        if not path.exists():
            return {"success": False, "error": f"File not found: {path}"}
        
        if not path.is_file():
            return {"success": False, "error": f"Path is not a file: {path}"}
        
        rel_path = str(path.relative_to(project_dir))
        path.unlink()
        return {"success": True, "path": rel_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="file_list",
    description="List files and directories in a directory within the project workspace. Use when you need to see what files exist.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to list (relative to project root or absolute within project)",
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
            "pattern": "*",
            "project_id": "project-uuid"
        }

    Returns:
        {"success": true, "files": [...], "directories": [...]}
    """
    try:
        path, project_dir = _resolve_path(arguments.get("path", "."), arguments.get("project_id"))
        pattern = arguments.get("pattern", "*")
        
        if not path.exists():
            return {"success": False, "error": f"Directory not found: {path}"}
        
        if not path.is_dir():
            return {"success": False, "error": f"Path is not a directory: {path}"}
        
        files = []
        directories = []
        
        for item in path.glob(pattern):
            if item.is_file():
                files.append({
                    "name": item.name,
                    "size": item.stat().st_size,
                    "path": str(item.relative_to(project_dir))
                })
            elif item.is_dir():
                directories.append({
                    "name": item.name,
                    "path": str(item.relative_to(project_dir))
                })
        
        return {
            "success": True,
            "path": str(path.relative_to(project_dir)),
            "files": files,
            "directories": directories,
            "total_files": len(files),
            "total_dirs": len(directories)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="file_exists",
    description="Check if a file or directory exists within the project workspace. Use when you need to verify file existence.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to check (relative to project root or absolute within project)"
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
            "path": "file.txt",
            "project_id": "project-uuid"
        }

    Returns:
        {"exists": true, "type": "file"}
    """
    try:
        path, project_dir = _resolve_path(arguments["path"], arguments.get("project_id"))
        
        if not path.exists():
            return {"exists": False, "path": str(path.relative_to(project_dir))}
        
        if path.is_file():
            return {
                "exists": True,
                "type": "file",
                "path": str(path.relative_to(project_dir)),
                "size": path.stat().st_size
            }
        elif path.is_dir():
            return {
                "exists": True,
                "type": "directory",
                "path": str(path.relative_to(project_dir))
            }
        else:
            return {
                "exists": True,
                "type": "other",
                "path": str(path.relative_to(project_dir))
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="file_mkdir",
    description="Create a directory within the project workspace. Creates parent directories if needed. Use when you need to create a folder.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to create (relative to project root or absolute within project)"
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
            "path": "new/folder",
            "project_id": "project-uuid"
        }

    Returns:
        {"success": true}
    """
    try:
        path, project_dir = _resolve_path(arguments["path"], arguments.get("project_id"))
        
        created = not path.exists()
        path.mkdir(parents=True, exist_ok=True)
        
        return {
            "success": True,
            "path": str(path.relative_to(project_dir)),
            "created": created
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
