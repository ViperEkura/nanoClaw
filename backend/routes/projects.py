"""Project management API routes"""
import os
import uuid
import shutil
from datetime import datetime, timezone
from flask import Blueprint, request, g

from backend import db
from backend.models import Project
from backend.utils.helpers import ok, err
from backend.utils.workspace import (
    create_project_directory,
    delete_project_directory,
    get_project_path,
    save_uploaded_files,
    validate_path_in_project,
)

bp = Blueprint("projects", __name__)


def _get_project(project_id, check_owner=True):
    """Get project with optional ownership check."""
    project = db.session.get(Project, project_id)
    if not project:
        return None
    if check_owner and project.user_id != g.current_user.id:
        return None
    return project


@bp.route("/api/projects", methods=["GET"])
def list_projects():
    """List all projects for current user"""
    user = g.current_user
    cursor = request.args.get("cursor")
    limit = min(int(request.args.get("limit", 20)), 100)
    q = Project.query.filter_by(user_id=user.id)

    if cursor:
        q = q.filter(Project.updated_at < (
            db.session.query(Project.updated_at).filter_by(id=cursor).scalar() or datetime.now(timezone.utc)))
    rows = q.order_by(Project.updated_at.desc()).limit(limit + 1).all()

    items = [
        {
            "id": p.id,
            "name": p.name,
            "path": p.path,
            "description": p.description,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "conversation_count": p.conversations.count(),
        }
        for p in rows[:limit]
    ]
    return ok({
        "items": items,
        "next_cursor": items[-1]["id"] if len(rows) > limit else None,
        "has_more": len(rows) > limit,
        "total": Project.query.filter_by(user_id=user.id).count(),
    })


@bp.route("/api/projects", methods=["POST"])
def create_project():
    """Create a new project"""
    user = g.current_user
    data = request.get_json()

    if not data:
        return err(400, "No data provided")

    name = data.get("name", "").strip()
    description = data.get("description", "")

    if not name:
        return err(400, "Project name is required")

    # Check if project name already exists for this user
    existing = Project.query.filter_by(user_id=user.id, name=name).first()
    if existing:
        return err(400, f"Project '{name}' already exists")

    # Create project directory
    try:
        relative_path, absolute_path = create_project_directory(name, user.id)
    except Exception as e:
        return err(500, f"Failed to create project directory: {str(e)}")

    # Create project record
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user.id,
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
    user = g.current_user
    project = _get_project(project_id)

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
    user = g.current_user
    project = _get_project(project_id)
    
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
    project = _get_project(project_id)

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
    user = g.current_user
    project_name = request.form.get("name", "").strip()
    description = request.form.get("description", "")

    files = request.files.getlist("files")

    if not files:
        return err(400, "No files uploaded")

    if not project_name:
        # Use first file's top-level folder name
        project_name = files[0].filename.split("/")[0] if files[0].filename else "untitled"

    # Check if project name already exists
    existing = Project.query.filter_by(user_id=user.id, name=project_name).first()
    if existing:
        return err(400, f"Project '{project_name}' already exists")

    # Create project directory first
    try:
        relative_path, absolute_path = create_project_directory(project_name, user.id)
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
        user_id=user.id,
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
    project = _get_project(project_id)

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


# --- REST file operation endpoints ---

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB read limit
TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".vue", ".html", ".css", ".scss", ".less",
    ".json", ".yaml", ".yml", ".toml", ".xml", ".csv", ".md", ".txt", ".log",
    ".sh", ".bash", ".zsh", ".bat", ".ps1", ".cmd",
    ".c", ".h", ".cpp", ".hpp", ".java", ".go", ".rs", ".rb", ".php",
    ".sql", ".r", ".swift", ".kt", ".dart", ".lua", ".pl", ".m",
    ".ini", ".cfg", ".conf", ".env", ".gitignore", ".dockerignore",
    ".dockerfile", ".makefile", ".cmake", ".gradle", ".properties",
    ".proto", ".graphql", ".tf", ".hcl",
}


def _resolve_file_path(project_id, filepath):
    """Resolve and validate a file path within a project directory."""
    project = _get_project(project_id)
    if not project:
        return None, None, err(404, "Project not found")
    project_dir = get_project_path(project.id, project.path)
    try:
        target = validate_path_in_project(filepath, project_dir)
    except ValueError:
        return None, None, err(403, "Invalid path: outside project directory")
    return project_dir, target, None


@bp.route("/api/projects/<project_id>/files/<path:filepath>", methods=["GET"])
def read_project_file(project_id, filepath):
    """Read a single file's content (text only)."""
    project_dir, target, error = _resolve_file_path(project_id, filepath)
    if error:
        return error

    if not target.exists():
        return err(404, "File not found")
    if not target.is_file():
        return err(400, "Path is not a file")

    if target.stat().st_size > MAX_FILE_SIZE:
        return err(400, "File too large (max 5 MB)")

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return err(400, "Binary file, cannot preview as text")

    return ok({
        "name": target.name,
        "path": str(target.relative_to(project_dir)),
        "size": target.stat().st_size,
        "extension": target.suffix,
        "content": content,
    })


