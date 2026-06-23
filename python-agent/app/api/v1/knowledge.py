import io
from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from app.db.vector_store import VectorStore

router = APIRouter()

vector_store = VectorStore()


class UploadRequest(BaseModel):
    title: str
    content: str
    source_type: str = "text"


@router.post("/knowledge/upload")
async def upload(req: UploadRequest):
    doc_id = await vector_store.add_document(req.title, req.content, req.source_type)
    return {"code": 200, "msg": "success", "data": {"document_id": doc_id}}


def _extract_text(filename: str, content: bytes) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "docx":
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    if ext == "pdf":
        import fitz
        text_parts: list[str] = []
        with fitz.open(stream=content, filetype="pdf") as doc:
            for page in doc:
                text_parts.append(page.get_text())
        return "\n".join(text_parts)
    return content.decode("utf-8", errors="replace")


@router.post("/knowledge/upload-file")
async def upload_file(
    title: str = Form(...),
    source_type: str = Form("text"),
    file: UploadFile = File(...),
):
    filename = file.filename or "unknown"
    content = await file.read()
    text = _extract_text(filename, content)
    doc_id = await vector_store.add_document(title, text, source_type)
    return {"code": 200, "msg": "success", "data": {"document_id": doc_id}}


@router.get("/knowledge/documents")
async def list_documents():
    docs = await vector_store.list_sources()
    return {"code": 200, "msg": "success", "data": docs}


@router.delete("/knowledge/documents/{doc_id}")
async def delete_document(doc_id: int):
    ok = await vector_store.delete_document(doc_id)
    if ok:
        return {"code": 200, "msg": "success", "data": None}
    return {"code": 404, "msg": "document not found", "data": None}