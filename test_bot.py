"""Offline tests: a fake LLM is used, so no API key or internet is needed."""
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from restaurant_bot.billing import calculate_bill  # noqa: E402
from restaurant_bot.bot import OrderingBot, parse_llm_json  # noqa: E402
from restaurant_bot.menu import Menu  # noqa: E402

MENU_CSV = Path(__file__).resolve().parents[1] / "data" / "menu.csv"


class FakeLLM:
    """Returns scripted JSON answers, one per call."""

    def __init__(self, *answers):
        self.answers = list(answers)

    def generate(self, system_prompt, history):
        a = self.answers.pop(0)
        return a if isinstance(a, str) else json.dumps(a)


@pytest.fixture
def menu():
    return Menu.from_csv(MENU_CSV)


def make_bot(menu, tmp_path, *answers):
    return OrderingBot(menu, FakeLLM(*answers), tmp_path / "orders.csv")


def test_bill_is_calculated_by_python(menu):
    bill = calculate_bill({"Butter Naan": 2, "Paneer Butter Masala": 1}, menu)
    assert bill.subtotal == Decimal("350.00")
    assert bill.gst == Decimal("17.50")
    assert bill.total == Decimal("367.50")


def test_menu_fuzzy_match(menu):
    assert menu.find("butter nan").name == "Butter Naan"
    assert menu.find("pizza") is None


def test_order_is_added_and_priced(menu, tmp_path):
    bot = make_bot(menu, tmp_path, {"reply": "Added!", "order": [{"item": "Butter Naan", "quantity": 2}], "confirm": False})
    turn = bot.handle("2 butter naan")
    assert bot.order == {"Butter Naan": 2}
    assert turn.bill.total == Decimal("94.50")


def test_item_not_on_menu_is_rejected(menu, tmp_path):
    bot = make_bot(menu, tmp_path, {"reply": "ok", "order": [{"item": "Pizza", "quantity": 1}], "confirm": False})
    turn = bot.handle("one pizza")
    assert bot.order == {} and turn.bill is None
    assert "not on our menu" in turn.warnings[0]


def test_quantity_limit_and_bad_values(menu, tmp_path):
    bot = make_bot(menu, tmp_path, {"reply": "ok", "order": [
        {"item": "Masala Chai", "quantity": 500}, {"item": "Dal Tadka", "quantity": "abc"},
        {"item": "Ice Cream", "quantity": -1}], "confirm": False})
    bot.handle("lots of chai")
    assert bot.order == {"Masala Chai": 20}


def test_remove_item(menu, tmp_path):
    bot = make_bot(menu, tmp_path,
                   {"reply": "ok", "order": [{"item": "Dal Tadka", "quantity": 1}, {"item": "Jeera Rice", "quantity": 1}], "confirm": False},
                   {"reply": "removed", "order": [{"item": "Dal Tadka", "quantity": 1}], "confirm": False})
    bot.handle("dal and rice")
    bot.handle("remove rice")
    assert bot.order == {"Dal Tadka": 1}


def test_confirm_saves_order_after_bill_shown(menu, tmp_path):
    bot = make_bot(menu, tmp_path,
                   {"reply": "Added", "order": [{"item": "Cold Coffee", "quantity": 1}], "confirm": False},
                   {"reply": "Done", "order": [{"item": "Cold Coffee", "quantity": 1}], "confirm": True})
    bot.handle("one cold coffee")
    turn = bot.handle("yes confirm")
    assert turn.confirmed and turn.order_id.startswith("ORD-")
    assert (tmp_path / "orders.csv").read_text().count("Cold Coffee") == 1
    assert "already confirmed" in bot.handle("more").reply


def test_cannot_confirm_before_bill_is_shown(menu, tmp_path):
    bot = make_bot(menu, tmp_path, {"reply": "ok", "order": [{"item": "Cold Coffee", "quantity": 1}], "confirm": True})
    turn = bot.handle("one coffee, confirm")
    assert not turn.confirmed


def test_bad_llm_output_is_handled(menu, tmp_path):
    bot = make_bot(menu, tmp_path, "this is not json")
    turn = bot.handle("hello")
    assert "did not get that" in turn.reply and bot.history == []


def test_json_inside_code_fence_is_parsed():
    assert parse_llm_json('```json\n{"reply": "hi"}\n```') == {"reply": "hi"}
