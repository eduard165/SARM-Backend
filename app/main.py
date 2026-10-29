from fastapi import FastAPI
from app.api import auth, businesses, catalogs, system, users, livestock

app = FastAPI(title="SARM API", description="SARM V1 - FastAPI + Supabase", version="0.5.0")
for router in (system.router, auth.router, catalogs.router, businesses.router, users.router, livestock.router):
    app.include_router(router)
