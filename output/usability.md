# Campus Customs — Usability Improvements

**Problem 9.** Four improvements on top of the working shop: two on the front
end and two in the agent and backend. Each section says what was added, why it
helps a Campus Customs shopper or the business, and **exactly where to see it in
the running app**.

## How to see everything

1. Start the backend and frontend (commands in `README.md`) and open
   **http://localhost:5173**.
2. Click **Log in** and use the test account: **test@campuscustoms.yale.edu** /
   **password** (also in `backend/TEST_ACCOUNTS.md`).
3. The test account already has items in its closet and wish list (added while
   verifying), so every feature has something to show right away.

| # | Improvement | Type | Where to look |
|---|---|---|---|
| 1 | **My Closet** | Front end | Top bar → **My Closet** (`/closet`); **"I own this"** button on any product page |
| 2 | **Wish List** | Front end | Top bar → **♡ Wish List** (`/wishlist`); **"♡ Save to wish list"** button on any product page; or ask the chat "add this to my wish list" |
| 3 | **Personal recommendations** | Agent / backend | **Home** page ("Recommended for you, Test"), bottom of **My Closet**, and chat: "What would you recommend for me?" |
| 4 | **Image compression** | Backend / front end | Every product image on the site (right-click an image → open in new tab: the URL is `/media/card/….webp` or `/media/large/….webp`) |

---

## 1. My Closet (front end)

### What I added
- A **My Closet** page (`/closet`, linked in the top bar when logged in) that
  shows the Campus Customs gear the shopper already owns. Each item appears as a
  normal product card with its size and the date it was added, plus a
  **Remove** button. Clicking a card opens the product page.
- An **"I own this"** button (with a size picker) on every product page. Once
  saved, the page shows "✓ In your closet (M)."
- On the Wish List, **"I bought it"** moves an item straight into the closet.
- A **"Recommended for you"** section at the bottom of the closet page, with
  picks that go with what they own (improvement 3).
- Stored in a new `closet_items` table (one row per product and size per
  shopper). Every item shows current details from the catalogue.

### Why it helps
- **Shopper:** one place to see their Yale wardrobe. It answers "do I already
  have this?" before buying a duplicate, and makes it easy to find pieces that
  go with what they own, such as a matching crewneck for a hoodie.
- **Business:** the closet works as **purchase history**. The shop has no
  checkout yet, so this is the most direct signal of what a customer actually
  buys. It feeds recommendations (no recommending things they already own) and,
  later, could drive "complete the set" emails.

### Where to see it
Log in → **My Closet** in the top bar. To add something, open any product (for
example the *District Vit Hoodie Vintage Sailor Bulldog*), pick a size and click
**I own this**.

---

## 2. Wish List (front end)

### What I added
- A **♡ Wish List** page (`/wishlist`) with saved items as product cards, the
  number of items and their **total price**, and two buttons per item: **I
  bought it** (moves it to the closet) and **Remove**.
- **Live stock for the saved size:** each item shows "Size M in stock" in green
  or **"Size L is sold out"** in red, read from the inventory every time the
  page loads.
- A **"♡ Save to wish list"** button with a size picker on every product page,
  then "♥ On your wish list (L)."
- **From the chat:** "add this to my wish list in medium" works through a new
  agent tool, `add_to_wish_list`. On a product page "this" is that product, as
  in Problem 8. The agent can also answer "what's on my wish list, and is it in
  stock?" with `get_my_lists`.
- Stored in a new `wishlist_items` table, the same shape as the closet.

### Why it helps
- **Shopper:** a "save for later" list for the hoodie they want before The Game
  or a gift for a parent. The sold-out flag means they don't find out at the
  last minute that their size is gone.
- **Business:** a wish list is a list of **intent to buy**. It shows which items
  and sizes are in demand, including sold-out sizes worth restocking (the test
  user wants the Boola Boola tee in L, which is at 0). It's also the basis for
  future "back in stock" or price-drop emails, and it shapes recommendations.

