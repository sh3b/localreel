from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    # TODO: Add deep-health check instead
    return {"status": "ok"}