@bp.route("/api/projects/<project_id>/files/<path:filepath>", methods=["PUT"])
def write_project_file(project_id, filepath):
    """Create or overwrite a file."""
    data = request.get_json()
    if not data or "content" not in data:
        return err(400, "Missing 'content' in request body")

    project_dir, target, error = _resolve_file_path(project_id, filepath)
    if error:
        return error

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data["content"], encoding="utf-8")
    except Exception as e:
        return err(500, f"Failed to write file: {str(e)}")

    return ok({
        "name": target.name,
        "path": str(target.relative_to(project_dir)),
        "size": target.stat().st_size,
    })


@bp.route("/api/projects/<project_id>/files/<path:filepath>", methods=["PATCH"])
def rename_project_file(project_id, filepath):
    """Rename or move a file/directory."""
    data = request.get_json()
    if not data or "new_path" not in data:
        return err(400, "Missing 'new_path' in request body")

    project_dir, target, error = _resolve_file_path(project_id, filepath)
    if error:
        return error

    if not target.exists():
        return err(404, "File not found")

    try:
        new_target = validate_path_in_project(data["new_path"], project_dir)
    except ValueError:
        return err(403, "Invalid path: outside project directory")

    if new_target.exists():
        return err(400, "Destination already exists")

    try:
        new_target.parent.mkdir(parents=True, exist_ok=True)
        target.rename(new_target)
    except Exception as e:
        return err(500, f"Failed to rename: {str(e)}")

    return ok({
        "name": new_target.name,
        "path": str(new_target.relative_to(project_dir)),
    })


@bp.route("/api/projects/<project_id>/files/<path:filepath>", methods=["DELETE"])
def delete_project_file(project_id, filepath):
    """Delete a file or directory."""
    project_dir, target, error = _resolve_file_path(project_id, filepath)
    if error:
        return error

    if not target.exists():
        return err(404, "File not found")

    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    except Exception as e:
        return err(500, f"Failed to delete: {str(e)}")

    return ok({"message": f"Deleted '{filepath}'"})


@bp.route("/api/projects/<project_id>/directories", methods=["POST"])
def create_project_directory_endpoint(project_id):
    """Create a directory in the project."""
    project = _get_project(project_id)
    if not project:
        return err(404, "Project not found")

    data = request.get_json()
    if not data or "path" not in data:
        return err(400, "Missing 'path' in request body")

    project_dir = get_project_path(project.id, project.path)
    try:
        target = validate_path_in_project(data["path"], project_dir)
    except ValueError:
        return err(403, "Invalid path: outside project directory")

    try:
        target.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        return err(400, "Directory already exists")
    except Exception as e:
        return err(500, f"Failed to create directory: {str(e)}")

    return ok({
        "path": str(target.relative_to(project_dir)),
    })


@bp.route("/api/projects/<project_id>/search", methods=["POST"])
def search_project_files(project_id):
    """Search file contents (grep-like)."""
    data = request.get_json()
    if not data or "query" not in data:
        return err(400, "Missing 'query' in request body")

    query = data["query"]
    subdir = data.get("path", "")
    max_results = min(data.get("max_results", 50), 200)
    case_sensitive = data.get("case_sensitive", False)

    project = _get_project(project_id)
    if not project:
        return err(404, "Project not found")

    project_dir = get_project_path(project.id, project.path)
    target_dir = project_dir / subdir if subdir else project_dir

    try:
        target_dir = target_dir.resolve()
        target_dir.relative_to(project_dir.resolve())
    except ValueError:
        return err(403, "Invalid path: outside project directory")

    if not target_dir.exists():
        return err(404, "Directory not found")

    import re
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(re.escape(query), flags)
    except re.error:
        return err(400, "Invalid search pattern")

    results = []
    try:
        for file_path in target_dir.rglob("*"):
            if len(results) >= max_results:
                break
            if not file_path.is_file():
                continue
            if file_path.name.startswith("."):
                continue
            # Skip binary files by extension
            if file_path.suffix.lower() not in TEXT_EXTENSIONS and file_path.suffix != "":
                continue

            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            matches = []
            for i, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    matches.append({"line": i, "content": line})
                    if sum(len(m.get("content", "")) for m in matches) > 10000:
                        break
            if matches:
                results.append({
                    "path": str(file_path.relative_to(project_dir)),
                    "matches": matches,
                })
    except Exception as e:
        return err(500, f"Search failed: {str(e)}")

    return ok({
        "query": query,
        "results": results,
        "total_matches": len(results),
    })
