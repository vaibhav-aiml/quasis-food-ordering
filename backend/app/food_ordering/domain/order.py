"""Order lifecycle domain models for food ordering."""

from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """Lifecycle status of a food order."""

    PLACED = "placed"
    PREPARING = "preparing"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    STOPPED_AT_PAYMENT = "stopped_at_payment"


class OrderRecord(BaseModel):
    """Persistent record of a food order."""

    order_id: str = Field(min_length=1)
    plan_id: str | None = None
    user_id: str = Field(min_length=1)
    restaurant: str = Field(min_length=1)
    items: list[str] = Field(default_factory=list)
    status: OrderStatus = OrderStatus.PLACED
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    estimated_delivery: datetime | None = None
    current_step: str | None = None
    cancel_reason: str | None = None
