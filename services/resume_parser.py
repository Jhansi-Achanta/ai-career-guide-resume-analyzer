"""Turn an uploaded resume file into clean plain text.

Supported formats
-----------------
* ``.pdf``  - text extracted with PyPDF2
* ``.docx`` - text extracted with python-docx (paragraphs, tables, headers)

Any other extension is rejected with a friendly message.  Every error raised
here is a :class:`ResumeParseError` whose text is safe to show to the user.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import config


class ResumeParseError(ValueError):
    """Raised with a friendly message that can be shown directly in the UI."""


def validate_upload(filename: str, data: bytes) -> str:
    """Validate name/size/format and return the lower-case extension (e.g. ``.pdf``)."""
    name = (filename or "").strip()
    if not name:
        raise ResumeParseError("Please choose a resume file first.")

    extension = Path(name).suffix.lower()
    if extension not in config.ALLOWED_EXTENSIONS:
        raise ResumeParseError(
            "Only PDF and DOCX resumes are supported. "
            "Please upload a .pdf or .docx file."
        )

    if not data:
        raise ResumeParseError("That file is empty. Please choose a different resume.")

    if len(data) > config.MAX_UPLOAD_BYTES:
        raise ResumeParseError(
            f"That file is too large ({_mb(len(data))} MB). "
            f"The maximum allowed size is {config.MAX_UPLOAD_MB} MB."
        )

    return extension


def extract_text(filename: str, data: bytes) -> str:
    """Return the plain text of a resume, or raise :class:`ResumeParseError`."""
    extension = validate_upload(filename, data)

    text = _from_pdf(data) if extension == ".pdf" else _from_docx(data)
    text = _clean(text)

    if len(text) < config.MIN_RESUME_CHARS:
        raise ResumeParseError(
            "We could not read enough text from that resume. It may be empty, "
            "password protected, or a scanned image. Please upload a text-based "
            "PDF or DOCX file."
        )

    return text[: config.MAX_RESUME_CHARS]


# ---------------------------------------------------------------------------
# Format-specific readers
# ---------------------------------------------------------------------------
def _from_pdf(data: bytes) -> str:
    try:
        from PyPDF2 import PdfReader
        from PyPDF2.errors import PdfReadError
    except ImportError as exc:  # pragma: no cover - dependency check
        raise ResumeParseError(
            "PDF support is not installed. Run: python -m pip install PyPDF2"
        ) from exc

    try:
        reader = PdfReader(BytesIO(data))

        if getattr(reader, "is_encrypted", False):
            try:
                # Many resumes use an empty owner password.
                reader.decrypt("")
            except Exception:
                pass
            if getattr(reader, "is_encrypted", False):
                raise ResumeParseError(
                    "That PDF is password protected. Please upload an unlocked copy."
                )

        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pages.append("")  # one bad page must not fail the whole resume
        return "\n".join(pages)

    except ResumeParseError:
        raise
    except PdfReadError as exc:
        raise ResumeParseError(
            "That PDF looks damaged or is not a real PDF. Please upload a different file."
        ) from exc
    except Exception as exc:
        raise ResumeParseError(
            "We could not read that PDF. Please try exporting your resume again "
            "or upload a DOCX file instead."
        ) from exc


def _from_docx(data: bytes) -> str:
    try:
        import docx
    except ImportError as exc:  # pragma: no cover - dependency check
        raise ResumeParseError(
            "DOCX support is not installed. Run: python -m pip install python-docx"
        ) from exc

    try:
        document = docx.Document(BytesIO(data))
    except Exception as exc:
        raise ResumeParseError(
            "That DOCX looks damaged or is not a real Word document. "
            "Please upload a different file."
        ) from exc

    blocks = [paragraph.text for paragraph in document.paragraphs]

    # Skills are very often stored inside tables.
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                blocks.append(cell.text)

    # Contact details frequently live in the header/footer.
    for section in document.sections:
        for container in (section.header, section.footer):
            if container is None:
                continue
            for paragraph in container.paragraphs:
                blocks.append(paragraph.text)

    return "\n".join(blocks)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _clean(text: str) -> str:
    """Normalise line endings/whitespace so the model sees tidy text."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")

    lines = []
    blank_run = 0
    for raw_line in text.split("\n"):
        # Collapse runs of spaces/tabs (PDF extraction often adds many).
        line = " ".join(raw_line.split())
        if line:
            blank_run = 0
            lines.append(line)
        else:
            blank_run += 1
            if blank_run <= 1:  # keep single blank lines, drop the rest
                lines.append("")

    return "\n".join(lines).strip()


def _mb(num_bytes: int) -> str:
    return f"{num_bytes / (1024 * 1024):.1f}"
