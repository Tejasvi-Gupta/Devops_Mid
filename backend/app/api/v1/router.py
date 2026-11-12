from fastapi import APIRouter

from app.api.v1 import admin, agent, auth, platform

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(auth.users)
api_router.include_router(platform.router)
api_router.include_router(agent.router)
api_router.include_router(admin.router)
api_router.include_router(admin.health)
