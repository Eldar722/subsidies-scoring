from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/simulate")
def simulate():
    raise HTTPException(501, detail="Not implemented yet — P1 task")
