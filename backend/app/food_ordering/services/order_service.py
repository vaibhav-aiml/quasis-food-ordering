"""In-memory order management service for food ordering.

Provides order history, tracking, and cancellation. Uses an in-memory
dict store seeded with sample data — swap for a database in production.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.food_ordering.domain.order import OrderRecord, OrderStatus

_logger = logging.getLogger("app.food_ordering.services.order")

# States from which cancellation is allowed
_CANCELLABLE_STATUSES = {OrderStatus.PLACED, OrderStatus.PREPARING}


def _build_seed_orders() -> list[OrderRecord]:
    """Build sample order history for testing."""
    now = datetime.now(timezone.utc)
    return [
        OrderRecord(
            order_id="order_001",
            plan_id="plan_sample_001",
            user_id="user_1",
            restaurant="Meghana Foods",
            items=["Chicken Biryani", "Extra Raita"],
            status=OrderStatus.DELIVERED,
            timestamp=now - timedelta(days=2),
            estimated_delivery=now - timedelta(days=2, hours=-1),
            current_step="Delivered",
        ),
        OrderRecord(
            order_id="order_002",
            plan_id="plan_sample_002",
            user_id="user_1",
            restaurant="Saravana Bhavan",
            items=["Masala Dosa", "Filter Coffee"],
            status=OrderStatus.DELIVERED,
            timestamp=now - timedelta(days=1),
            estimated_delivery=now - timedelta(days=1, hours=-1),
            current_step="Delivered",
        ),
        OrderRecord(
            order_id="order_003",
            plan_id="plan_sample_003",
            user_id="user_1",
            restaurant="Cafe Coffee Day",
            items=["Cappuccino"],
            status=OrderStatus.PREPARING,
            timestamp=now - timedelta(minutes=15),
            estimated_delivery=now + timedelta(minutes=20),
            current_step="Restaurant preparing food",
        ),
        OrderRecord(
            order_id="order_004",
            plan_id="plan_sample_004",
            user_id="user_2",
            restaurant="Paradise Biryani",
            items=["Chicken Biryani"],
            status=OrderStatus.OUT_FOR_DELIVERY,
            timestamp=now - timedelta(minutes=45),
            estimated_delivery=now + timedelta(minutes=10),
            current_step="Delivery partner on the way",
        ),
    ]


class OrderService:
    """Manages order history, tracking, and cancellation."""

    def __init__(self) -> None:
        self._store: dict[str, OrderRecord] = {}
        for order in _build_seed_orders():
            self._store[order.order_id] = order

    def get_history(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[OrderRecord]:
        """Return order history for a user, most recent first.

        Args:
            user_id: User identifier.
            limit: Maximum number of orders to return.
        """
        user_orders = [
            o for o in self._store.values()
            if o.user_id == user_id
        ]
        user_orders.sort(key=lambda o: o.timestamp, reverse=True)
        return user_orders[:limit]

    def track_order(self, order_id: str) -> OrderRecord:
        """Get current tracking state of an order.

        Raises:
            KeyError: If order_id is not found.
        """
        order = self._store.get(order_id)
        if order is None:
            raise KeyError(f"Order '{order_id}' not found")
        return order

    def cancel_order(self, order_id: str, reason: str) -> OrderRecord:
        """Cancel an in-progress order.

        Only orders in PLACED or PREPARING status can be cancelled.

        Args:
            order_id: Order identifier.
            reason: User-provided cancellation reason.

        Returns:
            Updated OrderRecord with CANCELLED status.

        Raises:
            KeyError: If order_id is not found.
            ValueError: If order is not in a cancellable state.
        """
        order = self._store.get(order_id)
        if order is None:
            raise KeyError(f"Order '{order_id}' not found")

        if order.status not in _CANCELLABLE_STATUSES:
            raise ValueError(
                f"Order '{order_id}' cannot be cancelled (status: {order.status.value})"
            )

        order.status = OrderStatus.CANCELLED
        order.cancel_reason = reason
        order.current_step = "Cancelled"
        _logger.info(
            "order_cancelled",
            extra={"order_id": order_id, "reason": reason},
        )
        return order
