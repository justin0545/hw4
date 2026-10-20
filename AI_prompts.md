# AI Prompt Log — MGT 409E Homework 4

**Student:** Justin
**Course:** MGT 409E — AI Foundations for Managers, Yale SOM
**Assignment:** Homework 4 — Campus Customs
**AI tool used:** Claude Code (Opus 5.5)
**Log started:** 2026-10-18

> **How to read this log.** Each section below covers one problem, worked in
> order. Prompts under "My prompt" are the ones I typed, copied word for word
> (typos included). When the first prompt didn't get me what I needed, a short
> note says what was missing, followed by the follow-up prompt.

---

## Working Context

| Field | Value |
|---|---|
| Business | Campus Customs |
| Database | `data/campus_customs.db` (SQLite): `catalogue` (102 rows), `inventory` (612), `users` (3), `chat_messages` (22) |
| Product images | `data/products/` — 102 `.jpg` files |

---

# Problem 1 — Vibe Coder Prompts

### My prompt
```
Let's start on homework 4. Create 'AI_prompts.md' and then keep it updated as I work. This file is the log of what I type. Similar to previous assignments, there should be one section for problem we walk through, each section should include the problem number and title, at least one prompt I typed, one follow-up prompt if needed.
```
**Timestamp:** 2026-10-18

### Outcome
Claude looked at the Homework 4 folder and the Homework 1 log for the format,
then created this file. No problem work yet.

### What was lacking
The log was ready, but I hadn't seen the data yet, and I wanted to look through
the database myself before describing Problem 2.

### Follow-up prompt
```
Open the campus_customs.db file so I can review it
```
**Timestamp:** 2026-10-18

### Outcome
No SQLite viewer is installed on this machine, so Claude exported the database
(read-only) to `db_review.html` and served the folder locally at
`http://localhost:8409/db_review.html` (config in `.claude/launch.json`). The
page has tabs for the catalogue (with product photos), an inventory grid by size
(out-of-stock and low-stock cells highlighted), users (password hashes
shortened), the chat message history, and the table schema.

---

# Problem 2 — Analyze the Database

### My prompt
```
Problem 2: Analyze the database - start the file output/harness.md. I will give you one short line for each field on why it matters, please record it properly in the file. Catalogue is important to understand all the information on the products the store currently offers - in this table there is name, type, price, stock, colors, description, and search tags all of which will help users as they chat with the agent to help find what they may be looking for or provide recommendations based on the conversation. Inventory keeps track of what is currently available for sale - in the table is product, type, and then the number of each size is available, all of which are helpful so the agent can provide the user with accurate information on what they can actually buy. User is a table that helps track the different users on the website - in the table is ID, first_name, last_name, name, email, password_hash, and created_at - this table will help track information on what they they purchased, looking for, etc. which can be helpful when remembering recommendations at later dates, sending out mailers when items are back in stock, and then also keeping a record of users. Chat messages and schema are additional logs that keep track of the chat messages and back end information used for the website.
```
**Timestamp:** 2026-10-18

### Outcome
Claude created `output/harness.md`. It has an overview of the five tables in the
database, and a section for each table with my reason it matters, lightly edited
for grammar. Each section also has a field-by-field table built from the actual
database columns (type and what each field holds). Claude also ran summary
queries and added a "Notes from the data" section: 145 of 612 size rows are out
of stock, there's no orders table, and chat history covers 2 of the 3 users.

---

# Problem 3 — Build the Campus Customs Website

### My prompt
```
Problem 3: Build the Campus Customs website - Please scaffold a React + Vite + Typescript front end for Campus Customs. Put a navigation bar at the top that links to the main pages: Home, Products, About Us, Log in, Create Account. For the 'Home' page, add quotes like "Proudly show your Yale pride!" and "Every day is spirit day!". For the "About Us" page include general information you would find and include text such as "We are Campus Customs, the premier location for Yale University apparel and gear. We offer some of the best options on campus for showing off your university pride. Stop by and take a look and bring your spirit game to the next level!" On the products page, show product images from the catalogue (use the image paths in the database) with basic product info (name, price, short description). Make each product open a single-item page (large image on one side, full product text on the other - description, price, sizes/stocks when you have them). Clicking a card on products should take the shopper there. Add a chat interface in the bottom right of the site (a floating chat panel is fine). It does not need to talk to an agent yet - a stub that will call the backend later is enough for this problem. You will need a small API soon to read the database, it is fine to start a simple FastAPI app in backend/main.py just to serve the products and images, then grow into the agent backend in problem 5.
```
**Timestamp:** 2026-10-18

