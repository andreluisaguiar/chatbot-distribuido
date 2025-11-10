from fastapi import APIRouter # type: ignore

router = APIRouter()

# Rota temporária para evitar o erro de importação
@router.get("/simple-status")
async def get_simple_status():
    return {"status": "chat module ativo"}