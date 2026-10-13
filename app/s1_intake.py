from __future__ import annotations

import base64
import io
import os
import tempfile
from app.schemas import Attachment
from app.trace import TraceCollector


def process_attachments(attachments: list[Attachment], trace: TraceCollector | None = None) -> list[dict]:
    results = []
    llm = None
    try:
        from app.llm import get_llm_client
        llm = get_llm_client()
    except Exception:
        pass
    for att in attachments:
        content = base64.b64decode(att.content_base64)
        ext = (att.file_name or "").lower()
        text = ""
        if ext.endswith(".pdf"):
            text = _extract_pdf(content)
        elif ext.endswith(".docx"):
            text = _extract_docx(content)
        elif ext.endswith((".jpg", ".jpeg", ".png", ".tiff", ".bmp")):
            if llm:
                text = llm.generate_vision("Transcribe all visible text from this document.", content, att.content_type or "image/jpeg", trace)
            else:
                text = "[Image attachment - LLM not available for OCR]"
        else:
            text = f"[Unsupported attachment type: {att.content_type}]"
        results.append({"file_name": att.file_name, "text": text, "content_type": att.content_type})
    return results


def _extract_pdf(content: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        return "[PDF extraction failed]"


def _extract_docx(content: bytes) -> str:
    try:
        from docx import Document
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        doc = Document(tmp_path)
        os.unlink(tmp_path)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return "[DOCX extraction failed]"