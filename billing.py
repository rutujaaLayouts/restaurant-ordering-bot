"""Bill calculation. All maths is done here in Python, never by the LLM."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .menu import Menu

GST_RATE = Decimal("0.05")  # 5% GST
TWO = Decimal("0.01")


@dataclass(frozen=True)
class BillLine:
    item: str
    quantity: int
    unit_price: Decimal
    amount: Decimal


@dataclass(frozen=True)
class Bill:
    lines: list[BillLine]
    subtotal: Decimal
    gst: Decimal
    total: Decimal


def calculate_bill(order: dict[str, int], menu: Menu, gst_rate: Decimal = GST_RATE) -> Bill:
    """order maps menu item name -> quantity."""
    lines = []
    for name, qty in order.items():
        item = menu.items[name.lower()]
        lines.append(BillLine(item.name, qty, item.price, (item.price * qty).quantize(TWO)))
    subtotal = sum((l.amount for l in lines), Decimal("0.00"))
    gst = (subtotal * gst_rate).quantize(TWO, rounding=ROUND_HALF_UP)
    return Bill(lines, subtotal, gst, subtotal + gst)