### Where to see it
Log in → **♡ Wish List** in the top bar. The test account shows the *Branford
1/4 Zip* (Size M in stock) and the *Boola Boola T Shirt* (**Size L is sold
out**). To add one, open a product, pick a size and click **♡ Save to wish
list**, or open the chat on a product page and type "add this to my wish list in
medium."

---

## 3. Personal Recommendations (agent / backend)

### What I added
- A recommendation engine (`backend/recommend.py`) that scores every in-stock
  product against three signals from the shopper's history, strongest first:
  1. **Closet**: what they own, their purchase history (weight 3)
  2. **Wish list**: what they want (weight 2)
  3. **Chat history**: products the assistant showed them in saved chats
     (weight 1)
- Products are compared on garment family, colors, theme words from the name
  (bulldog, hockey, Branford…) and search tags. Rare features count more than
  common ones, so "bulldog" outweighs "Yale," which is on almost everything.
- **Rules:** never recommend something they already own or have wish-listed,
  only items in stock, and at most 2 per garment family so the list isn't all
  hoodies.
- **Every pick has a reason**, shown on the card: "✨ Goes with your District
  Vit Hoodie Vintage Sailor Bulldog (in your closet)," "✨ Similar to Boola Boola
  T Shirt on your wish list," "✨ Because you looked at Sailing Left Chest Hoodie
  in chat."
- Guests and brand-new accounts get clearly labeled **Staff picks** instead.
- **Three places it shows up:**
  - The **Home** page "Recommended for you, \<name\>" section (the old fixed
    "Campus favorites" section became this).
  - The bottom of **My Closet**.
  - The **chat agent's new `recommend_for_me` tool**. "What would you recommend
    for me?" gets picks with reasons, and the agent can put all of them on the
    page using the Problem 7 page-results feature.
- `GET /api/recommendations` serves the website. It's plain Python over the
  catalogue (no AI call), so it's instant and costs nothing per page view.

### Why it helps
- **Shopper:** discovery without searching. Someone who owns the Sailor Bulldog
  hoodie sees the other vintage bulldog pieces right away, and the reason makes
  each pick feel considered rather than random.
- **Business:** more items per customer (cross-sell matching pieces). Picks are
  always in stock, so the shop never pushes something it can't sell. And it
  turns data the site already collects (closet, wish list, chats) into sales.

### Where to see it
- **Home page** while logged in as Test User: "Recommended for you, Test,"
  based on their closet, wish list and chats.
- **My Closet** → scroll down.
- **Chat:** "What would you recommend for me?" The agent names a couple of
  picks with reasons and the full list appears on the Products page under a
  "Recommended for you" banner.

---

## 4. Image Compression (backend / front end)

### What I added
- `backend/images.py` makes three compressed copies of each of the 102
  catalogue photos, stored in `data/products_optimized/`:

  | Version | Size and format | Used for |
  |---|---|---|
  | `card` | 360 px **WebP** | Product grids, chat cards, closet, wish list, recommendations |
  | `large` | 800 px **WebP** | The single-item product page |
  | `model` | 512 px JPEG | Any product photo sent to an AI vision model (fits one 512 px tile) |

- They're **built automatically when the server starts**, but only for
  missing or changed files. The first build took about 26 seconds, and later
  starts take about 0.3 seconds. The originals stay untouched.
- The product API now gives `image_url` (card), `image_url_large` and
  `image_url_original`. The website uses the card version everywhere except the
  product page, which uses the large version.
- Images are served with a **one-week browser cache header**, so moving between
  pages doesn't download them again.
- Cards have fixed image dimensions so the grid doesn't jump around while
  images load.

### Results (measured)

| | Before | After | Change |
|---|---|---|---|
| All 102 card images (the full Products page) | 3,603 KB | **595 KB** | **84% smaller** |
| Product-page images, all 102 | 3,603 KB | 2,314 KB | 36% smaller |
| Estimated vision-model input tokens to send all 102 photos* | 74,970 | **26,010** | **65% fewer** |