### Outcome
- **Backend:** `backend/main.py` is a FastAPI app with its own virtual
  environment (`backend/.venv`, dependencies in `requirements.txt`). It opens the
  database read-only and serves `/api/products`, `/api/products/{id}` and the
  product photos. Claude first mounted all of `data/` for images, which would
  have let anyone download the database file. Claude caught this while testing
  and changed it to serve only `data/products/`.
- **Frontend:** `frontend/` is a Vite + React + TypeScript app using React
  Router. It has a nav bar (Home, Products, About Us, Log in, Create Account)
  and these pages:
  - **Home:** a hero section with my quotes and four featured products.
  - **About Us:** my text plus sections on what we carry, who we serve, and
    getting help.
  - **Products:** a grid of all 102 products (photo, name, type, price,
    two-line description) with search and garment-type filters.
  - **Product page:** large photo on the left. Description, price, colors and a
    size grid on the right, marking sold-out sizes and sizes with 5 or fewer left.
- **Log in / Create Account:** forms only. Submitting shows a note that accounts
  aren't connected yet.
- **Chat:** a floating chat panel in the bottom right. `sendChatMessage()` in
  `src/api.ts` returns a placeholder reply for now and becomes a call to
  `/api/chat` in Problem 5.
- **Verification:** the build and lint passed with no errors. Claude ran both
  servers and clicked through every page in the browser. The Baseball Left Chest
  Crewneck page's sizes matched the database (70 total). The chat stub replied.
  Claude also found and fixed name fields that spilled past the edge of the
  Create Account form. `README.md` has instructions for running the site.

---

# Problem 4 — Create Account and Login

### My prompt
```
Problem 4: Create account and login - Please build a normal create-account/login flow. Create Account: first name, last name, email, password, confirm password. Log in: email and password. New accounts go into the users table. Make sure to store passwords securely so hackers (human or AI) cannot access them. The seed database already has a test user you can use while building - Email: test@campuscustoms.yale.edu, password: password, hash function: PBKDF2-HMAC-SHA256 120,000  iterations (stored as pbkdf2_sha256$salt$hash). How login should check a password: You never un-hash the stored value, you re-hash what the user typed and compare, read the salt out of the stored string - do not make a new one at login, hash the typed password with the same salt, then compare to the stored hash, use a constant-time compare, signup and login must use the same hash settings (same function, same salt handling, same iteration count). if they differ, even the right password will not match. To check, log in as the seeded test user and as a brand new account just created in our own app. Then, confirm you can log in as that user and that a brand new account we create also works. Update output/harness.md with how auth works.
```
**Timestamp:** 2026-10-18

### Outcome
- **Hash format first:** before writing code, Claude checked the seeded test
  user's stored value and confirmed the salt is used as plain text (UTF-8),
  not decoded from hex. Re-hashing "password" with that salt matched.
- **Backup:** this was the first change that writes to the database, so Claude
  saved an untouched copy as `data/campus_customs.seed.db`.
- **Backend (`backend/auth.py`):**
  - PBKDF2-HMAC-SHA256 at 120,000 iterations, with a new random salt at signup.
  - Login reads the salt from the stored string, re-hashes, and compares with
    `hmac.compare_digest`. Signup and login share one hashing function.
  - Endpoints: signup, login, logout and me.
  - Sessions use an HttpOnly cookie, and the new `sessions` table stores only
    a hash of each token.
  - Extra protections: the same error for a wrong email or a wrong password, a
    dummy hash check for unknown emails so response time gives nothing away, and
    a 15-minute lockout after 5 failed logins.
- **Frontend:** a Create Account form with confirm password (flags a mismatch as
  you type), a Log in form, and a nav bar that shows "Hi, \<name\>" and Log out
  once you're logged in.
- **Verification:**
  - `backend/test_auth.py` passed 25 of 25 checks, run on a copy of the seed
    database.
  - In the browser: the seed user was rejected with a wrong password and logged
    in with the right one.
  - Claude created a new account (Handsome Dan) on the Create Account page, then
    logged out and back in with it.
  - In the real database, user 4 is stored in the same format as the seed users,
    and the password text doesn't appear anywhere in the file.
  - Test credentials are in `backend/TEST_ACCOUNTS.md`.
