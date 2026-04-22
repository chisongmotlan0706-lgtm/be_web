from fastapi import FastAPI

from app.routers.getorder import router as getorder_router

app = FastAPI(title="Supabase Convert Results API")


@app.get("/")
def health_check():
    return {"status": "ok"}


app.include_router(getorder_router)
