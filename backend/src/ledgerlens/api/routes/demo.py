from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/demo", tags=["temporary foundation demo"])
SortField = Literal["id", "account_ref", "name", "balance", "active"]


class DemoCustomer(BaseModel):
    """Synthetic presentation data, not a canonical accounting model."""

    model_config = ConfigDict(frozen=True)
    id: int
    account_ref: str
    name: str
    balance: float
    active: bool


class SortDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    selector: SortField
    desc: bool = False


class GridLoadOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    skip: int = Field(default=0, ge=0, le=1_000_000)
    take: int = Field(default=25, ge=1, le=100)
    requireTotalCount: bool = False
    sort: list[SortDescriptor] = Field(default_factory=list, max_length=5)
    # DevExtreme can send an inactive filter as null. Expressions remain unsupported.
    filter: None = None


class GridRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    loadOptions: GridLoadOptions


class GridResult(BaseModel):
    data: list[DemoCustomer]
    totalCount: int | None = None


DEMO_CUSTOMERS = tuple(
    DemoCustomer(
        id=index,
        account_ref=f"DEMO{index:04d}",
        name=f"Demo Customer {index:03d}",
        balance=((index * 7919) % 200_000 - 20_000) / 100,
        active=index % 4 != 0,
    )
    for index in range(1, 101)
)

SORT_KEYS: dict[SortField, Callable[[DemoCustomer], int | str | float]] = {
    "id": lambda row: row.id,
    "account_ref": lambda row: row.account_ref,
    "name": lambda row: row.name,
    "balance": lambda row: row.balance,
    "active": lambda row: row.active,
}


@router.post("/customers/grid", response_model=GridResult, response_model_exclude_none=True)
def customer_grid(request: GridRequest) -> GridResult:
    options = request.loadOptions
    # Stable sorts preserve id ASC as the final tie-breaker for reproducible pages.
    rows = list(DEMO_CUSTOMERS)
    for descriptor in reversed(options.sort):
        rows.sort(key=SORT_KEYS[descriptor.selector], reverse=descriptor.desc)
    return GridResult(
        data=rows[options.skip : options.skip + options.take],
        totalCount=len(rows) if options.requireTotalCount else None,
    )
