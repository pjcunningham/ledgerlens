from dataclasses import dataclass, field
from typing import Literal

type Json = None | bool | int | float | str | list[Json] | dict[str, Json]
type Status = Literal["supported", "unsupported", "failed", "not-tested"]


@dataclass
class Observation:
    operation: str
    status: Status
    sqlstate: str | None = None
    details: dict[str, Json] = field(default_factory=dict)


@dataclass
class Column:
    name: str
    odbc_type: int | None
    type_name: str | None
    size: int | None
    scale: int | None
    nullable: int | None
    ordinal: int | None
    precision: int | None = None
    buffer_length: int | None = None


@dataclass
class Table:
    name: str
    kind: str
    columns: list[Column] = field(default_factory=list)
    metadata: list[Observation] = field(default_factory=list)


@dataclass
class Schema:
    tables: list[Table]
    observations: list[Observation] = field(default_factory=list)


@dataclass(frozen=True)
class Link:
    left_table: str
    left_column: str
    right_table: str
    right_column: str


PRIORITY_TABLES = (
    "SALES_LEDGER",
    "SALES_CONTACT",
    "SALES_DEL_ADDR",
    "PURCHASE_LEDGER",
    "PURCHASE_CONTACT",
    "PURCHASE_DEL_ADDR",
    "STOCK",
    "STOCK_TRAN",
    "PRICE_LIST",
    "INVOICE",
    "INVOICE_ITEM",
    "SALES_ORDER",
    "SOP_ITEM",
    "PURCHASE_ORDER",
    "POP_ITEM",
    "AUDIT_HEADER",
    "AUDIT_SPLIT",
    "AUDIT_JOURNAL",
    "AUDIT_USAGE",
    "AUDIT_VAT",
    "NOMINAL_LEDGER",
)
KEYS = {
    "ACCOUNT_REF",
    "INVOICE_NUMBER",
    "ORDER_NUMBER",
    "STOCK_CODE",
    "HEADER_NUMBER",
    "SPLIT_NUMBER",
}
FLAGS = {"DELETED_FLAG", "DATE_FLAG", "ACTIVE", "INACTIVE", "RECORD_DELETED"}
LINKS = (
    Link("INVOICE", "ACCOUNT_REF", "SALES_LEDGER", "ACCOUNT_REF"),
    Link("INVOICE", "INVOICE_NUMBER", "INVOICE_ITEM", "INVOICE_NUMBER"),
    Link("SALES_ORDER", "ACCOUNT_REF", "SALES_LEDGER", "ACCOUNT_REF"),
    Link("SALES_ORDER", "ORDER_NUMBER", "SOP_ITEM", "ORDER_NUMBER"),
    Link("SOP_ITEM", "STOCK_CODE", "STOCK", "STOCK_CODE"),
    Link("PURCHASE_ORDER", "ACCOUNT_REF", "PURCHASE_LEDGER", "ACCOUNT_REF"),
    Link("PURCHASE_ORDER", "ORDER_NUMBER", "POP_ITEM", "ORDER_NUMBER"),
    Link("POP_ITEM", "STOCK_CODE", "STOCK", "STOCK_CODE"),
    Link("SALES_LEDGER", "ACCOUNT_REF", "AUDIT_HEADER", "ACCOUNT_REF"),
    Link("PURCHASE_LEDGER", "ACCOUNT_REF", "AUDIT_HEADER", "ACCOUNT_REF"),
    Link("NOMINAL_LEDGER", "ACCOUNT_REF", "AUDIT_SPLIT", "NOMINAL_CODE"),
    Link("AUDIT_HEADER", "HEADER_NUMBER", "AUDIT_JOURNAL", "HEADER_NUMBER"),
)
