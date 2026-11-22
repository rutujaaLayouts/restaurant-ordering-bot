"""Menu loading and item matching."""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class MenuItem:
    category: str
    name: str
    price: Decimal


class Menu:
    """Holds menu items loaded from a CSV (columns: category, item, price)."""

    def __init__(self, items: list[MenuItem]):
        if not items:
            raise ValueError("Menu is empty.")
        self.items = {i.name.lower(): i for i in items}

    @classmethod
    def from_csv(cls, path: str | Path) -> "Menu":
        df = pd.read_csv(path)
        missing = {"category", "item", "price"} - set(df.columns)
        if missing:
            raise ValueError(f"menu CSV is missing columns: {sorted(missing)}")
        items = [
            MenuItem(str(r.category).strip(), str(r.item).strip(), Decimal(str(r.price)))
            for r in df.itertuples()
        ]
        return cls(items)

    def find(self, name: str) -> MenuItem | None:
        """Exact match (ignoring case) first, then a close spelling match."""
        key = (name or "").strip().lower()
        if key in self.items:
            return self.items[key]
        close = difflib.get_close_matches(key, list(self.items), n=1, cutoff=0.8)
        return self.items[close[0]] if close else None

    def as_prompt_text(self) -> str:
        """Menu as plain text for the LLM prompt (prices are for reading only)."""
        lines, last = [], None
        for item in self.items.values():
            if item.category != last:
                lines.append(f"\n{item.category}:")
                last = item.category
            lines.append(f"- {item.name} (Rs {item.price})")
        return "\n".join(lines).strip()

    def by_category(self) -> dict[str, list[MenuItem]]:
        grouped: dict[str, list[MenuItem]] = {}
        for item in self.items.values():
            grouped.setdefault(item.category, []).append(item)
        return grouped
