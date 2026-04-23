from fastapi import FastAPI

from app.routers.commission_config import router as commission_config_router
from app.routers.commission_import import router as commission_import_router
from app.routers.getorder import router as getorder_router

app = FastAPI(title="Supabase Convert Results API")


@app.get("/")
def health_check():
    return {"status": "ok"}


app.include_router(getorder_router)
app.include_router(commission_import_router)
app.include_router(commission_config_router)
