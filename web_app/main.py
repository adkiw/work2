from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from web_app.auth import AuthMiddleware, router as auth_router
from web_app.routers import router as api_router

import os

app = FastAPI()
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("WEBAPP_SECRET", "devsecret"))

app.mount("/static", StaticFiles(directory="web_app/static"), name="static")

app.include_router(auth_router)
app.include_router(api_router)