- **Also:** the backend's auto-reload got stuck partway through the change and
  had to be restarted by hand.
- **Docs:** added section 4 "How Authentication Works" to `output/harness.md`.

---

# Problem 5 — PydanticAI Agent Backend

### My prompt
```
Problem 5: PydanticAI agent backend - Now please build the shop chatbot as a PydanticAI agent behind FastAPI, plugged into our front-end chat widget. Put the API app in backend/main.py - that is the file to run with Uvicorn. Keep the agent as these four files next to it (same idea has homework 3). backend/prompts/prompt.md - system prompt (grow this same file later), backend/agent.py - agent entry/wiring, backend/tools.py - tools the agent can call, backend/models.py - Pydantic / PydanticAI structured types. In main.py, expose a chat route so a message from the website returns a reply from the agent (and whatever else we need for products/auth). We will need the AI model API key for the agent. Put Campus Customs voice and safety basics into prompts/prompt.md (we will expand tools and safety later). Start or update types in models.py for chat replies/product cards as needed. In output/harness.md, note how the front end talks to FastAPI and how the agent is loaded (prompt file + model). In output/harness.md, note how the front end talks to FastAPI and how the agent is loaded (prompt file + model). Mkae sure the backend runs from the backend/ folder like this "uvicorn main:app --reload --port 8000"
```
**Timestamp:** 2026-10-18

### Outcome
- **Homework 3 first:** Claude read the Homework 3 agent to reuse its layout
  and model setup. That means the course Portkey gateway, the same model, and a
  key from `PORTKEY_API_KEY`, which was already set in my environment.
- **Install problem:** PydanticAI wouldn't install inside the Homework 4 folder
  because the OneDrive path plus the package's file paths went over Windows'
  260-character limit. Turning on long paths is a system setting, so instead
  Claude moved the Python environment to `C:\Users\justi\.venvs\campus-customs-hw4`
  and deleted the half-installed `backend/.venv`.
- **The four agent files:**
  - `prompts/prompt.md`: voice, how to answer, and safety basics.
  - `models.py`: `ChatRequest`, `ChatReply`, `ProductCard`, the `ShopReply`
    agent output, and the tool result types.
  - `tools.py`: `search_products`, `get_product`, `check_stock`, plus building
    product cards and the model.
  - `agent.py`: wiring. It loads the prompt, registers tools, adds the shopper's
    name, checks that product IDs are real, and caps steps per message.
- **`main.py`:** adds `POST /api/chat`. Product cards are built from the
  database, not typed by the model, and logged-in chats are saved to
  `chat_messages`. Imports were changed so `uvicorn main:app --reload --port 8000`
  runs from `backend/`.
- **Frontend:** the chat widget now calls the agent, sends the conversation
  history (including which products were shown), and displays clickable
  product cards.
- **Problems found while testing:**
  - The first real question failed. The model checked stock for all 8 search
    results one by one and hit the tool-call cap. Claude rewrote that part of
    the prompt; the same question now takes 1 call.
  - A jailbreak test was blocked by the gateway's Azure filter and showed up as
    an error. Claude made it return a friendly redirect instead.
  - The agent said "Boola Boola!" in almost every reply, so the prompt now
    limits it.
  - The chat panel spilled off the edge of very narrow screens.
- **Verification:** `test_agent.py` passed 7/7 and `test_auth.py` 25/25. Live
  tests covered XL hoodies, pink (honestly "we don't carry it"), economics
  homework (declined), and prompt-injection attempts. In the browser, logged in:
  4 bulldog cards with the correct prices and sizes, and the follow-up "Does the
  first one come in a small?" was answered correctly from memory. The chat rows
  were saved for user 4.
- **Docs:** added section 5 to `output/harness.md`. Updated `README.md` and
  added `backend/.env.example`.

---

# Problem 6 — Tools: Product Info and Stock

### My prompt
```
Problem 6: Tools: product info and stock - Give the agent tools that look up real information from campus_customs.db : product desccription, price, how many are in stock (by size when the customer asks). The agent must use the database - it should not invetn prices or quantities. If a size is out of stock, say so clearly. Expand prompts/prompt.md so the agent knows to call these tools for price and stock questions. Add or update return types in models.py. In output/harness.md, list each tool and explain which model fields you chose for lookup results and why.
```
**Timestamp:** 2026-10-18

