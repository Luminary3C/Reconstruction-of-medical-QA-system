from fastapi import APIRouter
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