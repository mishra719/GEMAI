"""
ZIP file generation service for coding mode.
"""
import io
import json
import logging
import re
import zipfile
from pathlib import PurePosixPath
from typing import Optional

logger = logging.getLogger(__name__)


def _decode_escaped_source(content: str) -> str:
    """Convert common JSON-escaped source text into real file content."""
    if "\\" not in content:
        return content

    if not any(token in content for token in ("\\n", "\\r", "\\t", '\\"')):
        return content

    return (
        content
        .replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
        .replace('\\"', '"')
    )


def _stringify_file_content(content) -> str:
    """Convert structured content into a string for ZIP output."""
    if isinstance(content, str):
        return _decode_escaped_source(content)
    if isinstance(content, (dict, list)):
        return json.dumps(content, indent=2, ensure_ascii=False)
    return str(content)


def normalize_project_data(project_data: dict) -> Optional[dict]:
    """Normalize project structures so ZIP generation accepts common AI output shapes."""
    if not isinstance(project_data, dict):
        return None

    project_name = str(project_data.get("project_name") or "project").strip()
    project_name = re.sub(r"[\\/:*?\"<>|]+", "-", project_name) or "project"

    raw_files = project_data.get("files")
    normalized_files: dict[str, str] = {}

    if isinstance(raw_files, dict):
        for file_path, content in raw_files.items():
            if file_path:
                normalized_files[str(file_path)] = _stringify_file_content(content)
    elif isinstance(raw_files, list):
        for entry in raw_files:
            if not isinstance(entry, dict):
                continue

            file_path = entry.get("path") or entry.get("name")
            content = entry.get("content")
            if not file_path or content is None:
                continue

            normalized_files[str(file_path)] = _stringify_file_content(content)
    else:
        return None

    if not normalized_files:
        return None

    return {
        "project_name": project_name,
        "files": normalized_files,
    }


def create_project_zip(project_data: dict) -> Optional[io.BytesIO]:
    """
    Create a ZIP file from the structured project data.
    
    Expected format:
    {
        "project_name": "my-project",
        "files": {
            "path/to/file.py": "file content...",
            ...
        }
    }
    """
    try:
        normalized = normalize_project_data(project_data)
        if not normalized:
            logger.warning("Project data could not be normalized for ZIP generation")
            return None

        project_name = normalized["project_name"]
        files = normalized["files"]

        if not files:
            logger.warning("No files found in project data")
            return None

        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        added_files = 0

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path, content in files.items():
                # Sanitize path — prevent directory traversal
                normalized_path = str(file_path).replace("\\", "/").strip()
                clean_path = normalized_path.lstrip("/")
                pure_path = PurePosixPath(clean_path)
                first_part = pure_path.parts[0] if pure_path.parts else ""

                if (
                    not clean_path
                    or not pure_path.parts
                    or re.match(r"^[A-Za-z]:$", first_part)
                    or any(part in {"", ".", ".."} for part in pure_path.parts)
                ):
                    logger.warning(f"Skipping suspicious path: {file_path}")
                    continue

                # Add file to ZIP under project_name directory
                safe_relative_path = "/".join(pure_path.parts)
                full_path = f"{project_name}/{safe_relative_path}"
                zf.writestr(full_path, content)
                added_files += 1
                logger.info(f"Added to ZIP: {full_path}")

        if added_files == 0:
            logger.warning("All files were skipped during ZIP generation")
            return None

        zip_buffer.seek(0)
        logger.info(
            f"Created ZIP for project '{project_name}' with {added_files} files"
        )
        return zip_buffer

    except Exception as e:
        logger.error(f"Error creating ZIP: {e}")
        return None
