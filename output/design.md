# Campus Customs — Storefront Design

**Problem 10.** What changed and why it should keep shoppers around and buying.
Log in as `test@campuscustoms.yale.edu` / `password` to see everything.

## Look and feel

| Change | Why it helps |
|---|---|
| **Yale Blue (#00356b) and white**, a bright "spirit" blue for energy, and **gold** only for things to act on (Shop the collection, Create Account, Check out, bag count, "Sneak peek") | Reads as Yale at a glance, and gold always means "click here," so the eye goes straight to buying actions |
| **Graduate** (collegiate varsity lettering) for headlines and the logo, **Outfit** for body text | Feels like a team store, not a template, while body text stays easy to read |
| **Bulldog mascot**: original SVG artwork (not an official Yale mark) in the logo, hero, chat button, chat avatar, footer, stylist animation and checkout success | Gives the store a friendly face shoppers remember, and makes the chat feel like a character |
| **Clear order on every page**: small uppercase label → big varsity headline → one main button | Shoppers always know what the page is and what to do next |
| **Product-first cards**: photos on a soft spotlight, zoom on hover, card lifts, price in bold blue, "Sold out" badge | Products are the hero: bigger, livelier photos are what sells apparel |

## Home page

- **Hero**: "Proudly show your **Yale pride!**" (gold accent with a small wiggle), a
  bobbing bulldog inside a slowly spinning ring, and three real products floating
  around it (clickable). Two buttons: **Shop the collection** and **💬 Ask our
  Stylist** (opens the chat). *Why:* spirit plus products right away, with two
  clear ways in.
- **Gold spirit ticker**: "Boola Boola ✦ Every day is spirit day ✦ Beat Harvard
  ✦ …" scrolling. *Why:* energy and school pride without taking space.
- **Shop by style**: 5 round category tiles (Hoodies, Crewnecks, Tees,
  Quarter-zips, Jackets & Fleece) that open the filtered Products page. *Why:*
  one click to the right rack.
- **Top picks with hover sneak peeks**: hover a card and a gold-bordered
  "👀 Sneak peek" panel opens with a larger photo, full description, every size
  (sold-out sizes struck through) and "🔥 Almost gone in XL, XXL." It flips left
  near the screen edge. *Why:* shoppers size up an item without leaving the
  page, and low-stock alerts add healthy urgency.
- Sections **fade up as you scroll**. *Why:* the page feels alive and pulls
  attention down to the next section.

## Navigation

- **Products ▾ hover menu**: categories with one-line blurbs, plus **top picks
  with a live sneak peek** (photo, price, sizes) that changes as you hover each
  item. *Why:* the best sellers are visible from every page.
- **Bag button** with a gold count badge that pops when something is added.
- On Products: **category pills** (All / Hoodies / Crewnecks / …) and a rounded
  search box. Top items there also get sneak peeks.

## Buying, with fun effects on the way to checkout

| Moment | Effect | Why |
|---|---|---|
| Pick a size | Big tappable size buttons; sold-out sizes are struck through and disabled; "🔥 Only 3 left in M" when low | No guessing what's available; scarcity nudges |
| **Add to bag** without a size | Size row shakes, "Pick your size first 👆" | Prevents a dead-end error |
| **Add to bag** | The product photo **flies into the bag icon**, and the badge pops | Instant, satisfying confirmation |
| ♡ Save to wish list | **Heart burst** | Rewards saving (and a saved item is a likely future sale) |
| I own this | Paw-print burst 🐾 | Keeps the closet fun to fill in |
| Bag drawer | Slides in with photos, quantities and subtotal; the **Check out** button glows gold | The next step is obvious |
| **Check out** | **Confetti + 🐾 burst**, winking bulldog, "Boola Boola, you're all set! 🎉" | Ends on a high. It says plainly that online payment is coming soon (show the bag at the counter), so nothing is faked |

All effects are skipped automatically for shoppers whose device asks for
reduced motion.

## Recommendations: "the stylist is thinking"

While picks load (at least 1.8 seconds), the **bulldog stylist** bobs with a
**spinning gold cogwheel** next to a **swinging clothes rack whose hangers flip
through real product photos**, and the captions rotate: "Peeking in your
closet… Matching colors and layers… Flipping through the racks…". Then the picks
**deal in one by one**, each with its reason. **✨ Restyle me** runs it again.
*Why:* it shows the picks are personal (it really uses closet, wish list and
chat history), and a short wait plus the reveal makes them feel considered, so
shoppers look at them.

## Product page: Complete the look

Under every product: **"Complete the look"**, with in-stock pieces to wear over
or under it, each with a styling tip ("Wear a tee underneath so you can lose
the hoodie indoors · matching vintage theme"). Pieces they already own come
first. There's also a link to ask the Stylist. *Why:* cross-selling, so one
hoodie becomes a hoodie and a tee.

## Chat: from search box to personal stylist

| Change | Why it helps |
|---|---|
| Renamed **Campus Customs Stylist**: bulldog avatar with a gold ring, "● Online · outfits, sizes & stock," blue gradient header | Feels like a person at the counter, not a form |
| Bulldog chat button with a pulsing ring, plus a one-time "Need a game-day look? Ask the Stylist! 🐾" bubble | Invites the conversation that leads to a sale |
| **Starter chips**: 🏈 Outfit for game day at the Bowl · 🎁 Gift for a parent · ☕ Cozy hoodie for class · ✨ What goes with what I own? | Nobody stares at an empty box; one tap starts a styling chat |
| Bouncing-dots typing indicator, bubbles that slide in, mini bulldog next to each reply | Smooth, alive conversation |
| **Personality (prompt)**: an excited reaction to their plan, 1–2 picks with how to wear them, then **one question** (size, how cold, style, who it's for) until it knows enough | Asking where and how they'll wear it leads to the right piece, so fewer returns and more confidence to buy |
| **New `suggest_outfit` tool**: layering rules (tees under quarter-zips, hoodies and jackets; hoodies and crewnecks under jackets), color matching (navy, white and gray go with anything) and theme matching (same college, sport or vintage bulldog), only in stock, closet pieces first | Pairing advice is grounded in real inventory, not invented, and it sells the second item |

**Live examples (real model, 2026-10-18):**
- *"I need a gift for my mom, she's visiting for Family Weekend"* → "Family
  Weekend is such a sweet occasion! I'd start with the Champion Mens Triumph
  Raglan Crew… or the District Vit Crewneck Vintage Bulldog… **what size does
  your mom usually wear**, and does she prefer classic Yale or bulldog style?"
- *"I'm a large, and I love the vintage bulldog look. It's going to be pretty
  cold."* → the Vintage Bulldog hoodie over the Vintage Shield tee, under the
  Divinity School fleece, "All three are available in L." The database confirms
  L stock of 15, 8 and 5. The full outfit went on the page as "Complete the
  look."
- On the Branford 1/4 Zip page, *"What would go well with this?"* → the Tri Blend
  Football tee underneath, or the Dry Zone long sleeve for warmth, and it
  remembered the shopping was for mom.

## Checked in the running app

Desktop and phone width (no sideways scrolling). Hero, ticker, category tiles,
sneak peeks (including the flip near the right edge), the Products hover menu,
the stylist-thinking animation and its reveal, size picker, the add-to-bag fly
animation and badge pop, heart burst, bag drawer, checkout confetti and paws,
Complete the look, the new chat look and starter chips, and the live stylist
conversations above. The frontend builds and lints clean, and all 100 backend
checks pass.

**Fixed during testing:**
- Hidden sneak-peek panels caused sideways scrolling.
- The checkout paw burst was aimed at a button that had already disappeared.
- Effect clean-up relied on a browser signal that never fires in background
  tabs.
- The bulldog's pointy ears looked like a cat's, so they're now folded "rose"
  ears.
- The first stylist reply didn't ask a question, so the prompt now spells out
  the reply shape.
