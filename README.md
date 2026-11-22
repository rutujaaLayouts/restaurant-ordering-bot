# 🍛 Restaurant Ordering Bot (LLM Mini Project, PS 12)

**Name:** Rutuja Shejwal | **Roll No:** 12 | **Class:** LY CORE 02

## Problem statement
Taking food orders by phone is error-prone. This project is a chatbot that shows a menu, takes an
order in natural language, and confirms the bill. It helps small restaurants take orders without mistakes.

## How it works
1. The customer types an order (e.g. "2 butter naan and one dal tadka").
2. The **LLM** (Gemini or Groq) reads the message and returns the order as **JSON** (item + quantity).
3. **Python validates** each item against `data/menu.csv` (unknown items and bad quantities are rejected).
4. **Python calculates** the bill (subtotal + 5% GST). The LLM never does the maths.
5. After the customer confirms, the order is saved to `orders.csv` with an order ID and a receipt can be downloaded.

```
Customer -> Streamlit chat -> LLM (JSON) -> Python validation -> Python bill -> Reply + bill table
```

## Features
- Natural-language ordering, add / change / remove items
- Menu only: the bot cannot sell items that are not on the menu
- Accurate bill with `Decimal` maths and GST
- Live bill in the sidebar, order confirmation with ID, receipt download
- Works with **Gemini** or **Groq** (change one line in `.env`)
- 10 offline unit tests (no API key needed)

## Project structure
```
app.py                  Streamlit UI
restaurant_bot/
  bot.py                Conversation logic and order validation
  billing.py            Bill calculation (Python only)
  menu.py               Menu loading and item matching
  prompts.py            System prompt
  llm.py                Gemini and Groq clients
data/menu.csv           Menu with prices (edit to change the menu)
tests/test_bot.py       Unit tests
```

## How to run
```bash
git clone https://github.com/<username>/llm-ps12-12.git
cd llm-ps12-12
python -m venv venv && venv\Scripts\activate      # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                              # Mac/Linux: cp .env.example .env
# open .env and paste your free API key (Gemini: aistudio.google.com, Groq: console.groq.com)
streamlit run app.py
```
Run tests: `python -m pytest`

## Screenshots
Add your screenshots in the `screenshots/` folder and link them here:
`![Chat](screenshots/1_chat.png)`

## Safety notes
- API keys stay in `.env`, which is in `.gitignore` and never uploaded.
- The LLM output is never trusted blindly: items, quantities and the bill are checked by Python.

## Future improvements
Table numbers, a kitchen dashboard, voice ordering, and payment integration.