### Outcome
- **Return types (`models.py`):** Claude redesigned the tool results.
  - Fields are named with their meaning (`price_usd`, `quantity_in_stock`).
  - A stock `status` label (in stock / low stock / sold out / size not offered)
    is computed in code instead of left to the model.
  - `ProductDetail` gained `stock_by_size`, `sold_out_sizes` and `is_sold_out`.
  - `StockCheck` gained a `note` that tells the model to say "sold out"
    clearly.
  - Internal columns (`search_tags`, image path) were left out of tool results.
- **Tools (`tools.py`, `agent.py`):** `search_products`, `get_product` and
  `check_stock` now:
  - understand size words ("medium" → M, "2XL" → XXL);
  - reject non-sizes;
  - answer a wrong or made-up product ID with the closest real matches instead
    of a dead end;
  - have clearer descriptions of when to use each one.
- **Prompt:** a new "Price and stock questions" section. It has a question →
  tool table and rules: look prices and stock up every time, give exact prices
  with no invented sales, use only the catalogue description, state sold-out
  sizes clearly with no "check back," and give exact counts when asked or when
  stock is low.
- **Verification:**
  - New `test_tools.py` compares the tools with direct SQL for all 102 products
    and all 612 product-size rows: 11/11, 0 mismatches.
  - Eight live questions (price, a named size, how many left, two sold-out
    sizes, a full size breakdown, material, a product we don't sell) all matched
    the database exactly. The agent said "I don't have that information" for
    material and "we don't carry" for mittens.
- **Docs:** `output/harness.md` section 6 lists each tool and explains every
  field choice.

---

# Problem 7 — Chat Search That Updates the Page

### My prompt
```
Problem 7: Chat search that updates the page - Now we will add a neat feature to the site. When a customer asks about a type of item - for example "what hoodies do you have?" - the agent should search the catalogue and the website should dynamically show these matching items as product cards (image, name, price, short info). This is an API contract: the agent returns the structured product matches and then the front end renders them on the website. After the dynamic product cards are loaded by your new feature, make sure the same single-item page behavior we built in problem 3 still works: each product card - including the ones the chat just put on the page - should still open that detail view (large image + full info) when clicked. Update prompts/prompt.md and output/harness.md so it is clear how search results reach the page.
```
**Timestamp:** 2026-10-18

### Outcome
- **API contract:**
  - Each search now gets a `search_id`.
  - The agent's `ShopReply` gained `page_search_id` + `page_title`, so the
    agent points at a search it ran instead of typing out a list.
  - The backend keeps every match of each search (not just the 8 the model
    sees). A validator rejects made-up or empty searches.
  - `POST /api/chat` now returns `page_results`: title, query, filters, count
    and up to 48 product cards built from the database. `ProductCard` gained
    `description` for the card's short info.
- **Frontend:**
  - A shared chat-results store. When a reply has page results, the site moves
    to the Products page and shows a "From your chat" banner with the cards.
  - The cards use the **same** `ProductCard` component as the catalogue, so
    each one still opens the Problem 3 detail page.
  - Each chat reply with results gets a button to bring them back, and "Show
    all products" returns to the full catalogue.
- **Prompt:** a new "Showing search results on the page" section. It covers
  when to fill the page (browsing a kind of item) and when not to (one product,
  price/stock checks, things we don't carry, backup searches), how narrowing
  works, and keeping the chat short.
- **Found while testing:** the running server had kept the old prompt, because
  `uvicorn --reload` doesn't watch `.md` files. `agent.py` now re-reads
  `prompt.md` on every message, so prompt edits apply immediately.
- **Verification:**
  - `test_agent.py` passed 13/13, including all 27 hoodies reaching the page
    through the API and every card's detail record existing.
  - The live model filled the page for hoodies (27), navy crewnecks in medium
    (16) and bulldog (10), and correctly did **not** fill it for pink or a
    price question.
  - In the browser: asking from the Home page moved to Products with 27
    hoodie cards. Clicking one opened its detail page, and going back kept the
    results. "Just the gray ones" updated the page to 10, and "Show all
    products" restored 102.
- **Docs:** `output/harness.md` section 7 has the full data-flow diagram and the
  contract table.

---

# Problem 8 — Customer Memory

### My prompt
```
Problem 8: Customer memory - When a shopper is logged in, save their chat history in the database in an appropriate table and reload it when they return. The agent should know who is chatting (name, email) - put that in agent deps (or an equivalent clear pattern) and/or tools the agent can call. Also pass enough page context that if someone is on a product page and asks "do you have this in pink?", the agent knows which item they mean - put the code in the agent context. Guests can still chat, but history only needs to persist for logged in users. Document in output/harness.md: how user chat history is stored, what customer fields the agent sees, and how page context is passed.
```
**Timestamp:** 2026-10-18

### Outcome
- **Storage (`backend/chat_store.py`):**
  - Reuses the seed `chat_messages` table, adding a `page_results_json` column
    and a per-user index at startup.
  - Logged-in turns are saved. `GET /api/chat/history` returns the last 50
    messages, with cards rebuilt from the current catalogue.
  - The agent's memory for logged-in shoppers is loaded from the database on the
    server, and the browser's copy is ignored. Guests use in-memory history that
    isn't saved.
  - Content-filtered messages aren't saved, so they can't poison future turns.
- **Who's chatting:**
  - `ChatDeps.customer` (a `Customer` built from the session cookie) holds the
    name, email and member-since date.
  - An instruction function tells the model who's chatting, or that it's a
    guest.
  - A new `get_my_account` tool returns the shopper's own details.
- **Page context:**
  - The widget sends `{path, product_id, showing_chat_results}` with each
    message, and the server validates it.
  - `build_page_view()` looks the product up in the database. A
    `page_context()` instruction tells the model "they're on the product page
    for X (colors…); 'this' means this product."
- **Frontend:** the chat reloads saved history on page load or login ("Saved
  conversation" … "Welcome back, \<name\>!") and starts fresh on logout.
- **Prompt:** new section "Who you're talking to, and where they are."
- **Problems found while testing:**
  - The agent said "30 days" as a member when it was 29. The model did its own
    date math, and the server clock is in UTC. Claude added a `days_as_member`
    field computed in code.
  - The backend's auto-reload stalled mid-edit (as in Problem 4) and needed a
    manual restart.
  - Claude's own log lines weren't being printed and were fixed.
- **Verification:**
  - `test_memory.py` passed 22/22, and the other tests still pass.
  - Live: recalled the seed user's past hoodie and pink questions, gave their
    email and 29 days, and on product pages answered "this in pink?" and "in
    XL/medium?" about the right item.
  - A guest isn't remembered, and the agent refused to discuss another customer.
  - In the browser, Handsome Dan's 8 earlier messages came back after a reload.
- **Docs:** `output/harness.md` section 8.

---

# Problem 9 — Usability Improvements

### My prompt
```
Problem 9:  Usability improvements - Now that the core shop works, improve it. Let's add in 2 front-end usability improvement and 2 agent/backend usability improvements. For the front-end let's add a "closet" section that shows what they currently have and a "wish list" section so they can add certain items to their "wish list" for purchasing later. For the agent/backend let's add in a recommendation feature that will create recommendations for the user based off purchase and chat history and then lets add in a feature that will compress images from the catalogue and web pages to help reduce token cost and speed up web page access.
```
**Timestamp:** 2026-10-18

### What was lacking
I hadn't asked for a write-up or said the graders need to find every feature in
the running app, so I added that while Claude was building.

### Follow-up prompt
```
Then, write output/usability.md before or as you build. for each improement, say "what you added, why it helps a campus customs shopper or business. Then make sure all improvement actually show up in the running app, graders will reach the wrtite-up and look for the features.
```
**Timestamp:** 2026-10-18

### Outcome
- **My Closet:** a `/closet` page and an "I own this" button with a size picker
  on product pages, stored in a new `closet_items` table. The closet doubles as
  purchase history, since the shop has no checkout.
- **Wish List:**
  - A `/wishlist` page with the total price, live stock for each saved size
    ("Size L is sold out"), and "I bought it" (moves the item to the closet) and
    Remove buttons.
  - "♡ Save to wish list" on product pages.
  - New agent tools `add_to_wish_list` and `get_my_lists`, so the chat can save
    items and answer wish-list questions.
- **Recommendations (`recommend.py`):**
  - Scores in-stock items against the closet (weight 3), wish list (2) and
    products shown in chat (1). Rare features count more, and there are at
    most 2 per garment family.
  - Never recommends what the shopper owns or has wish-listed. Every pick has a
    reason ("Goes with your … (in your closet)").
  - Shown on the Home page and the closet page, and through the agent's new
    `recommend_for_me` tool, which can fill the page. Guests get labeled staff
    picks.
- **Image compression (`images.py`):**
  - 360 px WebP cards, 800 px WebP product pages, and a 512 px JPEG for any
    model call. Built at startup (only missing or changed files) and served with
    a one-week cache.
  - The full grid went from 3,603 KB to 595 KB (84% smaller). Estimated vision
    tokens dropped 65%.
  - Noted honestly that the current agent sends no images, so the token savings
    apply to future image features.
- **Write-up:** `output/usability.md` covers what was added, why it helps
  shoppers and the business, where to see each feature, measured results, and
  verification. Section 9 of `harness.md` covers the new tables, tools and
  routes.
- **Verification:**
  - New `test_usability.py` passed 29/29, and the other four test files still
    pass.
  - Every feature was checked in the running app as Test User: nav links, Home
    recommendations, both save buttons, wish-list sold-out flag and total, "I
    bought it," closet recommendations, the three chat features (recommend → 6
    cards on the page, wish-list status, "add this… in a medium"), and WebP
    images across all 102 grid cards.
  - Test User was left with 2 closet and 2 wish-list items so graders see
    populated pages.

---

# Problem 10 — Style the Website

### My prompt
```
Problem 10: Style the website - Now please add a creative design so the site feels like a real Campus Customs storefront - fonts, color, hierarchy, motion, product presentation, chat feel. Let's make the site seem it is the go to place for spirit apparel. When people talk to the chat bot, it should be friendly and excited when talking to users about clothes - make it ask questions on how they are going to wear and where so it can help find the right outfit, etc. Make it also seem intelligent on what different pieces can go with to offer other product recommendations. For the store front itself, use Yale colors and the bulldog mascot on the page. Add fun effects on certain buttons as people go to check out. For the recommendation section have it do an animation like it is "thinking" for different recommended items (something like a cogwheel or a stylist looking through clothes, etc.). The colors should be vibrant and a smooth user experience emphasizing the products. Include hover menus that give people a sneak peak before clicking on some top items.  Write output/design.md on what you changes and why it should help customers stick around and buy - keep it concrete and short.
```
**Timestamp:** 2026-10-18

### Outcome
- **Look:**
  - Yale Blue and white with a bright spirit blue, and gold reserved for
    actions.
  - Graduate (collegiate) headlines with Outfit body text.
  - An original SVG bulldog mascot in the logo, hero, chat button and avatar,
    footer, stylist animation and checkout. It's not an official Yale mark.
- **Home:**
  - A hero with a bobbing bulldog and floating products, plus a gold spirit
    ticker.
  - "Shop by style" category tiles.
  - **Top picks with hover sneak peeks** (gold "👀 Sneak peek" panel: larger
    photo, description, sizes, "Almost gone").
  - Sections fade in on scroll.
- **Nav:** a **Products ▾ hover menu** with categories and top picks (a live
  sneak peek on hover), plus a bag button with a count badge.
- **Products page:** category pills.
- **Buying effects:**
  - Size buttons. Add to bag shakes the sizes if none is picked; otherwise the
    photo **flies into the bag** and the badge pops.
  - A heart burst for the wish list and a paw burst for "I own this."
  - A slide-in bag drawer and a glowing **Check out** button that sets off
    **confetti and paws** and a winking-bulldog success panel. It says online
    payment is coming soon; nothing is charged.
  - Every effect turns off for shoppers who ask for reduced motion.
- **Recommendations:** a **"stylist is thinking"** animation (bulldog with a
  spinning gold cog, and a swinging clothes rack flipping through real product
  photos with rotating captions) for at least 1.8 seconds. Then the picks deal
  in one by one, and **Restyle me** replays it.
- **Stylist intelligence:**
  - New `suggest_outfit` tool: layering rules, color and theme matching, only
    in-stock items, closet first.
  - "Complete the look" on every product page (new `/api/products/{id}/outfit`).
  - The prompt was rewritten into an excited Campus Customs Stylist that reacts,
    picks, then asks one question at a time (where, how cold, size, style, who
    it's for).
- **Chat:** a bulldog avatar, "Online" status, starter chips (game day, gift,
  cozy class hoodie, what goes with what I own), bouncing typing dots, and an
  "Ask the Stylist" bubble.
- **Fixed during testing:**
  - Hidden sneak-peek panels caused sideways scrolling.
  - The checkout paw burst was aimed at a removed button.
  - Effect clean-up stalled in background tabs.
  - The mascot's cat-like pointy ears became folded "rose" ears.
  - Outfit picks tied alphabetically, so stock now breaks ties and picks rotate
    across layering options.
  - The stylist's first reply didn't ask a question, so the prompt now spells
    out the reply shape.
  - Starter chips are now shown for returning shoppers too.
- **Verification:**
  - Checked with screenshots at desktop and phone widths.
  - Live chats: the Family Weekend gift for mom got a question back about her
    size and style. The cold-game outfit in L was confirmed in stock (15/8/5).
    "What would go well with this?" on the Branford page worked.
  - The build and lint are clean, and all 100 backend checks pass.
- **Docs:** `output/design.md` (what changed and why it helps sell), and
  `harness.md` section 10.

---

# Problem 11 — Site Testing (App Check)

### My prompt
```
Problem 11: Site testing (app check) - Test the live site and document it in output/app_check.html (a page you can double click open). Include clear screenshots and short captions for: 1. Chart checking the inventory level of an item (honest stock/price from the DB), 2. The dynamic search-result cards appearing after a category question (e.g. hoodies), 3. One of the usability features added in problem 9. Make the html easy to grade: heading for each check, screenshot, one or two sentences on what the screenshot proves. Put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png)
```
**Timestamp:** 2026-10-18

### Outcome
- **Item 1:** Claude read "Chart checking" as **Chat checking** an item's
  inventory, and backed it up with database values.
- **Screenshot problem:** the in-app browser pane was hidden or small, so its
  screenshots were cropped, low-resolution, and caught animations half-finished.
  Claude switched to **headless Microsoft Edge** (already installed), driven by
  a Node script over the DevTools protocol. Nothing was downloaded.
  - The script logged in as the test user, typed into the chat and clicked
    cards like a shopper, and saved six 1280×860 PNGs to
    `output/app_check_images/`.
- **Check 1 (chat inventory):**
  - On the Champion Reverse Weave Hoodie page, "How many of this hoodie are in
    stock in each size, and how much is it?" got "$68 … XS 0 (sold out), S 25,
    M 20, L 20, XL 0 (sold out), XXL 15."
  - That matches the product page and the SQLite `catalogue`/`inventory` rows
    exactly.
- **Check 2 (search cards):**
  - "What hoodies do you have?" put a "From your chat · Hoodies · 27 matches"
    banner and 27 cards on the Products page. The database has 27 hoodies.
  - Clicking the first card opened the Problem 3 detail page, and its sizes
    matched the database.
- **Check 3 (Problem 9 features):**
  - Wish List with live saved-size stock: Branford M "in stock" (database 20),
    Boola Boola L "sold out" (database 0), and a $104.00 total.
  - My Closet with 8 recommendations, each with a reason from the closet, wish
    list or chats.
- **The report (`output/app_check.html`):**
  - A summary table, then one section per check: a heading, the screenshots,
    a one- or two-sentence "What this proves" caption, and a database-truth
    table. It also lists the other checks: 100/100 backend tests, and a clean
    build and lint.
  - Claude opened it from disk in headless Edge to confirm all 6 relative image
    links load. It fixed unreadable header labels and made the wide tables
    scroll inside their boxes on small screens.

---

# Problem 12 — Audit Trail, Safety, Finish Harness

### My prompt
```
Problem 12: Audit trail, safety, finish harness - Please keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/result, stop reason). Do not wipe it between runs. Also, put safety rules in prompts/prompt.md - rules to include are "Do not ask for any personal identifying information, do not ask for password, and do not spend extraneous tokens performing unnecessary tasks the user may prompt outside of general shopping assistance." Also include other safety guardrails that are standard I may not have thought of. Finish output/harnesss.md so it is clear how the system works. Model fields in models.py and why we chose them, tools and abilities, safety rules, specs (loop limits, result caps, models, how to run front + back)
```
**Timestamp:** 2026-10-18

### Outcome
- **Audit trail (`backend/audit.py`, `agent.run_chat`):**
  - Follows the Homework 3 format: a JSON array with one `AuditEntry` per
    agent-loop step. Each entry has the time, run ID, shopper (`user:<id>` or
    `guest`, no names or emails), page, redacted message preview, tool calls
    with clipped args, one-line result summaries (ok/retry/error), tokens, and
    the stop reason on the last step.
  - Append-only: read, append, atomic replace. It's never wiped, and an
    unreadable file is set aside, not deleted.
  - Also logs content-filter blocks, errors, rate-limit hits and output-guard
    replacements.
  - Tests write to a throwaway file, so the real trail only holds real
    activity.
- **Safety rules in `prompt.md`:** my three rules (no personal identifying
  information, no passwords, no tokens on non-shopping tasks), plus seven
  standard ones:
  - no professional advice
  - other customers' privacy
  - private instructions and prompt-injection resistance
  - honesty and no over-promising
  - act only when asked
  - respectful and appropriate for all ages, with nothing illegal
  - a distress response pointing to 988 and campus resources
- **Code guardrails (`backend/guardrails.py`):**
  - Redacts card numbers (Luhn-checked), SSNs, passwords, phone numbers and
    emails before the model, saved history or audit see them.
  - A rate limit of 12 messages per minute (over the limit means no model
    call), a 700-token reply cap, and an output leak check (password hash, API
    key, prompt text, card number).
- **Live tests:**
  - Essay, calculus and trivia requests → 1–2 sentence declines with no cards.
  - "Text me when it restocks" → please don't share your phone number.
  - "Verify my password" → refused.
  - Card number → the model saw `[redacted card number]` and warned.
  - Jailbreak → blocked and logged.
- **Fixes along the way:**
  - The agent told a shopper they could "complete the purchase securely"
    online. The prompt now says online payment isn't available yet.
  - Card redaction swallowed the following space.
- **Honest limitation:** for off-topic messages the model still makes one quick
  search before declining, about 90 tokens. It's documented in harness §13.
- **`harness.md` finished:**
  - A "Start here" overview with an architecture diagram and contents.
  - §11 Models reference (every model and field, and why, under five design
    rules).
  - §12 Tools and abilities, §13 Safety (prompt rules plus code guardrails,
    with live results), §14 Audit trail, §15 Specs (models and stack, loop
    limits, result caps, how to run the front and back ends, tests).
- **Verification:** new `test_safety.py` passed 24/24. All six test files pass
  (**124/124**), and the frontend build is clean.

---

# Problem 13 — Push to GitHub and Submit the URL

### My prompt
```
Now we are done with the assignment - the next step is for you to act like a TA grader and grade the assignment and then we need to upload the completed assignment to a public github repository
```
**Timestamp:** 2026-10-19

### What was lacking
Claude didn't have the official assignment rubric, so it could only grade
against my own prompts, not the course's requirements and point values.

### Follow-up prompt
```
You need the link to act as the TA grader, here it is https://zlisto.github.io/mgt_409_fa26/hw4/p1.html
```
**Timestamp:** 2026-10-19

### Outcome
- **Grading:** after all 13 problems were finished, Claude read the problem
  pages as the grading rubric and scored each one (self-grade about 92.5/100
  before fixes; saved locally as `grading_report.md`, which is git-ignored).
  Deductions found:
  - **P13:** not pushed yet; root files missing.
  - **P2:** the "why it matters" line was per table, not per field.
  - **P1:** the first section was titled "Setup" and was missing a "what was
    lacking" sentence.
  - **P3:** yalebulldogblue.com was never researched.
  - **P9:** image compression is a borderline "agent/backend" item.
- **Fixes I chose before pushing:**
  - Moved `requirements.txt` and `.env.example` to the project root, with the
    key also loadable from a root `.env`.
  - Added a `.gitignore` that keeps out `data/` (the database, product images,
    seed backup and generated images), `.env`, `node_modules/`, `dist/`,
    `.claude/`, `db_review.html` (it embeds database rows) and the grading
    report.
  - Rewrote the README to run on any machine (data-pack placement, a venv in
    the project, run and test commands, the file tree).
  - Made the tests fall back to the data pack's `campus_customs.db` when the
    local seed backup isn't there.
  - Added a per-field "why it matters" column to harness §2.
  - Retitled Problem 1, added its missing sentence, and added this section.
- **Publishing:** I chose a public repo named `hw4`, so a clone lands in a
  folder named `hw4`, matching the expected tree. Commits use my private GitHub
  noreply email. The GitHub CLI isn't installed, so I create the empty repo on
  github.com and Claude pushes with git.

### Follow-up prompt
```
Here is the repo https://github.com/justin0545/hw4.git
```
**Timestamp:** 2026-10-19

### Outcome
- Claude committed the project to **https://github.com/justin0545/hw4**, the
  URL to submit on Canvas.
- The commits use my GitHub noreply address, set for this repo only.
- Before pushing, Claude checked that the data pack and `.env` were excluded
  and scanned all 80 files for secrets: none found.
