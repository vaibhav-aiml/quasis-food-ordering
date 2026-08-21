"""Order management endpoints for food ordering.

API 5: GET  /orders/history            — User order history.
API 6: GET  /orders/{order_id}/track   — Live order tracking.
API 7: POST /order/cancel              — Cancel an in-progress order.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.dependencies import get_order_service
from app.food_ordering.services.order_service import OrderService

# Two routers: one for /orders (collection) and one for /order (singleton actions)
orders_router = APIRouter(prefix="/orders", tags=["food-orders"])
order_action_router = APIRouter(prefix="/order", tags=["food-orders"])


# -- Response models ----------------------------------------------------------


class OrderHistoryItem(BaseModel):
    """Single order in the history list."""

    id: str
    restaurant: str
    items: list[str]
    status: str
    timestamp: str


class OrderHistoryResponse(BaseModel):
    """Response payload for order history."""

    orders: list[OrderHistoryItem]


class TrackOrderResponse(BaseModel):
    """Response payload for order tracking."""

    order_id: str
    status: str
    estimated_delivery: str | None
    current_step: str | None


class CancelRequest(BaseModel):
    """Request payload for order cancellation."""

    order_id: str = Field(min_length=1, description="ID of the order to cancel.")
    reason: str = Field(min_length=1, description="Cancellation reason.")


class CancelResponse(BaseModel):
    """Response payload for order cancellation."""

    order_id: str
    status: str
    message: str


# -- Endpoints ----------------------------------------------------------------


@orders_router.get("/history", response_model=OrderHistoryResponse, status_code=200)
def get_order_history(
    service: Annotated[OrderService, Depends(get_order_service)],
    user_id: str = Query(description="User identifier"),
    limit: int = Query(default=10, ge=1, le=100, description="Max orders to return"),
) -> OrderHistoryResponse:
    """Get a user's past order history, most recent first."""
    records = service.get_history(user_id=user_id, limit=limit)
    items = [
        OrderHistoryItem(
            id=r.order_id,
            restaurant=r.restaurant,
            items=r.items,
            status=r.status.value,
            timestamp=r.timestamp.isoformat(),
        )
        for r in records
    ]
    return OrderHistoryResponse(orders=items)


@orders_router.get("/{order_id}/track", response_model=TrackOrderResponse, status_code=200)
def track_order(
    order_id: str,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> TrackOrderResponse:
    """Track the current status of a placed order."""
    try:
        record = service.track_order(order_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found")

    return TrackOrderResponse(
        order_id=record.order_id,
        status=record.status.value,
        estimated_delivery=record.estimated_delivery.isoformat() if record.estimated_delivery else None,
        current_step=record.current_step,
    )


@order_action_router.post("/cancel", response_model=CancelResponse, status_code=200)
def cancel_order(
    payload: CancelRequest,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> CancelResponse:
    """Cancel an in-progress order.

    Only orders in ``placed`` or ``preparing`` status can be cancelled.
    Returns 404 if order not found, 409 if order is not in a cancellable state.
    """
    try:
        record = service.cancel_order(order_id=payload.order_id, reason=payload.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Order '{payload.order_id}' not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return CancelResponse(
        order_id=record.order_id,
        status=record.status.value,
        message="Order cancelled successfully",
    )
