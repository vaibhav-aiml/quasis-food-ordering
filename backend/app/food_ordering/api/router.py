"""Aggregates food-ordering endpoint routers into one router."""

from fastapi import APIRouter
from app.food_ordering.api.endpoints import intent, plan

food_router = APIRouter()
food_router.include_router(intent.router)
food_router.include_router(plan.router)
