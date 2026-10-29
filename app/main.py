from fastapi import FastAPI
from app.api import auth, businesses, catalogs, system, users, livestock, summary

app = FastAPI(title="SARM API", description="SARM V1 - FastAPI + Supabase", version="0.6.0")
for router in (system.router, auth.router, catalogs.router, businesses.router, users.router, livestock.router, summary.router):
    app.include_router(router)
