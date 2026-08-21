"""Restaurant and Menu domain models for food ordering."""

from pydantic import BaseModel, Field


class CustomizationOption(BaseModel):
    """A single add-on or option within a customization group."""

    option_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    price_delta_inr: float = Field(default=0.0, ge=0.0)
    in_stock: bool = True


class CustomizationGroup(BaseModel):
    """A group of customizations e.g., 'Choose Portion', 'Choice of Raita', 'Add-ons'."""

    group_id: str = Field(min_length=1)
    group_name: str = Field(min_length=1)
    min_selection: int = Field(default=0, ge=0)
    max_selection: int = Field(default=1, ge=1)
    options: list[CustomizationOption] = Field(default_factory=list)


class MenuItem(BaseModel):
    """A dish / item in a restaurant's catalog."""

    item_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None
    price_inr: float = Field(gt=0.0)
    is_veg: bool = False
    customization_groups: list[CustomizationGroup] = Field(default_factory=list)
    in_stock: bool = True


class Restaurant(BaseModel):
    """Restaurant metadata and catalog."""

    restaurant_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    rating: float | None = Field(default=None, ge=0.0, le=5.0)
    eta_minutes: int | None = Field(default=None, ge=1)
    cuisines: list[str] = Field(default_factory=list)
    address: str | None = None
    is_open: bool = True
    menu: list[MenuItem] = Field(default_factory=list)
