from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.routes_search import router as search_router
from backend.app.api.v1.routes_items import router as items_router
from backend.app.api.v1.routes_feedback import router as feedback_router

app = FastAPI(title="Memory Search MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router, prefix="/v1", tags=["search"])
app.include_router(items_router, prefix="/v1", tags=["items"])
app.include_router(feedback_router, prefix="/v1", tags=["feedback"])

@app.get("/healthz")
def healthz():
    return {"ok": True}
