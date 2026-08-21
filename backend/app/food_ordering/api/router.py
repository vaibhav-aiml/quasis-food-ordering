"""Aggregates food-ordering endpoint routers into one router."""

from fastapi import APIRouter
from app.food_ordering.api.endpoints import intent, plan, execution, restaurants, orders

food_router = APIRouter()
food_router.include_router(intent.router)
food_router.include_router(plan.router)
food_router.include_router(execution.router)
food_router.include_router(restaurants.router)
food_router.include_router(orders.orders_router)
food_router.include_router(orders.order_action_router)
