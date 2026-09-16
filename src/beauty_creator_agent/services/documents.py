"""Transient, bounded extraction for user-uploaded reference files."""

import hashlib
import io
import zipfile
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree

from beauty_creator_agent.schemas.task import UploadedReference

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_CHARACTERS = 80_000
SUPPORTED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf"}


class DocumentExtractionError(ValueError):
    """Raised when an uploaded file cannot safely provide usable text."""


def extract_reference(
    *, filename: str, data: bytes, role: Literal["brief", "product_material", "existing_content"]
) -> UploadedReference:
    """Extract text without persisting the source file or trusting its instructions."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise DocumentExtractionError(
            "Only TXT, Markdown, DOCX, and text-based PDF files are supported."
        )
    if not data:
        raise DocumentExtractionError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise DocumentExtractionError("The uploaded file exceeds the 10 MB limit.")

    if suffix in {".txt", ".md"}:
        text = data.decode("utf-8-sig", errors="replace")
        media_type = "text/markdown" if suffix == ".md" else "text/plain"
    elif suffix == ".docx":
        text = _extract_docx_text(data)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        text = _extract_pdf_text(data)
        media_type = "application/pdf"

    compact = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not compact:
        raise DocumentExtractionError(
            "No selectable text was found. Scanned or image-only PDFs need OCR and are not "
            "supported yet."
        )
    digest = hashlib.sha256(data).hexdigest()
    return UploadedReference(
        source_id=f"upload:{digest[:16]}",
        role=role,
        media_type=media_type,
        sha256=digest,
        size_bytes=len(data),
        content=compact[:MAX_EXTRACTED_CHARACTERS],
    )


def _extract_docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            document = archive.read("word/document.xml")
        root = ElementTree.fromstring(document)
    except (KeyError, OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise DocumentExtractionError("The DOCX file is invalid or cannot be read.") from exc
    return "\n".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentExtractionError(
            "PDF support is not installed. Run the project dependency installation first."
        ) from exc
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:  # Parser-specific pypdf exceptions are not stable across releases.
        raise DocumentExtractionError("The PDF file cannot be read.") from exc
