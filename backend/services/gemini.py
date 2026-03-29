from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/producers/{producer_id}/advice")
def get_advice(producer_id: str):
    raise HTTPException(501, detail="Gemini advisor not implemented yet — P1 task")
