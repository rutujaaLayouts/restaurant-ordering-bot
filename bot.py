"""Conversation logic: LLM understands the customer, Python validates the order and prices it."""
from __future__ import annotations

import csv
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .billing import Bill, calculate_bill
from .llm import LLMClient, LLMError
from .menu import Menu
from .prompts import build_system_prompt

MAX_QTY = 20
FALLBACK_REPLY = "Sorry, I did not get that. Could you please say your order again?"


@dataclass
class BotTurn:
    reply: str
    bill: Bill | None = None
    confirmed: bool = False
    order_id: str | None = None
    warnings: list[str] = field(default_factory=list)


def parse_llm_json(raw: str) -> dict:
    """Parse the LLM output safely (also handles ```json fences)."""
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("No JSON found in LLM output")
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("LLM output is not a JSON object")
    return data


class OrderingBot:
    def __init__(self, menu: Menu, llm: LLMClient, orders_file: str | Path = "orders.csv"):
        self.menu = menu
        self.llm = llm
        self.orders_file = Path(orders_file)
        self.reset()

    def reset(self) -> None:
        self.history: list[dict[str, str]] = []
        self.order: dict[str, int] = {}  # canonical menu name -> quantity
        self.bill_shown = False
        self.finished = False

    def current_bill(self) -> Bill | None:
        return calculate_bill(self.order, self.menu) if self.order else None

    @staticmethod
    def greeting() -> str:
        return ("Welcome to Spice Route! I can take your order from our menu. "
                "What would you like today?")

    def handle(self, user_text: str) -> BotTurn:
        if self.finished:
            return BotTurn("This order is already confirmed. Please start a new order.")
        user_text = user_text.strip()
        if not user_text:
            return BotTurn("Please type your order.")

        self.history.append({"role": "user", "content": user_text})
        system_prompt = build_system_prompt(self.menu.as_prompt_text(), self.order)
        try:
            data = parse_llm_json(self.llm.generate(system_prompt, self.history))
        except LLMError:
            self.history.pop()
            raise
        except ValueError:  # includes json.JSONDecodeError
            self.history.pop()
            return BotTurn(FALLBACK_REPLY, self.current_bill())

        reply = str(data.get("reply", "")).strip() or FALLBACK_REPLY
        warnings: list[str] = []
        self.order = self._validate_order(data.get("order"), warnings)

        bill = self.current_bill()
        order_id, confirmed = None, False
        if data.get("confirm") is True and bill and self.bill_shown:
            order_id = self._save_order(bill)
            confirmed = self.finished = True
        elif bill:
            self.bill_shown = True

        self.history.append({"role": "assistant", "content": reply})
        return BotTurn(reply, bill, confirmed, order_id, warnings)

    def _validate_order(self, raw_order, warnings: list[str]) -> dict[str, int]:
        """Keep only real menu items with a sane quantity. Never trust the LLM blindly."""
        if not isinstance(raw_order, list):
            return dict(self.order)
        clean: dict[str, int] = {}
        for entry in raw_order:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("item", ""))
            item = self.menu.find(name)
            if item is None:
                warnings.append(f"'{name}' is not on our menu, so it was not added.")
                continue
            try:
                qty = int(entry.get("quantity", 0))
            except (TypeError, ValueError):
                continue
            if qty < 1:
                continue
            if qty > MAX_QTY:
                warnings.append(f"Maximum {MAX_QTY} per item. {item.name} set to {MAX_QTY}.")
                qty = MAX_QTY
            clean[item.name] = min(clean.get(item.name, 0) + qty, MAX_QTY)
        return clean

    def _save_order(self, bill: Bill) -> str:
        order_id = "ORD-" + uuid.uuid4().hex[:6].upper()
        new_file = not self.orders_file.exists()
        with self.orders_file.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(["order_id", "time", "items", "subtotal", "gst", "total"])
            items = "; ".join(f"{l.item} x{l.quantity}" for l in bill.lines)
            w.writerow([order_id, datetime.now().isoformat(timespec="seconds"),
                        items, bill.subtotal, bill.gst, bill.total])
        return order_id
