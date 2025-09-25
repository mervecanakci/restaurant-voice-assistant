import os
import json
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import httpx

from app.db.init_db import init_db
from app.api.restaurants import router as restaurants_router
from app.api.menu_items import router as menu_router
from app.api.orders import router as orders_router
from app.api.wallet import router as wallet_router
from app.api.auth import router as auth_router
from app.websocket_realtime import router as realtime_router

app = FastAPI(title="Restaurant Ordering API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(auth_router)
app.include_router(restaurants_router)
app.include_router(menu_router)
app.include_router(orders_router)
app.include_router(wallet_router)
app.include_router(realtime_router)
