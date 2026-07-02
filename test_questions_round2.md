# DISH Assistant — test list (round 2)

Type each into the **"Ask anything…"** box. **Expect** = where it should land.
🛒 = you named a product/price, so the **PDF/video should show that exact product/price**.
🔗 = a multi-part question that stitches several guides into one walkthrough.

The quality gate runs on every build: a clean one **publishes**; a shaky one is **held for
review** with the exact step flagged — that's the system checking itself, not a failure.

## Products

| # | Question | Expect |
|---|----------|--------|
| 1 | add a spicy chicken wrap as a food for 9.50 and put it on the menu | Add product (Q1) 🛒 |
| 2 | change the price of 7-Up to 2.80 | Adjust price (Q2) 🛒 *(existing product)* |
| 3 | set Baileys to 6.50 euros | Adjust price (Q2) 🛒 *(existing product)* |
| 4 | add a passion fruit mojito as a drink for 8 and only show it during happy hour | Q1 + Q17 🔗🛒 |
| 5 | add a halloumi burger and mark its allergens | Q1 + Q6 🔗🛒 |
| 6 | flag the caesar salad as containing dairy and gluten | Allergens (Q6) |
| 7 | bundle a burger, fries and a drink into one combo | Composite (Q4) |
| 8 | give the flat white a PLU number | PLU (Q11) |
| 9 | create a product group called Mocktails | Product group (Q12) |
| 10 | run a happy hour 25% off | Promotions (Q18) |
| 11 | stop the kitchen tickets printing on their own | Ticket printing (Q21) |
| 12 | lower the VAT on food | VAT for food (Q24) |
| 13 | build a 4-course fixed-price menu | Fixed-price menu (Q16) |
| 14 | add a second barcode to a product so I can scan it | Product codes (Q25) |

## Self-service

| # | Question | Expect |
|---|----------|--------|
| 15 | let customers pay when they pick up their order | Pay on pickup (Q26) |
| 16 | set the opening hours for self-service | Time schedules (Q27) |
| 17 | change how the QR shop looks | QR shop appearance (Q28) |
| 18 | recommend add-ons at the kiosk checkout | Cross-selling (Q29) |
| 19 | add a legal imprint to the web shop | Imprint (Q30) |
| 20 | personalise the kiosk screen | Kiosk appearance (Q31) |
| 21 | make QR codes for table ordering | Create QR codes (Q37) |
| 22 | enable pagers so guests know their food is ready | Buzzer/pager (Q38) |

## Payment

| # | Question | Expect |
|---|----------|--------|
| 23 | add a cash payment method | Payment methods (Q40) |
| 24 | manage my card machines | EFT devices (Q41) |
| 25 | set up a portable card terminal that works on its own | Stand-alone EFT (Q42) |
| 26 | let regulars pay on a tab / on account | On account (Q43) |
| 27 | configure a smart voucher | Smart Voucher (Q44) |

---

**Check for each:** right section + guide · steps make sense · for 🛒 questions the PDF/video
shows *your* product & price · gate says publish (or flags the one step to glance at).
