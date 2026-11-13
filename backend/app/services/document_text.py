"""Extract plain text from teacher-uploaded slides and notes (PDF, DOCX, PPTX).

Used as reference material for AI quiz generation. The text is data only; it is
never treated as instructions (see ai_quiz.SYSTEM_PROMPT).
"""
import io
import re
import zipfile
import xml.etree.ElementTree as ET

from app.services.question_bank import QuestionParseError, _docx_paragraphs

MAX_EXTRACTED_CHARS = 30000          # what is sent to the model
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024   # zip-bomb guard for DOCX/PPTX
MAX_PDF_PAGES = 200

_PPTX_TEXT_TAG = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"
_PPTX_SLIDE = re.compile(r"^ppt/slides/slide(\d+)\.xml$")


def _check_zip_size(zf: zipfile.ZipFile) -> None:
    total = sum(info.file_size for info in zf.infolist())
    if total > MAX_UNCOMPRESSED_BYTES:
        raise QuestionParseError("This file expands to too much data to be a normal document.")


def _pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise QuestionParseError(
            "PDF support is not installed on the server. Ask the administrator to run "
            "pip install -r requirements.txt, or upload a DOCX or PPTX instead."
        ) from exc
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise QuestionParseError("Password-protected PDFs cannot be read. Remove the password and try again.")
        pages = reader.pages[:MAX_PDF_PAGES]
        return "\n".join((page.extract_text() or "") for page in pages)
    except QuestionParseError:
        raise
    except Exception as exc:
        raise QuestionParseError("This PDF could not be read. Check that the file is not damaged.") from exc


def _docx_text(content: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            _check_zip_size(zf)
        return "\n".join(p for p in _docx_paragraphs(content) if p)
    except zipfile.BadZipFile as exc:
        raise QuestionParseError("This DOCX file could not be read.") from exc
    except ET.ParseError as exc:
        raise QuestionParseError("This DOCX file could not be read.") from exc


def _pptx_text(content: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            _check_zip_size(zf)
            slides = []
            for name in zf.namelist():
                m = _PPTX_SLIDE.match(name)
                if m:
                    slides.append((int(m.group(1)), name))
            slides.sort()
            parts = []
            for number, name in slides:
                root = ET.fromstring(zf.read(name))
                lines = []
                for para in root.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}p"):
                    text = "".join(t.text or "" for t in para.iter(_PPTX_TEXT_TAG)).strip()
                    if text:
                        lines.append(text)
                if lines:
                    parts.append(f"Slide {number}:\n" + "\n".join(lines))
            return "\n\n".join(parts)
    except (zipfile.BadZipFile, ET.ParseError, KeyError) as exc:
        raise QuestionParseError("This PPTX file could not be read.") from exc


def extract_text(filename: str, content: bytes) -> str:
    """Return the readable text of an uploaded file, capped at MAX_EXTRACTED_CHARS.

    Raises QuestionParseError with a message that is safe to show the teacher.
    """
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        text = _pdf_text(content)
    elif name.endswith(".docx"):
        text = _docx_text(content)
    elif name.endswith(".pptx"):
        text = _pptx_text(content)
    else:
        raise QuestionParseError("Upload a PDF, DOCX or PPTX file.")

    text = re.sub(r"[ \t]+", " ", text).strip()
    if len(text) < 50:
        raise QuestionParseError(
            "No readable text was found in this file. Scanned or image-only slides are not supported."
        )
    return text[:MAX_EXTRACTED_CHARS]