*Using the published high-detail image token formula for OpenAI GPT-4o-class
models: 85 tokens plus 170 per 512 px tile (`images.vision_tokens`). A 900 px
photo is 4 tiles (765 tokens). The 512 px version is 1 tile (255 tokens).

In the browser, the full Products page now loads only `/media/card/*.webp`
files. Measured after scrolling the whole grid: about 518 KB of images
downloaded.

### Why it helps
- **Shopper:** pages load faster, especially the 102-item Products page on a
  phone or busy campus Wi-Fi, and use far less mobile data.
- **Business:** less bandwidth to pay for and faster pages, which keeps
  shoppers browsing. On **AI cost**, being honest: the current chat agent works
  from text and doesn't send product photos to the model, so it doesn't save
  tokens today. But any image feature, such as "find a product like this
  photo" or the Homework 3 photo matcher, would send the `model` version
  (`images.image_for_model()`), which cuts image tokens by about two-thirds per
  photo.

### Where to see it
Anywhere a product image appears. Right-click an image → "Open image in new
tab": the URL is `/media/card/<name>.webp` on grids and
`/media/large/<name>.webp` on a product page. In the browser's developer tools
→ Network → Img, the files are a few KB each, and repeat visits are served from
the cache. To print the size report:
`cd backend && python images.py`.

---

## Verification

**Automated:** `backend/test_usability.py`, **29/29**, on a throwaway copy of the
database:
- Closet and wish list need a login. Adding twice keeps one row, unknown
  products and bad sizes are rejected, sold-out saved sizes are flagged, "I
  bought it" moves the item, and another shopper can't see or delete these
  items.
- Recommendations come from all three signals, never include owned or
  wish-listed items, only include in-stock items, give every pick a reason,
  keep at most 2 per garment family, and give guests staff picks.
- The agent's `recommend_for_me` fills the page and `add_to_wish_list` saves.
- Images are served as WebP, are much smaller than the originals, have the
  cache header, and all 102 × 3 versions exist.

The other test files still pass: `test_auth` 25/25, `test_tools` 11/11,
`test_agent` 13/13 and `test_memory` 22/22.

**In the running app** (logged in as Test User, 2026-10-18):

| Check | Result |
|---|---|
| Top bar shows **My Closet** and **♡ Wish List** when logged in | ✅ |
| Home: "Recommended for you, Test, based on 9 products from your chats," each card with a ✨ reason; images are `/media/card/*.webp` | ✅ |
| Boola Boola T Shirt page: size L → **♡ Save to wish list** → "♥ On your wish list (L)"; image is `/media/large/…webp` | ✅ |
| Sailor Bulldog Hoodie page: size M → **I own this** → "✓ In your closet (M)" | ✅ |
| Wish List: "2 items · $100.00 total"; Champion hoodie "Size M in stock," Boola Boola "**Size L is sold out**" | ✅ |
| **I bought it** on the Champion hoodie → "Moved … to your closet," and it appears on My Closet | ✅ |
| My Closet: 2 items with sizes and dates; recommendations now say "Goes with your … Sailor Bulldog (in your closet)" and "Similar to Boola Boola T Shirt on your wish list" | ✅ |
| Chat: "What would you recommend for me?" → names picks with closet-based reasons; Products page shows a **"Recommended for you" banner with 6 cards** | ✅ |
| Chat: "What's on my wish list, and is it in stock in my size?" → "Boola Boola T Shirt in L. It's sold out in L right now…" | ✅ |
| Chat on the Branford 1/4 Zip page: "Please add this to my wish list in a medium" → added; confirmed in stock in M at $72 (database: M = 20, $72) | ✅ |
| Products page: all 102 cards use `/media/card/*.webp`; about 518 KB of images downloaded for the whole grid (originals: 3.6 MB) | ✅ |
