"""
ZIP generation API endpoint.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.models.user import User
from app.services.gemini import parse_code_response
from app.services.zip import create_project_zip, normalize_project_data

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["ZIP Generation"])


class ZipRequest(BaseModel):
    """Request schema for ZIP generation."""
    code_response: str  # The raw AI response text containing JSON project structure


@router.post("/generate-zip")
def generate_zip(
    payload: ZipRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a downloadable ZIP from a structured code response."""
    # Parse the code response
    project_data = parse_code_response(payload.code_response)
    normalized_project = normalize_project_data(project_data) if project_data else None

    if not normalized_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Could not parse a valid project structure from the response. "
                "Expected a JSON object with a non-empty 'files' object or array."
            ),
        )

    # Create ZIP
    zip_buffer = create_project_zip(normalized_project)

    if not zip_buffer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create ZIP file.",
        )

    project_name = normalized_project.get("project_name", "project")
    logger.info(f"ZIP generated for user {current_user.id}: {project_name}")

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{project_name}.zip"'
        },
    )
