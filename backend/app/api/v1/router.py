from fastapi import APIRouter

from app.api.v1.events import router as events_router
from app.api.v1.operations import router as operations_router
from app.api.v1.reviews import router as reviews_router

router = APIRouter()
router.include_router(events_router)
router.include_router(reviews_router)
router.include_router(operations_router)
