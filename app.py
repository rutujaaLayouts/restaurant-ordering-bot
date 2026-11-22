"""Streamlit UI for the Restaurant Ordering Bot (PS 12)."""
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from restaurant_bot.bot import OrderingBot
from restaurant_bot.llm import LLMError, create_client
from restaurant_bot.menu import Menu

load_dotenv()
ROOT = Path(__file__).parent

st.set_page_config(page_title="Spice Route Ordering Bot", page_icon="🍛", layout="wide")


@st.cache_resource
def load_menu() -> Menu:
    return Menu.from_csv(ROOT / "data" / "menu.csv")


def bill_table(bill) -> str:
    rows = ["| Item | Qty | Price | Amount |", "|---|---:|---:|---:|"]
    rows += [f"| {l.item} | {l.quantity} | ₹{l.unit_price} | ₹{l.amount} |" for l in bill.lines]
    rows += [f"| **Subtotal** | | | ₹{bill.subtotal} |",
             f"| GST (5%) | | | ₹{bill.gst} |",
             f"| **Total** | | | **₹{bill.total}** |"]
    return "\n".join(rows)


def receipt_text(order_id, bill) -> str:
    lines = [f"SPICE ROUTE - ORDER {order_id}", "-" * 36]
    lines += [f"{l.item} x{l.quantity}  Rs {l.amount}" for l in bill.lines]
    lines += ["-" * 36, f"Subtotal: Rs {bill.subtotal}", f"GST 5%:   Rs {bill.gst}",
              f"TOTAL:    Rs {bill.total}", "Thank you!"]
    return "\n".join(lines)


def new_order() -> None:
    st.session_state.bot.reset()
    st.session_state.messages = [{"role": "assistant", "content": OrderingBot.greeting()}]
    st.session_state.receipt = None


menu = load_menu()

if "bot" not in st.session_state:
    try:
        st.session_state.bot = OrderingBot(menu, create_client(), ROOT / "orders.csv")
    except LLMError as exc:
        st.error(f"Setup problem: {exc}")
        st.info("Copy `.env.example` to `.env`, add your API key, then restart the app.")
        st.stop()
    new_order()

bot: OrderingBot = st.session_state.bot

# ---------- Sidebar: menu + live bill ----------
with st.sidebar:
    st.header("📋 Menu")
    for category, items in menu.by_category().items():
        with st.expander(category, expanded=category == "Main Course"):
            for it in items:
                st.write(f"{it.name} — ₹{it.price}")
    st.divider()
    st.header("🧾 Your bill")
    bill = bot.current_bill()
    if bill:
        st.markdown(bill_table(bill))
    else:
        st.caption("No items yet.")
    st.button("Start new order", on_click=new_order, use_container_width=True)

# ---------- Main: chat ----------
st.title("🍛 Spice Route Ordering Bot")
st.caption("Tell me what you'd like. Example: *2 butter naan and one paneer butter masala*")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if st.session_state.get("receipt"):
    st.download_button("⬇️ Download receipt", st.session_state.receipt, "receipt.txt")

if prompt := st.chat_input("Type your order...", disabled=bot.finished):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                turn = bot.handle(prompt)
            except LLMError as exc:
                st.error(f"The AI service had a problem. Please try again. ({exc})")
                st.stop()
        text = turn.reply
        for w in turn.warnings:
            text += f"\n\n⚠️ {w}"
        if turn.bill:
            text += "\n\n" + bill_table(turn.bill)
        if turn.confirmed:
            text += f"\n\n✅ **Order confirmed! Your order ID is `{turn.order_id}`.**"
            st.session_state.receipt = receipt_text(turn.order_id, turn.bill)
        st.markdown(text)
    st.session_state.messages.append({"role": "assistant", "content": text})
    st.rerun()
