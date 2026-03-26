"""Project management API routes"""
import os
import uuid
import shutil
from flask import Blueprint, request

from backend import db
from backend.models import Project, User
from backend.utils.helpers import ok, err
from backend.utils.workspace import (
    create_project_directory,
    delete_project_directory,
    get_project_path,
    save_uploaded_files
)

bp = Blueprint("projects", __name__)


@bp.route("/api/projects", methods=["GET"])
def list_projects():
    """List all projects for a user"""
    user_id = request.args.get("user_id", type=int)
    
    if not user_id:
        return err(400, "Missing user_id parameter")
    
    projects = Project.query.filter_by(user_id=user_id).order_by(Project.updated_at.desc()).all()
    
    return ok({
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "path": p.path,
                "description": p.description,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "conversation_count": p.conversations.count()
            }
            for p in projects
        ],
        "total": len(projects)
    })


@bp.route("/api/projects", methods=["POST"])
def create_project():
    """Create a new project"""
    data = request.get_json()
    
    if not data:
        return err(400, "No data provided")
    
    user_id = data.get("user_id")
    name = data.get("name", "").strip()
    description = data.get("description", "")
    
    if not user_id:
        return err(400, "Missing user_id")
    
    if not name:
        return err(400, "Project name is required")
    
    # Check if user exists
    user = User.query.get(user_id)
    if not user:
        return err(404, "User not found")
    
    # Check if project name already exists for this user
    existing = Project.query.filter_by(user_id=user_id, name=name).first()
    if existing:
        return err(400, f"Project '{name}' already exists")
    
    # Create project directory
    try:
        relative_path, absolute_path = create_project_directory(name, user_id)
    except Exception as e:
        return err(500, f"Failed to create project directory: {str(e)}")
    
    # Create project record
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=name,
        path=relative_path,
        description=description
    )
    
    db.session.add(project)
    db.session.commit()
    
    return ok({
        "id": project.id,
        "name": project.name,
        "path": project.path,
        "description": project.description,
        "created_at": project.created_at.isoformat()
    })


@bp.route("/api/projects/<project_id>", methods=["GET"])
def get_project(project_id):
    """Get project details"""
    project = Project.query.get(project_id)
    
    if not project:
        return err(404, "Project not found")
    
    # Get absolute path
    absolute_path = get_project_path(project.id, project.path)
    
    # Get directory statistics
    file_count = sum(1 for _ in absolute_path.rglob("*") if _.is_file())
    dir_count = sum(1 for _ in absolute_path.rglob("*") if _.is_dir())
    total_size = sum(f.stat().st_size for f in absolute_path.rglob("*") if f.is_file())
    
    return ok({
        "id": project.id,
        "name": project.name,
        "path": project.path,
        "absolute_path": str(absolute_path),
        "description": project.description,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        "conversation_count": project.conversations.count(),
        "stats": {
            "files": file_count,
            "directories": dir_count,
            "total_size": total_size
        }
    })


@bp.route("/api/projects/<project_id>", methods=["PUT"])
def update_project(project_id):
    """Update project details"""
    project = Project.query.get(project_id)
    
    if not project:
        return err(404, "Project not found")
    
    data = request.get_json()
    
    if not data:
        return err(400, "No data provided")
    
    # Update name if provided
    if "name" in data:
        name = data["name"].strip()
        if not name:
            return err(400, "Project name cannot be empty")
        
        # Check if new name conflicts with existing project
        existing = Project.query.filter(
            Project.user_id == project.user_id,
            Project.name == name,
            Project.id != project_id
        ).first()
        
        if existing:
            return err(400, f"Project '{name}' already exists")
        
        project.name = name
    
    # Update description if provided
    if "description" in data:
        project.description = data["description"]
    
    db.session.commit()
    
    return ok({
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "updated_at": project.updated_at.isoformat()
    })


@bp.route("/api/projects/<project_id>", methods=["DELETE"])
def delete_project(project_id):
    """Delete a project"""
    project = Project.query.get(project_id)
    
    if not project:
        return err(404, "Project not found")
    
    # Delete project directory
    try:
        delete_project_directory(project.path)
    except Exception as e:
        return err(500, f"Failed to delete project directory: {str(e)}")
    
    # Delete project record (cascades to conversations and messages)
    db.session.delete(project)
    db.session.commit()
    
    return ok({"message": "Project deleted successfully"})


@bp.route("/api/projects/upload", methods=["POST"])
def upload_project_folder():
    """Upload a folder as a new project via file upload"""
    user_id = request.form.get("user_id", type=int)
    project_name = request.form.get("name", "").strip()
    description = request.form.get("description", "")

    files = request.files.getlist("files")

    if not user_id:
        return err(400, "Missing user_id")

    if not files:
        return err(400, "No files uploaded")

    if not project_name:
        # Use first file's top-level folder name
        project_name = files[0].filename.split("/")[0] if files[0].filename else "untitled"

    # Check if user exists
    user = User.query.get(user_id)
    if not user:
        return err(404, "User not found")

    # Check if project name already exists
    existing = Project.query.filter_by(user_id=user_id, name=project_name).first()
    if existing:
        return err(400, f"Project '{project_name}' already exists")

    # Create project directory first
    try:
        relative_path, absolute_path = create_project_directory(project_name, user_id)
    except Exception as e:
        return err(500, f"Failed to create project directory: {str(e)}")

    # Write uploaded files to project directory
    try:
        stats = save_uploaded_files(files, absolute_path)
    except Exception as e:
        shutil.rmtree(absolute_path, ignore_errors=True)
        return err(500, f"Failed to save uploaded files: {str(e)}")

    # Create project record
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=project_name,
        path=relative_path,
        description=description
    )

    db.session.add(project)
    db.session.commit()

    return ok({
        "id": project.id,
        "name": project.name,
        "path": project.path,
        "description": project.description,
        "created_at": project.created_at.isoformat(),
        "stats": stats
    })


@bp.route("/api/projects/<project_id>/files", methods=["GET"])
def list_project_files(project_id):
    """List files in a project directory"""
    project = Project.query.get(project_id)
    
    if not project:
        return err(404, "Project not found")
    
    project_dir = get_project_path(project.id, project.path)
    
    # Get subdirectory parameter
    subdir = request.args.get("path", "")
    
    try:
        target_dir = project_dir / subdir if subdir else project_dir
        target_dir = target_dir.resolve()
        
        # Validate path is within project
        target_dir.relative_to(project_dir.resolve())
    except ValueError:
        return err(403, "Invalid path: outside project directory")
    
    if not target_dir.exists():
        return err(404, "Directory not found")
    
    if not target_dir.is_dir():
        return err(400, "Path is not a directory")
    
    # List files
    files = []
    directories = []
    
    try:
        for item in target_dir.iterdir():
            # Skip hidden files
            if item.name.startswith("."):
                continue
            
            relative_path = item.relative_to(project_dir)
            
            if item.is_file():
                files.append({
                    "name": item.name,
                    "path": str(relative_path),
                    "size": item.stat().st_size,
                    "extension": item.suffix
                })
            elif item.is_dir():
                directories.append({
                    "name": item.name,
                    "path": str(relative_path)
                })
    except Exception as e:
        return err(500, f"Failed to list directory: {str(e)}")
    
    return ok({
        "project_id": project_id,
        "current_path": str(subdir) if subdir else "/",
        "files": files,
        "directories": directories,
        "total_files": len(files),
        "total_dirs": len(directories)
    })
