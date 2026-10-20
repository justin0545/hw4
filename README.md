# Campus Customs: Shop + AI Stylist (MGT 409E Homework 4)

A Yale spirit-apparel storefront (React + Vite + TypeScript) with an AI shopping
assistant, the **Campus Customs Stylist**: a PydanticAI agent behind a FastAPI
backend. Shoppers can browse products, create an account, chat about merch, see
matching items appear on the page, save a closet and wish list, and get honest
price and stock answers from a local SQLite database.

**How it all works:** [`output/harness.md`](output/harness.md) (start with its "Start here" section).

## Project layout

```
hw4/
├── AI_prompts.md            # log of the prompts typed for each problem
├── requirements.txt         # Python dependencies for the backend
├── .env.example             # placeholder for PORTKEY_API_KEY (copy to .env)
├── .gitignore               # keeps data/, .env and node_modules out of git
├── README.md
├── frontend/                # Vite + React + TypeScript storefront and chat widget
├── backend/
│   ├── main.py              # FastAPI app: run with  uvicorn main:app --reload --port 8000
│   ├── agent.py             # the agent: wiring, context, tools, audit loop
│   ├── models.py            # Pydantic / PydanticAI structured types
│   ├── tools.py             # tool logic, product lookups, model setup (Portkey)
│   ├── prompts/prompt.md    # system prompt (voice, tools, safety rules)
│   ├── auth.py, db.py, chat_store.py, shopper_lists.py,
│   │   recommend.py, images.py, guardrails.py, audit.py   # supporting modules
│   └── test_*.py            # 124 automated checks (no API calls)
└── output/
    ├── harness.md           # how the system works: data, models, tools, safety, specs
    ├── design.md            # storefront design and why it helps sell (Problem 10)
    ├── usability.md         # four usability improvements (Problem 9)
    ├── app_check.html       # live-site test report; double-click to open (Problem 11)
    ├── app_check_images/    # screenshots linked from app_check.html
    └── audit_trail.json     # append-only log of agent-loop activity (Problem 12)
```

## 1. Place the data pack (not in git)

The database and product images aren't in this repo. Unzip the course
`data.zip` into a `data/` folder at the top of the project:

```
hw4/data/campus_customs.db      # catalogue, inventory, users (with the seeded test user)
hw4/data/products/*.jpg         # product images referenced by the catalogue
```

On first start the backend adds the tables it needs (sessions, closet, wish
list, a column on chat_messages) and builds compressed copies of the images in
`data/products_optimized/`. The first start takes about 30 seconds; later starts
are instant.

## 2. Set the API key

The agent calls `gpt-5.6-luna` through the course **Portkey** gateway. Set
`PORTKEY_API_KEY` in your environment, or copy `.env.example` to `.env` (in the
project root or `backend/`) and fill it in. `.env` is git-ignored. Never commit
a real key.

## 3. Run the backend (port 8000)

Python 3.12+ (developed on 3.14). From the project root:

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
```

```bash
pip install -r requirements.txt
```

Then from the `backend/` folder:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

> **Windows + OneDrive note:** if `pip install` fails with a "file name too long"
> error, the project path is too deep. Create the virtual environment somewhere
> short instead (e.g. `python -m venv C:\venvs\hw4`) and activate that one.

## 4. Run the frontend (port 5173)

Node 20+. From the project root:

```bash
npm --prefix frontend install
```

```bash
npm --prefix frontend run dev
```

Open **http://localhost:5173**. Vite forwards `/api` and `/media` to the
backend on port 8000.

**Test login** (seeded in the database): `test@campuscustoms.yale.edu` /
`password`. Or create a new account on the site.

## Things to try

- Ask the chat: *"What hoodies do you have?"* The matching cards appear on the
  Products page, and each one opens its product page.
- On any product page: *"Do you have this in pink?"* or *"How many are left in
  medium?"* The answers come straight from the database.
- Log in: **My Closet**, **♡ Wish List**, personal **Recommended for you**
  (with the stylist "thinking" animation), and chat history that comes back
  when you return.
- *"What goes with this?"* The stylist builds an outfit from real stock.

## Tests

From `backend/` with the virtual environment active. All six files use
throwaway copies of the database and audit file and a scripted stand-in model,
so they make **no API calls**:

```bash
python test_auth.py && python test_tools.py && python test_agent.py && python test_memory.py && python test_usability.py && python test_safety.py
```

| File | Checks | Covers |
|---|---|---|
| `test_auth.py` | 25 | PBKDF2 hashing, login, signup, sessions, lockout |
| `test_tools.py` | 11 | every price and stock number vs. SQL (102 products, 612 sizes) |
| `test_agent.py` | 13 | tools, output validator, history, page results |
| `test_memory.py` | 22 | saved chat history, customer and page context |
| `test_usability.py` | 29 | closet, wish list, recommendations, compressed images |
| `test_safety.py` | 24 | audit trail, redaction, rate limit, output guard |

## API

| Endpoint | Returns |
|---|---|
| `GET /api/health` | `{"ok": true, "agent_model": …, "api_key": true/false}` |
| `GET /api/products`, `GET /api/products/{id}` | Catalogue with per-size inventory (read-only) |
| `GET /api/products/{id}/outfit` | "Complete the look": pieces that pair with a product |
| `POST /api/auth/signup`, `/login`, `/logout`, `GET /api/auth/me` | Accounts; session in an HttpOnly cookie |
| `GET/POST /api/me/closet`, `/api/me/wishlist`, `DELETE /api/me/{kind}/{id}`, `POST /api/me/wishlist/{id}/move-to-closet` | My Closet and Wish List (login required) |
| `GET /api/recommendations` | Personal picks (staff picks for guests) |
| `GET /api/chat/history` | A logged-in shopper's saved conversation |
| `POST /api/chat` | `{message, history, page}` → `{reply, products, page_results}` from the agent |
| `GET /media/card/…`, `/media/large/…`, `/media/products/…` | Compressed and original product images |

## Safety and audit

Safety rules are in [`backend/prompts/prompt.md`](backend/prompts/prompt.md)
("Safety rules"). Code guardrails in `backend/guardrails.py` redact sensitive
data before the model sees it, rate-limit chat, cap reply length and block
replies that would leak secrets. Every agent-loop step is appended to
[`output/audit_trail.json`](output/audit_trail.json). Details are in
harness §13–15.
