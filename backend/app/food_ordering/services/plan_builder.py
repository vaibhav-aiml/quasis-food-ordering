"""Deterministic OrderPlan Builder for Food Ordering.

Translates a structured, validated FoodOrderIntent into a sequence of
OrderStep commands tailored for execution by the Android AccessibilityService.
"""

import uuid
from app.food_ordering.domain.intent import FoodOrderIntent
from app.food_ordering.domain.plan import (
    ExecutionStepType,
    OrderPlan,
    OrderStep,
)


class FoodPlanBuilder:
    """Compiles a FoodOrderIntent into an executable OrderPlan."""

    def build_plan(self, intent: FoodOrderIntent) -> OrderPlan:
        """Construct deterministic execution steps from validated intent.

        Args:
            intent: A validated FoodOrderIntent.

        Returns:
            A complete OrderPlan with sequential OrderStep items and
            a hard stop before payment confirmation.
        """
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        steps: list[OrderStep] = []
        step_counter = 1

        # Step 1: Launch target application (non-critical fallback so execution proceeds smoothly)
        app_pkg = (
            "in.swiggy.android"
            if intent.target_app == "swiggy"
            else "com.application.zomato"
        )
        steps.append(
            OrderStep(
                step_id=step_counter,
                step_type=ExecutionStepType.LAUNCH_APP,
                target_value=intent.target_app,
                parameters={"package_name": app_pkg},
                expected_screen="home",
                timeout_seconds=15,
                is_critical=False,
            )
        )
        step_counter += 1

        # Step 2: Search & Select Restaurant (if specified)
        if intent.restaurant_name:
            steps.append(
                OrderStep(
                    step_id=step_counter,
                    step_type=ExecutionStepType.SEARCH_RESTAURANT,
                    target_value=intent.restaurant_name,
                    parameters={"query": intent.restaurant_name},
                    expected_screen="home_search",
                    timeout_seconds=10,
                    is_critical=True,
                )
            )
            step_counter += 1

            steps.append(
                OrderStep(
                    step_id=step_counter,
                    step_type=ExecutionStepType.SELECT_RESTAURANT,
                    target_value=intent.restaurant_name,
                    parameters={"restaurant_name": intent.restaurant_name},
                    expected_screen="search_results",
                    timeout_seconds=12,
                    is_critical=True,
                )
            )
            step_counter += 1

        # Step 3: Iterate through dishes / food items
        for item in intent.items:
            # 3a. Search item inside restaurant menu (non-critical helper)
            steps.append(
                OrderStep(
                    step_id=step_counter,
                    step_type=ExecutionStepType.SEARCH_MENU_ITEM,
                    target_value=item.name,
                    parameters={"item_name": item.name},
                    expected_screen="restaurant_menu",
                    timeout_seconds=8,
                    is_critical=False,
                )
            )
            step_counter += 1

            # 3b. Select item
            steps.append(
                OrderStep(
                    step_id=step_counter,
                    step_type=ExecutionStepType.SELECT_ITEM,
                    target_value=item.name,
                    parameters={"item_name": item.name, "quantity": item.quantity},
                    expected_screen="restaurant_menu",
                    timeout_seconds=10,
                    is_critical=True,
                )
            )
            step_counter += 1

            # 3c. Apply customizations if requested
            if item.customizations or item.portion_or_size:
                steps.append(
                    OrderStep(
                        step_id=step_counter,
                        step_type=ExecutionStepType.APPLY_CUSTOMIZATION,
                        target_value=item.name,
                        parameters={
                            "item_name": item.name,
                            "portion": item.portion_or_size,
                            "customizations": item.customizations,
                        },
                        expected_screen="customization_sheet",
                        timeout_seconds=10,
                        is_critical=False,
                    )
                )
                step_counter += 1

            # 3d. Add to Cart
            steps.append(
                OrderStep(
                    step_id=step_counter,
                    step_type=ExecutionStepType.ADD_TO_CART,
                    target_value=item.name,
                    parameters={"quantity": item.quantity},
                    expected_screen="customization_sheet_or_menu",
                    timeout_seconds=10,
                    is_critical=True,
                )
            )
            step_counter += 1

        # Step 4: Cart and Checkout navigation (only if items were added)
        if intent.items:
            steps.append(
                OrderStep(
                    step_id=step_counter,
                    step_type=ExecutionStepType.VIEW_CART,
                    target_value="cart",
                    parameters={},
                    expected_screen="floating_cart_or_menu",
                    timeout_seconds=10,
                    is_critical=True,
                )
            )
            step_counter += 1

            steps.append(
                OrderStep(
                    step_id=step_counter,
                    step_type=ExecutionStepType.PROCEED_TO_CHECKOUT,
                    target_value="checkout",
                    parameters={},
                    expected_screen="cart_summary",
                    timeout_seconds=15,
                    is_critical=True,
                )
            )
            step_counter += 1

            # CRITICAL SAFETY STEP: Hard stop before payment
            steps.append(
                OrderStep(
                    step_id=step_counter,
                    step_type=ExecutionStepType.STOP_FOR_PAYMENT,
                    target_value="payment",
                    parameters={"safety_enforced": True},
                    expected_screen="payment_options",
                    timeout_seconds=5,
                    is_critical=True,
                )
            )

        return OrderPlan(
            plan_id=plan_id,
            target_app=intent.target_app,
            restaurant_name=intent.restaurant_name,
            items=intent.items,
            steps=steps,
            stop_before_payment=True,
        )
