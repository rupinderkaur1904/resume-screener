"""
PDF validation and text extraction service.

Responsibilities:
1. Validate the uploaded file (extension + size)
2. Generate a safe unique filename so two users uploading "resume.pdf"
   never overwrite each other on disk
3. Save the file to the uploads directory
4. Extract raw text from the PDF using PyMuPDF

Kept as plain functions (no FastAPI, no DB) so they are trivial to unit test.
All FastAPI-specific things (HTTPException, UploadFile) live in the route file.

Why PyMuPDF over pdfplumber or PyPDF2?
- Fastest text extraction of the three
- Handles most real-world PDF layouts well
- Already in requirements.txt
"""
import uuid
from pathlib import Path

# NOTE:
# PyMuPDF (fitz) is imported lazily inside extract_text_from_pdf().
# This prevents backend startup from failing entirely if PyMuPDF cannot be
# installed on the current platform (e.g., Windows build requirements for pymupdf).

from app.config import get_settings

settings = get_settings()


def validate_upload(filename: str, file_size_bytes: int, file_bytes: bytes | None = None) -> None:
    """
    Check extension, size, and (optionally) PDF magic bytes.
    Raises ValueError with a human-readable message if any check fails.
    The route converts ValueError to HTTP 400.

    Why ValueError instead of HTTPException?
    Because this function has no knowledge of HTTP. Keeping it pure means
    it can be unit tested without spinning up FastAPI.

    Args:
        filename:        original filename from the upload
        file_size_bytes: size in bytes (read after spooling into memory)
        file_bytes:      optional raw bytes; when provided, validates that the
                         file starts with the PDF magic bytes (``%PDF-``).
    """
    # --- Extension check ---
    suffix = Path(filename).suffix.lower()
    allowed = settings.ALLOWED_UPLOAD_EXTENSIONS  # (".pdf",)
    if suffix not in allowed:
        raise ValueError(
            f"File type '{suffix}' is not allowed. "
            f"Accepted types: {', '.join(allowed)}"
        )

    # --- Size check ---
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise ValueError(
            f"File is too large ({file_size_bytes / 1024 / 1024:.1f} MB). "
            f"Maximum allowed size is {settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    # --- Content / magic-byte check ---
    if file_bytes is not None and not file_bytes.startswith(b"%PDF-"):
        raise ValueError(
            "File does not appear to be a valid PDF (missing %%PDF- magic bytes)."
        )


def make_safe_filename(user_id: int, original_filename: str) -> str:
    """
    Generate a unique filename that is safe to store on disk.

    Problem: two users both upload "resume.pdf" → they overwrite each other.
    Solution: prefix with user_id + a full UUID so every stored file
    is guaranteed unique.

    Example:
        user_id=1, original="Rupinder Resume Final v3.pdf"
        → "1_a3f8c2e1b4d5e6f7a8b9c0d1e2f3a4b5_Rupinder_Resume_Final_v3.pdf"

    Spaces replaced with underscores so the path is shell-safe.
    Full UUID hex (32 chars) is used to minimize collision probability.
    Path separators and control characters are stripped from the stem
    to prevent directory traversal or OS-level issues.
    """
    import re as _re
    stem = Path(original_filename).stem
    # Remove path separators, control chars, and collapse whitespace
    stem = _re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', stem)
    stem = _re.sub(r'\s+', '_', stem).strip('_')
    if not stem:
        stem = "document"
    suffix = Path(original_filename).suffix.lower()
    # Only allow safe extensions
    if suffix not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        suffix = ".pdf"
    unique_id = uuid.uuid4().hex  # 32-char hex string
    return f"{user_id}_{unique_id}_{stem}{suffix}"


def save_upload_to_disk(file_bytes: bytes, safe_filename: str) -> str:
    """
    Write the file bytes to the uploads directory.

    Returns the full file path string (stored in the DB so we can
    re-open the file later if needed).

    The uploads directory is created if it doesn't exist yet, important
    on first startup before any file has been uploaded.
    """
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / safe_filename
    file_path.write_bytes(file_bytes)

    return str(file_path)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text from a PDF using PyMuPDF (fitz).

    Why open from bytes instead of from the saved file path?
    We already have the bytes in memory from the upload. Re-reading
    from disk would be an unnecessary extra I/O operation.

    PyMuPDF opens PDFs with fitz.open(). Passing stream=bytes and
    filetype="pdf" lets it work directly from memory.

    Returns the extracted text as a single string. Empty string if
    the PDF has no extractable text layer (e.g. a scanned image PDF).

    Known limitation: a scanned/image-only PDF returns empty text here since
    there's no text layer to extract. A production version would add an OCR
    fallback (e.g. Tesseract); out of scope for this project.
    """
    text_parts = []

    try:
        import fitz  # PyMuPDF - imported lazily to avoid hard startup dependency
    except Exception as e:
        # Fail explicitly when PDF extraction is requested.
        # Auth and other APIs can still work even if PDF extraction is unavailable.
        raise RuntimeError(
            "PyMuPDF is not available in this environment; cannot extract PDF text."
        ) from e

    # Open PDF from bytes in memory - no temp file needed
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            # get_text() returns the page's text with newlines preserved
            text_parts.append(page.get_text())

    # Join all pages with a newline between them
    text = "\n".join(text_parts).strip()
    if not text:
        raise ValueError(
            "The PDF contains no extractable text (it may be a scanned image). "
            "Please upload a text-based PDF."
        )
    return text