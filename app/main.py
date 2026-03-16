from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="Incident Postmortem Agent")
app.include_router(router)