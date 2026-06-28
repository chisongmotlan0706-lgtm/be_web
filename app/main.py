from fastapi import Depends, FastAPI

from app.auth import get_current_user
from app.routers.commission_config import router as commission_config_router
from app.routers.commission_import import router as commission_import_router
from app.routers.withdraw_requests_duplicate import router as withdraw_requests_duplicate_router
from app.routers.commission_split_config import router as commission_split_config_router
from app.routers.app_config_kv import router as app_config_kv_router
from app.routers.auth import router as auth_router
from app.routers.zalo_groups import router as zalo_groups_router
from app.routers.bot_registry import router as bot_registry_router
from app.routers.aff_bot import router as aff_bot_router

app = FastAPI(title="Supabase Convert Results API")


@app.get("/")
def health_check():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(commission_import_router, dependencies=[Depends(get_current_user)])
app.include_router(withdraw_requests_duplicate_router, dependencies=[Depends(get_current_user)])
app.include_router(commission_config_router, dependencies=[Depends(get_current_user)])
app.include_router(commission_split_config_router, dependencies=[Depends(get_current_user)])
app.include_router(app_config_kv_router, dependencies=[Depends(get_current_user)])
app.include_router(zalo_groups_router, dependencies=[Depends(get_current_user)])
app.include_router(bot_registry_router, dependencies=[Depends(get_current_user)])
app.include_router(aff_bot_router, dependencies=[Depends(get_current_user)])
