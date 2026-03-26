"""Workspace path validation utilities"""
import os
import shutil
from pathlib import Path
from typing import Optional
from flask import current_app

from backend import load_config


def get_workspace_root() -> Path:
    """Get workspace root directory from config"""
    cfg = load_config()
    workspace_root = cfg.get("workspace_root", "./workspaces")
    
    # Convert to absolute path
    workspace_path = Path(workspace_root)
    if not workspace_path.is_absolute():
        # Relative to project root
        workspace_path = Path(__file__).parent.parent.parent / workspace_root
    
    # Create if not exists
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    return workspace_path.resolve()


def get_project_path(project_id: str, project_path: str) -> Path:
    """
    Get absolute path for a project
    
    Args:
        project_id: Project ID
        project_path: Relative path stored in database
        
    Returns:
        Absolute path to project directory
    """
    workspace_root = get_workspace_root()
    project_dir = workspace_root / project_path
    
    # Create if not exists
    project_dir.mkdir(parents=True, exist_ok=True)
    
    return project_dir.resolve()


def validate_path_in_project(path: str, project_dir: Path) -> Path:
    """
    Validate that a path is within the project directory
    
    Args:
        path: Path to validate (can be relative or absolute)
        project_dir: Project directory path
        
    Returns:
        Resolved absolute path
        
    Raises:
        ValueError: If path is outside project directory
    """
    p = Path(path)
    
    # If relative, resolve against project directory
    if not p.is_absolute():
        p = project_dir / p
    
    # Resolve to absolute path
    p = p.resolve()
    
    # Security check: ensure path is within project directory
    try:
        p.relative_to(project_dir.resolve())
    except ValueError:
        raise ValueError(f"Path '{path}' is outside project directory")
    
    return p


def create_project_directory(name: str, user_id: int) -> tuple[str, Path]:
    """
    Create a new project directory
    
    Args:
        name: Project name
        user_id: User ID
        
    Returns:
        Tuple of (relative_path, absolute_path)
    """
    workspace_root = get_workspace_root()
    
    # Create user-specific directory
    user_dir = workspace_root / f"user_{user_id}"
    user_dir.mkdir(parents=True, exist_ok=True)
    
    # Create project directory
    project_dir = user_dir / name
    
    # Handle name conflicts
    counter = 1
    original_name = name
    while project_dir.exists():
        name = f"{original_name}_{counter}"
        project_dir = user_dir / name
        counter += 1
    
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Return relative path (from workspace root) and absolute path
    relative_path = f"user_{user_id}/{name}"
    return relative_path, project_dir.resolve()


def delete_project_directory(project_path: str) -> bool:
    """
    Delete a project directory
    
    Args:
        project_path: Relative path from workspace root
        
    Returns:
        True if deleted successfully
    """
    workspace_root = get_workspace_root()
    project_dir = workspace_root / project_path
    
    if project_dir.exists() and project_dir.is_dir():
        # Verify it's within workspace root (security check)
        try:
            project_dir.resolve().relative_to(workspace_root.resolve())
            shutil.rmtree(project_dir)
            return True
        except ValueError:
            raise ValueError("Cannot delete directory outside workspace root")
    
    return False




def save_uploaded_files(files, project_dir: Path) -> dict:
    """
    Save uploaded files to project directory (for folder upload)

    Args:
        files: List of FileStorage objects from Flask request.files
        project_dir: Target project directory

    Returns:
        Dict with upload statistics
    """
    file_count = 0
    dir_count = 0
    total_size = 0

    for f in files:
        if not f.filename:
            continue

        # filename contains relative path like "AlgoLab/src/main.py"
        # Skip the first segment (folder name) since project_dir already represents it
        parts = f.filename.split("/")
        if len(parts) > 1:
            relative = "/".join(parts[1:])  # "src/main.py"
        else:
            relative = f.filename  # root-level file

        target = project_dir / relative

        # Create parent directories if needed
        target.parent.mkdir(parents=True, exist_ok=True)

        # Save file
        f.save(str(target))
        file_count += 1

        # Count new directories
        if target.parent != project_dir:
            dir_count += 1

        total_size += target.stat().st_size

    return {
        "files": file_count,
        "directories": dir_count,
        "size": total_size
    }


def copy_folder_to_project(source_path: str, project_dir: Path, project_name: str) -> dict:
    """
    Copy a folder to project directory (for folder upload)
    
    Args:
        source_path: Source folder path
        project_dir: Target project directory
        project_name: Project name
        
    Returns:
        Dict with copy statistics
    """
    source = Path(source_path)
    
    if not source.exists():
        raise ValueError(f"Source path does not exist: {source_path}")
    
    if not source.is_dir():
        raise ValueError(f"Source path is not a directory: {source_path}")
    
    # Security check: don't copy from sensitive system directories
    sensitive_dirs = ["/etc", "/usr", "/bin", "/sbin", "/root", "/home"]
    for sensitive in sensitive_dirs:
        if str(source.resolve()).startswith(sensitive):
            raise ValueError(f"Cannot copy from system directory: {sensitive}")
    
    # Copy directory
    if project_dir.exists():
        shutil.rmtree(project_dir)
    
    shutil.copytree(source, project_dir)
    
    # Count files
    file_count = sum(1 for _ in project_dir.rglob("*") if _.is_file())
    dir_count = sum(1 for _ in project_dir.rglob("*") if _.is_dir())
    
    return {
        "files": file_count,
        "directories": dir_count,
        "size": sum(f.stat().st_size for f in project_dir.rglob("*") if f.is_file())
    }
