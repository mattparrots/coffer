"""Import routes."""

from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import settings
from ..database import get_db
from ..services.import_service import detect_parser, import_file

router = APIRouter(prefix="/import")
templates = Jinja2Templates(directory=settings.templates_dir)


@router.get("", response_class=HTMLResponse)
async def import_page(request: Request):
    """Import page with file upload and history."""
    async with get_db() as db:
        # Get import history
        cursor = await db.execute(
            """
            SELECT id, filename, institution, imported_at, transaction_count, status
            FROM imports
            ORDER BY imported_at DESC
            LIMIT 20
            """
        )
        rows = await cursor.fetchall()

        imports = [
            {
                "id": row[0],
                "filename": row[1],
                "institution": row[2],
                "imported_at": row[3],
                "transaction_count": row[4],
                "status": row[5],
            }
            for row in rows
        ]

        # Get accounts for selection
        cursor = await db.execute("SELECT id, name, institution FROM accounts ORDER BY name")
        accounts = [
            {"id": row[0], "name": row[1], "institution": row[2]}
            for row in await cursor.fetchall()
        ]

    return templates.TemplateResponse(
        "imports/upload.html",
        {
            "request": request,
            "active_page": "import",
            "imports": imports,
            "accounts": accounts,
        },
    )


@router.post("/upload", response_class=HTMLResponse)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
):
    """Handle file upload and import."""
    settings.ensure_directories()

    # Save uploaded file
    file_path = settings.imports_dir / file.filename
    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    try:
        # Import the file
        async with get_db() as db:
            # First, detect the parser and show preview
            parser = await detect_parser(file_path)

            if not parser:
                return templates.TemplateResponse(
                    "imports/_result.html",
                    {
                        "request": request,
                        "success": False,
                        "error": "Could not detect file format. Supported formats: Chase CSV, Venmo CSV, Apple Card CSV",
                    },
                )

            # Parse and import
            result = await import_file(db, file_path)

            return templates.TemplateResponse(
                "imports/_result.html",
                {
                    "request": request,
                    "success": True,
                    "result": result,
                },
            )

    except Exception as e:
        return templates.TemplateResponse(
            "imports/_result.html",
            {
                "request": request,
                "success": False,
                "error": str(e),
            },
        )
