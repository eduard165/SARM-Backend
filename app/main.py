from fastapi import FastAPI
from app.api import auth, businesses, catalogs, system, users, livestock, summary, events, reports

app = FastAPI(title="SARM API", description="SARM V1 - FastAPI + Supabase", version="0.7.0")
for router in (system.router, auth.router, catalogs.router, businesses.router, users.router, livestock.router, summary.router, events.router, reports.router):
    app.include_router(router)

import time
@app.middleware('http')
async def timing(request,call_next):
    start=time.perf_counter();response=await call_next(request)
    prior=response.headers.get('Server-Timing')
    response.headers['Server-Timing']=(prior+', ' if prior else '')+f'app;dur={(time.perf_counter()-start)*1000:.1f}'
    response.headers['Cache-Control']='private, no-store'
    return response
