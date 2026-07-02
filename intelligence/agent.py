"""
agent.py - the deterministic "brain" for the DISH Docs assistant.

Given a free-form, randomly phrased question like
    "I want to add apple juice cocktail as a drink and bring it to the menu"
this module:
  1. EXTRACTS the user's parameters  -> name="Apple Juice Cocktail", type="drink",
     price=auto (sensible default when none is given)  [this is the "smartness"]
  2. ROUTES the question to the right guide(s) out of the 25 (Q1..Q25)
  3. MERGES multiple guides into ONE answer when a question spans several
  4. Knows when to ASK a clarifying question, and when it has NO matching guide
  5. Exposes recipe_vars() so the capture/demo uses the user's product
     (e.g. it creates "Apple Juice Cocktail" instead of "Sparkling Water")

It is 100% deterministic and dependency-free, so it can be unit-tested offline and
behaves the same every run. When a model key is configured (intelligence.llm.available()),
answer() can optionally use it to polish the prose - but routing and parameters always
come from this deterministic core, so behaviour stays predictable and testable.
"""
import json
import re
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REC = ROOT / "recipes"

# ──────────────────────────────────────────────────────────────────────────────
# Category / type understanding: the word the user says -> real DISH product-group
# preference list the capture engine will try in order.
# ──────────────────────────────────────────────────────────────────────────────
DRINK_WORDS = {
    "drink", "drinks", "beverage", "beverages", "cocktail", "cocktails", "mocktail",
    "juice", "soda", "softdrink", "water", "coffee", "tea", "beer", "wine", "rose",
    "smoothie", "lemonade", "cola", "coke", "shake", "milkshake", "martini",
    "aperitif", "spritz", "espresso", "cappuccino", "latte", "macchiato", "mocha",
    "lassi", "mojito", "ale", "ipa", "lager", "stout", "cider", "pilsner", "shandy",
    "gin", "vodka", "whisky", "whiskey", "rum", "tequila", "brandy", "cognac",
    "liqueur", "prosecco", "champagne", "sangria", "margarita", "negroni", "bellini",
    "daiquiri", "cosmopolitan", "colada", "americano", "cortado", "ristretto",
    "chai", "matcha", "kombucha", "frappe", "frappuccino", "cordial", "squash",
    "tonic", "seltzer", "punch", "nectar", "kefir", "brew",
}
FOOD_WORDS = {
    "food", "dish", "meal", "snack", "starter", "main", "side", "dessert",
    "burger", "hamburger", "cheeseburger", "patty", "pizza", "pasta", "spaghetti",
    "lasagna", "lasagne", "ravioli", "gnocchi", "tortellini", "risotto", "noodle",
    "noodles", "ramen", "pho", "udon", "salad", "sandwich", "sub", "panini",
    "baguette", "wrap", "bowl", "soup", "stew", "chowder", "broth", "casserole",
    "fries", "chips", "wedges", "mash", "nachos", "taco", "tacos", "burrito",
    "quesadilla", "enchilada", "fajita", "kebab", "gyro", "shawarma", "falafel",
    "hummus", "dumpling", "dumplings", "gyoza", "sushi", "sashimi", "maki",
    "tempura", "curry", "tikka", "masala", "korma", "biryani", "satay", "paella",
    "rice", "omelette", "omelet", "frittata", "quiche", "pancake", "pancakes",
    "waffle", "waffles", "crepe", "croissant", "bagel", "toast", "muffin", "scone",
    "donut", "doughnut", "brownie", "cookie", "biscuit", "cake", "cheesecake",
    "pie", "tart", "tiramisu", "gelato", "sorbet", "pudding", "custard", "parfait",
    "chicken", "beef", "pork", "lamb", "turkey", "duck", "bacon", "ham", "sausage",
    "sausages", "steak", "schnitzel", "meatball", "meatballs", "nugget", "nuggets",
    "wing", "wings", "ribs", "fillet", "filet", "cutlet", "chop", "chops",
    "fish", "salmon", "tuna", "cod", "haddock", "prawn", "prawns", "shrimp",
    "scampi", "calamari", "mussels", "oysters", "lobster", "crab", "egg", "eggs",
    "margherita", "pepperoni", "cheese", "guacamole", "salsa", "platter",
    "porridge", "oatmeal", "granola", "hotdog", "poke", "gratin",
}
# Multi-word items, checked before single tokens (so "hot chocolate" -> drink, not the
# food token "chocolate"; "fish and chips" stays one food, etc.).
DRINK_PHRASES = ("soft drink", "flat white", "hot chocolate", "iced coffee",
                 "cold brew", "green tea", "iced tea", "ice tea", "gin and tonic",
                 "pale ale", "still water", "sparkling water", "energy drink",
                 "hot drink", "house wine", "draft beer", "draught beer")
FOOD_PHRASES = ("fish and chips", "ham and cheese", "mac and cheese", "ice cream",
                "hot dog", "surf and turf", "bangers and mash", "spring roll",
                "egg roll", "dim sum", "club sandwich", "pad thai", "chicken wings")
CATEGORY_PREF = {
    "drink": ["Soft Drinks", "Drinks", "Dranken", "Food", "Miscellaneous"],
    "food":  ["Food", "Dranken", "Drinks", "Miscellaneous"],
    "other": ["Miscellaneous", "Food", "Drinks"],
}
# A sensible auto-price when the user does not give one ("price you can set any").
DEFAULT_PRICE = {"drink": "3.50", "food": "8.50", "other": "5.00"}

# The 14 EU allergens, with the everyday words people type mapped to the DISH label,
# so "mark it as containing milk and sesame" -> ["Milk", "Sesame"]. The product's
# allergens then flow into the answer (and the recipe var) instead of a generic note.
ALLERGEN_WORDS = {
    "gluten": "Gluten", "wheat": "Gluten", "coeliac": "Gluten", "celiac": "Gluten",
    "milk": "Milk", "dairy": "Milk", "lactose": "Milk",
    "egg": "Eggs", "eggs": "Eggs",
    "fish": "Fish",
    "crustacean": "Crustaceans", "crustaceans": "Crustaceans", "shellfish": "Crustaceans",
    "prawn": "Crustaceans", "prawns": "Crustaceans", "shrimp": "Crustaceans", "crab": "Crustaceans", "lobster": "Crustaceans",
    "mollusc": "Molluscs", "molluscs": "Molluscs", "mussel": "Molluscs", "mussels": "Molluscs",
    "oyster": "Molluscs", "oysters": "Molluscs", "squid": "Molluscs", "snail": "Molluscs",
    "peanut": "Peanuts", "peanuts": "Peanuts",
    "nut": "Nuts", "nuts": "Nuts", "tree nut": "Nuts", "almond": "Nuts", "almonds": "Nuts",
    "hazelnut": "Nuts", "hazelnuts": "Nuts", "walnut": "Nuts", "walnuts": "Nuts",
    "cashew": "Nuts", "cashews": "Nuts", "pecan": "Nuts", "pistachio": "Nuts",
    "soy": "Soy", "soya": "Soy", "soybean": "Soy", "soybeans": "Soy",
    "sesame": "Sesame",
    "celery": "Celery",
    "mustard": "Mustard",
    "sulphite": "Sulphites", "sulfite": "Sulphites", "sulphites": "Sulphites", "sulfites": "Sulphites",
    "lupin": "Lupin",
}


def _join_and(items):
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _extract_allergens(nlq):
    """Pull named allergens out of the query - only when there is allergen context
    (so 'add a fish dish' alone doesn't get tagged as the allergen Fish)."""
    if not re.search(r"\b(allergen|allergens|contain|contains|containing|free\s*from|"
                     r"intolerant|made\s+with|has\b|with\b)\b", nlq):
        return []
    out = []
    for w, canon in ALLERGEN_WORDS.items():
        if re.search(r"\b%s\b" % re.escape(w), nlq) and canon not in out:
            out.append(canon)
    return out

# Words that, as the object of "add", are NOT a product (they're another feature).
# If ANY token of the captured name is one of these, it's not a product creation.
NON_PRODUCT_OBJECTS = {
    "allergen", "allergens", "additive", "additives", "code", "codes", "barcode",
    "barcodes", "ean", "plu", "promotion", "promotions", "promo", "discount",
    "discounts", "menu", "menus", "submenu", "sub-menu", "submenus",
    "group", "groups", "category", "categories", "price", "prices", "level",
    "levels", "set", "sets", "period", "periods", "profile", "profiles",
    "restriction", "restrictions", "composite", "composites", "store", "stores",
    "deal", "combo", "bundle", "rule", "packaging", "info", "information",
    "available", "during", "only", "offer", "special",
    "it", "that", "them", "this", "stop", "go",
}

# Features that can ride along with a product creation but must never be the
# PRIMARY guide when the user is actually creating a product.
SECONDARY_ONLY = {6, 11, 17, 18, 24, 25}

# Guides whose own steps already include assigning a product to a menu, so a
# "...and put it on the menu" clause should NOT add a separate menu guide.
MENU_IS_BUILTIN = {1}

# Guides that BUILD a menu. When one of these is the primary intent, a bare
# "lunch menu"/"dinner menu" is the NAME of the menu being built, not a request
# to time-restrict it, so the weak Q17 triggers below should be ignored. Strong
# time signals ("during lunch", "only available", ...) still merge Q17.
MENU_BUILD_GUIDES = {15, 16, 19}
WEAK_17 = {"lunch menu", "dinner menu", "breakfast menu"}

# ──────────────────────────────────────────────────────────────────────────────
# Routing knowledge: per-guide weighted phrases. Higher weight = more specific.
# Curated from the real guide titles + captured step captions.
# ──────────────────────────────────────────────────────────────────────────────
PROFILES = {
    1:  [("add a product", 5), ("create a product", 5), ("new product", 4),
         ("add product", 5), ("add an item", 4), ("add a drink", 4),
         ("add a dish", 4), ("add a new", 3), ("create product", 5),
         ("assign it to a menu", 4), ("add it to a menu", 4), ("add to a menu", 4),
         ("bring it to the menu", 4), ("bring to menu", 4), ("put it on the menu", 4),
         ("put on the menu", 4), ("place it on the menu", 4), ("onto the menu", 3),
         ("on the drinks menu", 4), ("on the food menu", 4), ("on the bar menu", 4),
         ("to the drinks menu", 4), ("to the food menu", 4),
         ("as a drink", 3), ("as a food", 3), ("as a dish", 3),
         ("menu item", 4), ("new menu item", 5), ("create a menu item", 5),
         ("a menu item for", 4)],
    2:  [("list view", 6), ("in the list", 4), ("edit in the list", 6),
         ("quick edit", 5), ("inline", 5), ("bulk edit", 5), ("at once", 4),
         ("several products", 5), ("multiple products", 5), ("edit the name", 3),
         ("product names", 4), ("change product names", 5), ("change the name", 4),
         ("overview list", 4), ("in the overview", 4), ("rename", 4)],
    3:  [("sales restriction", 6), ("restriction", 5), ("restrictions", 5),
         ("restrict", 5), ("sales and restrictions", 6), ("assign sales", 5),
         ("sales restrictions", 6)],
    4:  [("composite", 6), ("composites", 6), ("combo", 5), ("combo deal", 6),
         ("bundle", 6), ("meal deal", 5), ("multiple articles", 5),
         ("combine products", 5), ("link multiple products", 6),
         ("multiple products to one", 6), ("bundle multiple", 7),
         ("into one item", 6), ("products into one", 6), ("into one", 5)],
    5:  [("search and filter", 6), ("search function", 5), ("filter function", 6),
         ("find a product", 5), ("find products", 5), ("search for a product", 5),
         ("search for an article", 5), ("look for a product", 5), ("locate a product", 5),
         ("filter products", 5)],
    6:  [("allergen", 6), ("allergens", 6), ("additive", 6), ("additives", 6),
         ("allergy", 5), ("allergies", 5), ("gluten", 5), ("nuts", 4),
         ("dietary", 4), ("assign allergens", 6)],
    7:  [("adjust product details", 6), ("adjusting product details", 6),
         ("edit a product", 4), ("edit product", 4), ("change product details", 6),
         ("modify a product", 5), ("update a product", 5), ("change a product", 4),
         ("edit product information", 5), ("product information", 3),
         ("change the details", 4), ("edit the product", 4),
         ("update the details", 5), ("update an existing", 5), ("existing product", 4),
         ("update product details", 6), ("edit the details", 6), ("edit details", 5),
         ("edit an existing", 5), ("details of an existing", 5), ("modify the details", 5),
         ("of an existing", 3)],
    8:  [("regime forfettario", 8), ("forfettario", 8), ("flat rate tax", 6),
         ("flat-rate tax", 6), ("italian tax", 6), ("simplified tax", 5)],
    9:  [("production order", 7), ("prep order", 6), ("preparation order", 6),
         ("production sequence", 5), ("kitchen order", 4), ("order of production", 5)],
    10: [("manage products", 6), ("managing products", 6), ("manage and add", 5),
         ("product management", 5), ("manage my products", 6),
         ("manage all my products", 6)],
    11: [("plu", 7), ("price look up", 6), ("price look-up", 6), ("assign a plu", 7),
         ("plu code", 7), ("plu number", 7)],
    12: [("product group", 6), ("product groups", 6), ("add a product group", 7),
         ("new product group", 7), ("add a group", 5), ("new group", 5),
         ("add a category", 5), ("new category", 5), ("create a group", 5),
         ("create a category", 5)],
    13: [("price set", 7), ("price sets", 7), ("pricing rule", 6),
         ("add set", 5), ("pricing rule set", 7), ("price management set", 6)],
    14: [("price level", 7), ("price levels", 7), ("add price level", 7),
         ("manage price level", 7)],
    15: [("derived menu", 7), ("derived menus", 7), ("child menu", 5),
         ("base menu", 5), ("menu derived from", 6)],
    16: [("french menu", 7), ("fixed-price menu", 7), ("fixed price menu", 7),
         ("prix fixe", 7), ("set-price menu", 6), ("set price menu", 6),
         ("course menu", 5), ("3 course", 4), ("three course", 4),
         ("with a fixed price", 6), ("fixed price", 4), ("fixed-price", 4)],
    17: [("time period", 6), ("time periods", 6), ("time restriction", 7),
         ("time restrictions", 7), ("only during", 6), ("available during", 6),
         ("during lunch", 6), ("during dinner", 6), ("during breakfast", 6),
         ("during happy hour", 6), ("show during", 6), ("only show it during", 7),
         ("only show it at", 7), ("only show", 5), ("show it at", 6),
         ("only available at", 7), ("only available", 5),
         ("at certain times", 5), ("specific times", 5),
         ("schedule the menu", 6), ("add a period", 6),
         ("dinner time", 6), ("lunch time", 6), ("breakfast time", 6)],
    18: [("promotion", 7), ("promotions", 7), ("promo", 6), ("discount", 6),
         ("special offer", 6), ("% off", 5), ("percent off", 5),
         ("happy hour discount", 7), ("deal on", 4), ("add a discount", 7),
         ("happy hour", 7)],
    19: [("arrange menu", 6), ("arranging menus", 6), ("organise the menu", 6),
         ("organize the menu", 6), ("rearrange", 6), ("sub-menu", 5), ("submenu", 5),
         ("submenus", 5), ("manage menus", 5), ("managing menus", 5),
         ("menu structure", 6), ("add a submenu", 6), ("order the menu", 5)],
    20: [("price level to a store", 7), ("price levels to a store", 7),
         ("assign price level to store", 7), ("store price level", 6),
         ("price level for the store", 7), ("link a price level", 6)],
    21: [("ticket printing", 7), ("ticket print", 6), ("stop printing", 7),
         ("disable printing", 7), ("disable automated", 6), ("automatic ticket", 7),
         ("automated ticket", 7), ("kitchen ticket", 6), ("stop tickets", 7),
         ("printing automatically", 7), ("turn off printing", 7),
         ("printing tickets", 6), ("print tickets", 6), ("auto print", 6),
         ("auto printing", 6), ("from printing", 5), ("printing ticket", 6),
         ("disable ticket", 7), ("tickets to print", 6)],
    22: [("menus for specific areas", 7), ("menu for an area", 6),
         ("area and time", 6), ("areas and times", 7), ("assign menu to area", 7),
         ("menu to an area", 7), ("menu to a specific area", 7), ("specific area at", 7),
         ("area at certain times", 7), ("for specific areas", 7),
         ("terminal menu", 5), ("menu per area", 6), ("facility menu", 5),
         ("which menu shows", 6), ("specific area", 6)],
    23: [("packaging profile", 7), ("packaging profiles", 7), ("packaging", 6),
         ("deposit", 5), ("takeaway packaging", 7), ("container deposit", 6),
         ("add a packaging", 7)],
    24: [("vat level", 6), ("change the vat", 6), ("change vat", 6), ("vat for food", 7),
         ("food vat", 7), ("vat rate for food", 7), ("tax level for food", 7),
         ("btw", 5), ("change the tax on food", 7), ("vat", 5), ("vat on food", 7),
         ("vat rate", 6), ("tax on food", 6), ("food tax", 6), ("lower the vat", 6)],
    25: [("product code", 6), ("product codes", 7), ("multiple codes", 7),
         ("barcode", 6), ("barcodes", 6), ("ean", 6), ("scan code", 5),
         ("add a code", 6), ("add codes", 6), ("multiple product codes", 7),
         ("extra code", 5), ("scan", 4), ("scannable", 5), ("at the till", 4),
         ("scan my", 5), ("scan the", 4)],
    # ---- Self-service (26-38) ----
    26: [("pay on pick up", 7), ("pay on pickup", 7), ("payment on pickup", 7),
         ("payment on pick up", 7), ("pickup payment", 6), ("pay when you pick up", 7),
         ("pay when they pick up", 7), ("pay at pickup", 7), ("pay at pick up", 7),
         ("pay on collection", 7), ("pay when picking up", 7), ("pay at collection", 7),
         ("when they pick up their order", 6), ("when they collect their order", 6),
         ("pay for pickup", 6), ("pay for pick up", 6)],
    27: [("time schedule", 6), ("time schedules", 6), ("self-service time", 6),
         ("self service time schedule", 7), ("opening hours schedule", 5),
         ("schedule for self-service", 6), ("opening hours", 6), ("opening times", 6),
         ("set the hours", 6), ("self-service hours", 6), ("self service hours", 6),
         ("operating hours", 6), ("business hours", 5), ("hours my self-service", 6),
         ("hours my self service", 6), ("when self-service is open", 6)],
    28: [("appearance of the self-service qr shop", 8), ("qr shop appearance", 7),
         ("self-service qr shop", 7), ("appearance of the qr shop", 7),
         ("customise the qr shop", 6), ("customize the qr shop", 6),
         ("look of the qr shop", 6), ("qr shop look", 6), ("style the qr shop", 6),
         ("restyle the qr shop", 6), ("qr shop design", 6), ("change the qr shop", 6),
         ("how the qr shop looks", 6), ("personalise the qr shop", 6),
         ("personalize the qr shop", 6), ("qr shop branding", 6)],
    29: [("cross-selling", 7), ("cross selling", 7), ("cross-sell", 6), ("cross sell", 6),
         ("cross-selling products", 7), ("cross-sell at checkout", 7), ("upsell at checkout", 6),
         ("upsell", 6), ("up-sell", 6), ("suggest extra items", 6), ("suggest add ons", 6),
         ("suggest add-ons", 6), ("extra items at checkout", 6), ("recommend extra items", 6),
         ("offer extra items", 6), ("suggest more items", 6)],
    30: [("imprint", 7), ("legal notice", 6), ("imprint for web shops", 7),
         ("imprint for the qr", 7), ("set up the imprint", 7)],
    31: [("appearance of the kiosk", 8), ("kiosk appearance", 7), ("customise the kiosk", 6),
         ("customize the kiosk", 6), ("personalise the kiosk", 6), ("personalize the kiosk", 6),
         ("look of the kiosk", 6), ("kiosk look", 6), ("kiosk screen", 5), ("kiosk design", 6),
         ("style the kiosk", 6), ("restyle the kiosk", 6), ("change the kiosk", 5),
         ("how the kiosk looks", 6), ("change how the kiosk looks", 7), ("kiosk branding", 6)],
    32: [("settings for dish payment", 8), ("dish payment settings", 7),
         ("change dish payment", 6), ("payment site", 6)],
    33: [("random spot checks", 8), ("spot checks", 7), ("spot check", 6),
         ("grab and go checks", 6), ("self-service pos checks", 6)],
    34: [("webshop", 7), ("web shop", 6), ("personalise the webshop", 7),
         ("personalize the webshop", 7), ("adjust the webshop", 7), ("customise the webshop", 7)],
    35: [("link two different menus", 8), ("two different menus in the kiosk", 8),
         ("eat-in or takeaway menu", 7), ("eat in or takeaway", 6), ("link two menus", 7),
         ("kiosk eat-in takeaway", 6), ("eat-in and takeaway", 6), ("eat in and takeaway", 6),
         ("two menus in the kiosk", 8), ("menus in the kiosk", 6),
         ("takeaway menu in the kiosk", 7), ("link a menu in the kiosk", 6),
         ("different menus in the kiosk", 7)],
    36: [("reorder via qr", 8), ("reorder via qr code on the table", 8), ("reordering via qr", 7),
         ("qr code on the table", 6), ("reorder qr", 6)],
    37: [("create qr codes", 7), ("creating qr codes", 7), ("qr codes for self-service", 8),
         ("generate qr codes", 7), ("qr code for self service", 7), ("make qr codes", 6)],
    38: [("buzzer", 7), ("pager", 7), ("buzzer support", 7), ("pager support", 7),
         ("buzzer pager", 7), ("buzzer for the kiosk", 7)],
    # ---- Payment (39-44) ----
    39: [("pagamento non riscosso", 9), ("non riscosso", 8)],
    40: [("payment method", 6), ("payment methods", 6), ("add a payment method", 7),
         ("add payment method", 7), ("manage payment methods", 7), ("payment menu", 6),
         ("payment menus", 6), ("new payment method", 7)],
    41: [("eft device", 7), ("eft devices", 7), ("manage eft", 7), ("managing eft", 7),
         ("eft terminal", 6), ("payment terminal device", 6), ("card machine", 5),
         ("card machines", 6), ("card readers", 6), ("card terminals", 6)],
    42: [("stand-alone eft", 8), ("standalone eft", 8), ("stand alone eft", 8),
         ("stand-alone terminal", 7), ("standalone terminal", 7), ("stand-alone eft terminal", 8),
         ("card reader", 5), ("works on its own", 6), ("on its own", 4),
         ("standalone card reader", 7), ("portable card reader", 6),
         ("standalone card machine", 7), ("card reader on its own", 7)],
    43: [("on account", 7), ("pay on account", 7), ("on-account", 7),
         ("account payment method", 7), ("on account payment", 7)],
    44: [("smart voucher", 8), ("smart vouchers", 8), ("configure smart voucher", 8),
         ("voucher payment method", 7)],
}

# Secondary intents: distinct add-on features that can ride along with a primary
# request and trigger a MERGED answer.  {qid: [(phrase, _), ...]}
SECONDARY = {
    17: [("only during", 1), ("during lunch", 1), ("during dinner", 1),
         ("during breakfast", 1), ("only show it during", 1), ("at lunch", 1),
         ("at dinner", 1), ("time period", 1), ("time restriction", 1),
         ("only available", 1), ("certain times", 1), ("specific times", 1),
         ("lunch menu", 1), ("dinner menu", 1), ("breakfast menu", 1)],
    6:  [("allergen", 1), ("allergens", 1), ("additive", 1), ("additives", 1),
         ("allergy", 1), ("gluten", 1)],
    18: [("discount", 1), ("promotion", 1), ("promo", 1), ("% off", 1),
         ("special offer", 1)],
    11: [("plu", 1)],
    25: [("barcode", 1), ("ean", 1), ("product code", 1), ("product codes", 1)],
    24: [("food vat", 1), ("vat for food", 1)],
}

# Price-change ambiguity: a bare "change the price" could mean three guides.
PRICE_AMBIGUOUS_OPTIONS = [
    {"qid": 2,  "label": "Edit one product's price directly in the list view"},
    {"qid": 13, "label": "Create/adjust a price SET (a pricing rule)"},
    {"qid": 14, "label": "Create/adjust a price LEVEL (e.g. takeaway pricing)"},
]


# ──────────────────────────────────────────────────────────────────────────────
def _norm(s):
    s = (s or "").lower()
    s = s.replace("’", "'").replace("&", " and ")
    s = re.sub(r"[^a-z0-9%' ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


_CLAUSE_SPLIT = re.compile(r"\s*(?:,|;|&|\bas well as\b|\bplus\b|\balso\b|\bthen\b|\band\b)\s*", re.I)

def _clauses(query):
    """Split a request into sub-requests on natural conjunctions ("and"/"then"/","/...), so
    each part can be routed independently. This is what makes EVERY guide mergeable without
    a hardcoded list of allowed combinations - the words decide, not a fixed table."""
    return [c.strip() for c in _CLAUSE_SPLIT.split(query or "") if c and c.strip()]


def _catalog():
    """{qid: {title, steps:[captions]}} read from the real recipe scripts."""
    out = {}
    for fp in sorted(glob.glob(str(REC / "Q*_script.json"))):
        try:
            d = json.loads(Path(fp).read_text(encoding="utf-8"))
        except Exception:
            continue
        qid = d.get("id")
        if qid is None:
            m = re.search(r"Q0*(\d+)_script", fp)
            qid = int(m.group(1)) if m else None
        if qid is None:
            continue
        title = d.get("workflow_title") or d.get("title") or ("Question %d" % qid)
        steps = [s.get("caption", "").strip() for s in d.get("steps", []) if s.get("caption")]
        out[qid] = {"title": title, "steps": steps}
    return out


# ──────────────────────────────────────────────────────────────────────────────
#  PARAMETER EXTRACTION  ("the smartness")
# ──────────────────────────────────────────────────────────────────────────────
_PRICE_RE = re.compile(
    r"(?:€|eur|euro[s]?\s*|\$|£|price\s*(?:of|is|=|:)?\s*|for\s+|at\s+|costs?\s+|priced\s+(?:at\s+)?)"
    r"(\d+(?:[.,]\d{1,2})?)|(\d+(?:[.,]\d{1,2})?)\s*(?:€|eur|euro[s]?|dollars?|pounds?)",
    re.I)

_TYPE_AS_RE = re.compile(r"\bas\s+(?:a|an)\s+([a-z][a-z\- ]{1,20})", re.I)

# "add/create/make/set up [a/an] <NAME> [as a ...|to ...|for ...|with ...|priced ...]"
_NAME_RE = re.compile(
    r"\b(?:add|create|make|set\s+up|register|insert|put(?:\s+in)?|wanna\s+add|want\s+to\s+add)\s+"
    r"(?:a\s+new\s+|a\s+|an\s+|the\s+|my\s+)?"
    r"(?:product\s+(?:called|named)\s+|item\s+(?:called|named)\s+|"
    r"(?:called|named)\s+)?"
    r"([a-z0-9][a-z0-9'\- ]*?)"
    # End the name at a clause/feature word. NOTE: a bare "and" no longer ends the name —
    # only "and <action>" does — so compound names like "fish and chips", "gin and tonic"
    # and "ham and cheese" survive, while "...and put it on the menu" still splits.
    r"(?=\s+(?:as\b|to\b|onto\b|on\b|in\b|into\b|for\b|with\b|priced?\b|that\b|which\b|"
    r"containing\b|contains\b|contain\b|having\b|made\s+with\b|allergen"
    r"|and\s+(?:put|add|adds|assign|assigns|set|sets|make|makes|create|creates|bring|brings|"
    r"place|places|give|gives|tick|mark|marks|register|insert|enable|enables|also|then|"
    r"it\b|its\b|them\b|this\b|that\b))|[.,;]|$)",
    re.I)


def _detect_type(text, name=""):
    """drink / food / other. Matches whole WORDS (not substrings) so 'steak' is no longer
    read as the drink 'tea', and 'chocolate' is not read as 'cola'. Known multi-word items
    are checked first so e.g. 'hot chocolate' is a drink and 'fish and chips' is food."""
    blob = _norm(text + " " + name)
    for ph in DRINK_PHRASES:
        if ph in blob:
            return "drink"
    for ph in FOOD_PHRASES:
        if ph in blob:
            return "food"
    toks = set(blob.split())
    if toks & DRINK_WORDS:
        return "drink"
    if toks & FOOD_WORDS:
        return "food"
    return "other"


def _clean_name(raw):
    raw = re.sub(r"\b(a|an|the|new|my)\b", " ", raw, flags=re.I)
    raw = re.sub(r"\s+", " ", raw).strip(" '-")
    raw = re.sub(r"\b(product|item)$", "", raw, flags=re.I).strip()
    return " ".join(w.capitalize() if not w.isupper() else w for w in raw.split())


def extract_params(query):
    """Return the structured details the demo/answer should use."""
    q = query or ""
    nlq = _norm(q)
    p = {"product_name": None, "type": "other", "price": None,
         "price_auto": False, "category_pref": None, "is_add": False,
         "menu": None, "raw": q}

    # ----- name + "is this an add-a-product request?" -----
    m = _NAME_RE.search(q)
    if m:
        cand = m.group(1).strip()
        # Strip a trailing price/quantity phrase that leaked into the name, e.g.
        # "cappuccino of 5 euro" -> "cappuccino" (the price is parsed separately below).
        cand = re.sub(
            r"\s+(?:of|for|at|priced(?:\s+at)?|costs?|@)?\s*[€$£]?\s*\d+(?:[.,]\d{1,2})?"
            r"\s*(?:euros?|eur|dollars?|pounds?|cents?|bucks?|€|\$|£)?\s*$",
            "", cand, flags=re.I).strip()
        cand_tokens = set(_norm(cand).split())
        if cand_tokens and not (cand_tokens & NON_PRODUCT_OBJECTS) and len(cand) >= 2:
            name = _clean_name(cand)
            if name and not (set(_norm(name).split()) & NON_PRODUCT_OBJECTS):
                p["product_name"] = name
                p["is_add"] = True

    # ----- type / category -----
    t = None
    mt = _TYPE_AS_RE.search(q)
    if mt:
        t = _detect_type(mt.group(1))
    if not t or t == "other":
        t = _detect_type(q, p["product_name"] or "")
    # Smart fallback: if the words can't tell (still "other") and we're ADDING a named
    # product, ask the model whether it's food / drink / other - so the new product lands
    # in the right group (e.g. "Baileys" -> drink) instead of always "Miscellaneous".
    if p["is_add"] and t == "other" and p["product_name"]:
        try:
            from intelligence import llm
            if llm.available():
                a = (llm.ask_text(
                    "Classify this restaurant menu item as exactly one word - food, drink, "
                    "or other: \"%s\"" % p["product_name"],
                    system="Reply with one word only: food, drink, or other.",
                    max_tokens=4) or "").strip().lower()
                if a in ("food", "drink"):
                    t = a
        except Exception:
            pass
    p["type"] = t
    p["category_pref"] = CATEGORY_PREF.get(t, CATEGORY_PREF["other"])

    # ----- price -----
    pm = _PRICE_RE.search(q)
    if pm:
        val = pm.group(1) or pm.group(2)
        if val:
            p["price"] = ("%.2f" % float(val.replace(",", ".")))
    if not p["price"]:
        p["price"] = DEFAULT_PRICE.get(t, DEFAULT_PRICE["other"])
        p["price_auto"] = True

    # ----- menu name (optional) -----
    mm = re.search(r"\b(?:on|to|onto|in)\s+the\s+([a-z][a-z ]*?)\s+menu\b", q, re.I)
    if mm:
        p["menu"] = _clean_name(mm.group(1))

    # ----- price-edit product ("change the price of water to 20") -----
    # "change/set/make ..." aren't add-verbs, so _NAME_RE misses the product. Capture it
    # here too, so the BUILD (which calls extract_params) feeds the product + amount into
    # the recording's {NAME}/{PRICE} variables for every phrasing, not just "add ...".
    if not p["product_name"]:
        try:
            pe_name, pe_amt = _price_edit(q)
        except Exception:
            pe_name, pe_amt = None, None
        if pe_name:
            p["product_name"] = pe_name
            if pe_amt:
                p["price"] = pe_amt
                p["price_auto"] = False

    # ----- named allergens (e.g. "...containing milk and sesame") -----
    p["allergens"] = _extract_allergens(nlq)

    return p


# ──────────────────────────────────────────────────────────────────────────────
#  ROUTING
# ──────────────────────────────────────────────────────────────────────────────
def _phrase_in(phrase, nlq):
    """True if a phrase is present in the (already normalised) query text.
    The phrase is normalised the SAME way as the query so hyphenated phrases
    ("self-service qr shop", "stand-alone eft") still match the de-hyphenated text.
    Short acronyms ("ean", "plu", "vat", "btw") must match as WHOLE words, otherwise
    they hit inside unrelated words (e.g. "ean" inside "p-ean-uts" sent an allergen
    question to the barcode guide). Longer phrases keep substring matching so
    morphological variants ("nuts" in "peanuts") still work."""
    pn = _norm(phrase)
    if not pn:
        return False
    if len(pn) <= 3:
        return re.search(r"\b%s\b" % re.escape(pn), nlq) is not None
    return pn in nlq


def _score_guides(nlq):
    scores = {}
    for qid, phrases in PROFILES.items():
        s = 0.0
        for phrase, w in phrases:
            if _phrase_in(phrase, nlq):
                s += w * (1.0 + 0.4 * _norm(phrase).count(" "))
        if s:
            scores[qid] = round(s, 2)
    return scores


def _is_price_change(nlq):
    # "fixed price"/"price menu" are menu features, not a price-change request.
    if "fixed price" in nlq or "fixed-price" in nlq or "price menu" in nlq:
        return False
    pricey = ("price" in nlq or "cost" in nlq or "costs" in nlq or "how much" in nlq)
    return bool(
        re.search(r"\b(change|update|adjust|edit|modify)\b", nlq)
        and pricey
        and not re.search(r"\b(add|create|make|new|set\s*up)\b", nlq)
        and not any(k in nlq for k in ("price level", "price set", "price levels",
                                       "price sets", "to a store", "to store")))


# ── Single-product price change ──────────────────────────────────────────────
# "change the price of water to 20 euros", "set cola's price to 3.50",
# "make the latte cost 4", "update the burger price to 12". This is UNAMBIGUOUS
# (one product), so it routes straight to the list-view price edit (Q2) instead of
# the 3-way clarify. The product name and new amount are EXTRACTED (never hardcoded).
_VERB = r"(?:change|set|update|adjust|edit|modify|put|correct|lower|raise|increase|decrease|reduce)"
_AMT = r"[€$£]?\s*(\d+(?:[.,]\d{1,2})?)"
_PRICE_EDIT_AMT = [
    re.compile(r"price\s+(?:of|for)\s+(?:the\s+|a\s+|an\s+|my\s+)?([a-z0-9][a-z0-9'\- ]*?)\s+(?:to|at|=|->|costs?|should\s+be)\s*" + _AMT, re.I),
    re.compile(r"([a-z0-9][a-z0-9'\- ]*?)(?:'s|s')\s+price\s+(?:to|at|=|should\s+be)\s*" + _AMT, re.I),
    re.compile(r"(?:make|let)\s+(?:the\s+|a\s+|an\s+|my\s+)?([a-z0-9][a-z0-9'\- ]*?)\s+cost\s+" + _AMT, re.I),
    re.compile(_VERB + r"\s+(?:the\s+)?([a-z0-9][a-z0-9'\- ]*?)\s+price\s+(?:to|at|=)\s*" + _AMT, re.I),
    # "set Baileys to 6.50" / "change Bombay Gin to 8.50 euros" - NO word "price", so the
    # amount must clearly be money: a decimal, a currency symbol, or a currency word.
    re.compile(_VERB + r"\s+(?:the\s+)?([a-z0-9][a-z0-9'\- ]*?)\s+(?:to|=)\s+[€$£]\s*(\d+(?:[.,]\d{1,2})?)", re.I),
    re.compile(_VERB + r"\s+(?:the\s+)?([a-z0-9][a-z0-9'\- ]*?)\s+(?:to|=)\s+(\d+[.,]\d{1,2})\b(?!\s*(?:%|am|pm))", re.I),
    re.compile(_VERB + r"\s+(?:the\s+)?([a-z0-9][a-z0-9'\- ]*?)\s+(?:to|=)\s+(\d+)\s*(?:euros?|eur|dollars?|pounds?|cents?|bucks?)\b", re.I),
    # bare integer ("change Bombay Gin to 8") - only when it ENDS the request, so units
    # like "set timer to 5 minutes" or "table to 4 people" are not mistaken for a price.
    re.compile(_VERB + r"\s+(?:the\s+)?([a-z0-9][a-z0-9'\- ]*?)\s+(?:to|=)\s+(\d{1,3})\s*(?:euros?|eur|€)?\s*$", re.I),
]
_PRICE_EDIT_NAME = re.compile(
    r"price\s+(?:of|for)\s+(?:the\s+|a\s+|an\s+|my\s+)?([a-z0-9][a-z0-9'\- ]*?)"
    r"(?=\s+(?:to|at|in|on|please|now)\b|[.,;]|$)", re.I)


_LEADING_DROP = {"change", "set", "update", "adjust", "edit", "modify", "put", "correct",
                 "lower", "raise", "increase", "decrease", "reduce", "make", "let",
                 "the", "a", "an", "my", "new", "please", "want", "wanna", "to", "i"}


def _strip_leading(name):
    """Drop leading verb/filler words a pattern may have swept into the product name
    (e.g. "change water" -> "water")."""
    toks = name.split()
    while toks and toks[0].lower() in _LEADING_DROP:
        toks.pop(0)
    return " ".join(toks)


def _valid_product_name(name):
    if not name or len(name) < 2:
        return False
    return not (set(_norm(name).split()) & NON_PRODUCT_OBJECTS)


def _price_edit(query):
    """Return (product_name|None, amount|None) when the query is a single-product
    price change, else (None, None)."""
    q = query or ""
    for pat in _PRICE_EDIT_AMT:
        m = pat.search(q)
        if m:
            name = _strip_leading(_clean_name(m.group(1)))
            if _valid_product_name(name):
                return name, ("%.2f" % float(m.group(2).replace(",", ".")))
    m = _PRICE_EDIT_NAME.search(q)
    if m:
        name = _strip_leading(_clean_name(m.group(1)))
        if _valid_product_name(name):
            return name, None
    return None, None


def _is_price_change_intent(nlq):
    """Wants to change a PRICE (any verb), but NOT a price set/level/store and NOT
    adding a brand-new product."""
    if "fixed price" in nlq or "fixed-price" in nlq or "price menu" in nlq:
        return False
    if not ("price" in nlq or "cost" in nlq or "costs" in nlq):
        return False
    if not re.search(r"\b(change|set|update|adjust|edit|modify|put|correct|lower|"
                     r"raise|increase|decrease|reduce|make|let)\b", nlq):
        return False
    if any(k in nlq for k in ("price level", "price set", "price levels", "price sets",
                              "to a store", "to store", "pricing rule")):
        return False
    if re.search(r"\b(add|create)\b", nlq) and "price of" not in nlq:
        return False
    return True


# ──────────────────────────────────────────────────────────────────────────────
#  SECTION AWARENESS - a random question is answered WITHIN one section only
#  (Products / Self-service / Payment). The three sections never intersect.
# ──────────────────────────────────────────────────────────────────────────────
SECTION_RANGES = [("Products", 1, 25), ("Self-service", 26, 38), ("Payment", 39, 44)]


def section_of(qid):
    """Map a guide id to its section name. Returns None for unknown ids."""
    try:
        qid = int(qid)
    except (TypeError, ValueError):
        return None
    for name, lo, hi in SECTION_RANGES:
        if lo <= qid <= hi:
            return name
    return None


# Light section-level keyword hints. They only nudge classification / break ties;
# the per-guide PROFILES above still do the heavy lifting. Kept deliberately
# distinctive so the three sections do not overlap.
SECTION_HINTS = {
    "Self-service": [
        ("self-service", 4), ("self service", 4), ("kiosk", 4), ("qr shop", 4),
        ("qr code", 3), ("qr codes", 4), ("webshop", 4), ("web shop", 4),
        ("web-shop", 4), ("imprint", 4), ("cross-selling", 3), ("cross selling", 3),
        ("buzzer", 4), ("pager", 4), ("pay on pick", 4), ("grab and go", 4),
        ("scan and order", 3), ("order portal", 3), ("pick up their order", 3),
        ("pickup", 2), ("pick up", 2),
    ],
    "Payment": [
        ("payment method", 4), ("payment methods", 4), ("payment menu", 3),
        ("eft", 4), ("eft device", 4), ("payment terminal", 3), ("card reader", 3),
        ("pin terminal", 3), ("smart voucher", 4), ("voucher", 2), ("on account", 4),
        ("pagamento", 4), ("riscosso", 4),
    ],
    "Products": [
        ("product", 2), ("article", 2), ("allergen", 3), ("plu", 3), ("vat", 3),
        ("composite", 3), ("product group", 3), ("price level", 2), ("price set", 2),
        ("promotion", 2), ("packaging", 3),
    ],
}


def dominant_section(query, scores=None, params=None):
    """Decide which ONE section a free-form question belongs to.
    Ranks sections by their strongest single in-section guide score, with light
    section keyword hints and an add-a-product nudge toward Products as
    tie-breakers. Returns the section name, or None when nothing matches."""
    nlq = _norm(query)
    if scores is None:
        scores = _score_guides(nlq)
    if params is None:
        params = extract_params(query)
    best = {name: 0.0 for name, _, _ in SECTION_RANGES}
    agg = {name: 0.0 for name, _, _ in SECTION_RANGES}
    for qid, s in scores.items():
        sec = section_of(qid)
        if sec:
            best[sec] = max(best[sec], s)
            agg[sec] += s
    for sec, hints in SECTION_HINTS.items():
        for ph, w in hints:
            if ph in nlq:
                best[sec] = max(best[sec], float(w))
                agg[sec] += w
    if params.get("is_add"):
        best["Products"] = max(best["Products"], 5.0)
        agg["Products"] += 5
    ranked = sorted(best.keys(), key=lambda s: (best[s], agg[s]), reverse=True)
    top = ranked[0]
    return top if best[top] > 0 else None


def route(query, section=None):
    """Return ranked [(qid, score)] for the primary intent. When `section` is
    given, only guides in that section are considered, so a question can never
    route across sections."""
    nlq = _norm(query)
    scores = _score_guides(nlq)
    params = extract_params(query)
    # If it's clearly an add-a-product request, boost Q1 so generic "add X" lands
    # on the create-product guide.
    if params["is_add"]:
        scores[1] = scores.get(1, 0) + 5
    # "product group(s)" is its own guide (Q12). Don't let "create a product group" be read
    # as "create a product" (Q1) just because that phrase is a substring.
    if "product group" in nlq or "product groups" in nlq:
        scores[12] = scores.get(12, 0) + 6
        if not params["is_add"]:
            scores[1] = 0
    # Combo: "price level(s)" + "store" is specifically Q20, not Q14. Move the
    # price-level weight onto Q20 so it clearly beats the generic price-level guide.
    if ("price level" in nlq or "price levels" in nlq) and "store" in nlq:
        scores[20] = scores.get(20, 0) + scores.get(14, 0) + 10
        scores[14] = 0
    if section:
        scores = {q: s for q, s in scores.items() if section_of(q) == section}
    return sorted(scores.items(), key=lambda kv: -kv[1])


def plan(query):
    """Decide what to do. Returns a dict describing the action.
    Routing is SECTION-SCOPED: the query is first classified into ONE section
    (Products / Self-service / Payment) and every routed or merged guide must
    belong to that section, so sections never intersect."""
    nlq = _norm(query)
    params = extract_params(query)

    # 0) SINGLE-PRODUCT price change ("change the price of water to 20 euros") ->
    # list-view price edit (Q2). Unambiguous, so skip the 3-way clarify. Product +
    # amount are extracted so the answer/build use the user's values (no hardcoding).
    pe_name, pe_amt = _price_edit(query)
    pe_intent = _is_price_change_intent(nlq) and (
        pe_name or re.search(r"\bprice\s+of\b", nlq)
        or (params.get("price") and not params.get("price_auto")))
    # "set Baileys to 6.50" has no word "price", but a clear product + money amount IS a
    # price change, so route it too (otherwise the build falls back to the sample product).
    if pe_intent or (pe_name and pe_amt):
        params["price_edit"] = True
        if pe_name:
            params["product_name"] = pe_name
            params["is_add"] = False
        if pe_amt:
            params["price"] = pe_amt
            params["price_auto"] = False
        return {"action": "single", "params": params, "guides": [2],
                "primary": 2, "score": 9, "section": "Products"}

    # 1) vague price-change ambiguity -> clarify (a Products-only feature)
    if _is_price_change(nlq):
        return {"action": "clarify", "params": params, "section": "Products",
                "question": "Which kind of price change do you mean?",
                "options": PRICE_AMBIGUOUS_OPTIONS}

    # 2) classify the section, then route ONLY within it
    sec = dominant_section(query, params=params)
    ranked = route(query, section=sec)
    if not ranked or ranked[0][1] < 3:
        return {"action": "none", "params": params, "section": sec,
                "message": "I don't have a guide that covers that yet."}

    # Outside Products there is no product creation, so drop any add-a-product
    # signal a phrase like "add a payment method" may have falsely triggered
    # (otherwise it would prepend a bogus "Here's how to do this for ..." header).
    if sec != "Products":
        params["is_add"] = False
        params["product_name"] = None

    primary = ranked[0][0]
    primary_score = ranked[0][1]

    # When the user is genuinely creating a product, the create-product guide (Q1)
    # is the PRIMARY act; a time/allergen guide that happens to score higher is a
    # secondary feature, not the main intent.
    if params["is_add"] and primary in SECONDARY_ONLY:
        primary = 1
        primary_score = max(primary_score, dict(ranked).get(1, 0))

    # 3) MERGE - clause by clause, but every merged guide stays inside `sec`.
    # Split the request into clauses on natural conjunctions and route EACH clause
    # through the same (section-scoped) scorer. Cross-section clauses are dropped.
    merge = []
    for clause in _clauses(query):
        rc = route(clause, section=sec)
        if not rc or rc[0][1] < 4:           # the clause must clearly name a task
            continue
        g = rc[0][0]
        cp = extract_params(clause)
        if cp["is_add"] and g in SECONDARY_ONLY and sec == "Products":
            g = 1
        if section_of(g) != sec:             # never cross the section boundary
            continue
        if g not in merge:
            merge.append(g)
    if primary not in merge:                 # make sure the strongest overall intent is in
        merge.insert(0, primary)
    # also keep the curated short add-on triggers (e.g. "only during", "% off") that may
    # not be full profile phrases, so time/allergen/discount still merge - but ONLY when
    # the question itself is in that add-on's section (all SECONDARY entries are Products).
    for qid, phrases in SECONDARY.items():
        if section_of(qid) != sec:
            continue
        if qid in merge or qid in MENU_IS_BUILTIN:
            continue
        if qid == 17 and 22 in merge:        # Q22 ("areas AND times") already covers the time part
            continue
        matched = [ph for ph, _ in phrases if _phrase_in(ph, nlq)]
        if qid == 17 and merge and merge[0] in MENU_BUILD_GUIDES:
            matched = [ph for ph in matched if ph not in WEAK_17]
        if matched:
            merge.append(qid)
    if not merge:
        merge = [primary]
    primary = merge[0]                       # the guide the answer/build leads with

    if len(merge) > 1:
        return {"action": "merge", "params": params, "guides": merge,
                "primary": primary, "score": primary_score, "section": sec}
    return {"action": "single", "params": params, "guides": [primary],
            "primary": primary, "score": primary_score, "section": sec}


# ──────────────────────────────────────────────────────────────────────────────
#  ANSWER ASSEMBLY  (grounded in the real steps, with the user's params woven in)
# ──────────────────────────────────────────────────────────────────────────────
def _tailor_caption(cap, params):
    """Weave the user's concrete product details into a generic step caption."""
    c = cap
    name = params.get("product_name")
    low = cap.lower()
    if name and ("name of the product" in low or "fill in the name" in low
                 or "give the product a name" in low or "enter a name" in low):
        c = c.rstrip(".") + ' — here, enter "%s".' % name
    elif ("product group" in low or ("drop-down" in low and "group" in low)) \
            and params.get("category_pref"):
        c = c.rstrip(".") + ' — for a %s, pick "%s".' % (
            params.get("type", "product"), params["category_pref"][0])
    elif "price" in low and ("enter" in low or "fill" in low or "set up" in low):
        tag = " (auto-set; change if you like)" if params.get("price_auto") else ""
        c = c.rstrip(".") + ' — e.g. %s%s.' % (params.get("price", ""), tag)
    elif "allergen" in low and params.get("allergens"):
        c = c.rstrip(".") + " — here, tick: %s." % _join_and(params["allergens"])
    return c


def recipe_vars(qid, params):
    """Variables to inject into recipes/Q{qid}_capture.json so the live demo
    builds the USER's product instead of the hard-coded sample. Everything here is
    DERIVED from the current question (no product is ever hard-coded in a recipe)."""
    v = {}
    if params.get("product_name"):
        v["NAME"] = params["product_name"]
    if params.get("price"):
        v["PRICE"] = params["price"]
    # MENUGROUP: which menu column group a product belongs under, derived from its
    # detected type (drink -> "Drinks", food -> "Food"). This replaces the previously
    # hard-coded "Drinks" drop target so the drag generalises to any product.
    t = params.get("type", "other")
    v["MENUGROUP"] = {"drink": "Drinks", "food": "Food"}.get(t, "Other")
    # PRODUCTGROUP: the best product-group to file the new product under in the create
    # form, again derived from the type (drink -> "Soft Drinks", food -> "Food", ...).
    pref = params.get("category_pref") or CATEGORY_PREF.get(t, CATEGORY_PREF["other"])
    v["PRODUCTGROUP"] = pref[0]
    if params.get("allergens"):
        v["ALLERGENS"] = ", ".join(params["allergens"])
    return v


def _guide_block(qid, cat, params, tailor=False, start=1):
    title = cat.get(qid, {}).get("title", "Question %d" % qid)
    steps = cat.get(qid, {}).get("steps", [])
    lines = []
    n = start
    for cap in steps:
        if start > 1 and n == start and cap.lower().startswith("welcome"):
            continue
        text = _tailor_caption(cap, params) if tailor else cap
        lines.append("%d. %s" % (n, text))
        n += 1
    return title, lines, n


def render(qid, query="", polish=False):
    """Full numbered-step answer for a SPECIFIC guide id. Used when the GPT tier did the
    routing - we still render the COMPLETE grounded steps (never a prose summary), so every
    answer has all steps regardless of which tier picked the guide."""
    cat = _catalog()
    params = extract_params(query)
    tailor = bool(params.get("product_name")) or bool(params.get("allergens"))
    title, lines, _ = _guide_block(qid, cat, params, tailor=tailor, start=1)
    header = ""
    if qid == 1 and params.get("product_name"):
        header = ('Here\'s how to do this for "%s" (%s, price %s%s):\n\n'
                  % (params["product_name"], params.get("type", "product"),
                     params.get("price"), " auto-set" if params.get("price_auto") else ""))
    body = "How to %s:\n\n%s" % (title[0].lower() + title[1:], "\n".join(lines))
    ans = header + body
    if polish:
        try:
            from intelligence import llm
            if llm.available():
                want = len(re.findall(r"(?m)^\s*\d+\.", ans))
                refined = llm.ask_text(
                    "Rewrite this step-by-step guide to read smoothly and concisely. Keep "
                    "EVERY numbered step and all values; return the COMPLETE numbered list.\n\n" + ans,
                    system="You are the DISH POS documentation assistant.", max_tokens=3500)
                if refined and len(re.findall(r"(?m)^\s*\d+\.", refined)) >= want:
                    ans = refined.strip()
        except Exception:
            pass
    return {"answer": ans, "qid": qid, "title": title, "action": "single",
            "params": params, "guides": [qid], "section": section_of(qid),
            "sources": [{"workflow": title, "qid": qid}],
            "recipe_vars": recipe_vars(qid, params)}


def answer(query, polish=False):
    """Full deterministic answer. Returns a dict consumable by server.py.
       Shape: {answer, qid, title, guides, params, action, sources, options?, recipe_vars?}
    """
    cat = _catalog()
    pl = plan(query)
    params = pl["params"]

    if pl["action"] == "none":
        return {"answer": pl["message"] + " Try rephrasing, or ask about adding a "
                "product, prices, menus, allergens, promotions, or printing.",
                "qid": None, "title": "", "guides": [], "params": params,
                "action": "none", "section": pl.get("section"), "sources": []}

    if pl["action"] == "clarify":
        opts = "\n".join("  • %s" % o["label"] for o in pl["options"])
        return {"answer": pl["question"] + "\n\n" + opts,
                "qid": None, "title": "", "guides": [], "params": params,
                "action": "clarify", "section": pl.get("section"),
                "options": pl["options"], "sources": []}

    guides = pl["guides"]
    primary = pl["primary"]
    tailor = bool(params.get("product_name")) or bool(params.get("allergens"))

    header = ""
    if params.get("price_edit") and params.get("product_name"):
        amt = params.get("price")
        to = (' to €%s' % amt) if (amt and not params.get("price_auto")) else ""
        header = ('Here\'s how to change the price of "%s"%s:\n\n'
                  % (params["product_name"], to))
    elif params.get("product_name") and 1 in guides:
        header = ('Here\'s how to do this for "%s" (%s, price %s%s):\n\n'
                  % (params["product_name"], params.get("type", "product"),
                     params.get("price"),
                     " auto-set" if params.get("price_auto") else ""))

    body_parts, sources = [], []
    n = 1
    for i, qid in enumerate(guides):
        title, lines, n = _guide_block(qid, cat, params, tailor=tailor, start=n)
        if len(guides) > 1:
            label = ("First — %s" if i == 0 else "Then — %s") % title
            body_parts.append(label + ":\n" + "\n".join(lines))
        else:
            body_parts.append("How to %s:\n\n%s"
                              % (title[0].lower() + title[1:], "\n".join(lines)))
        sources.append({"workflow": title, "qid": qid})

    body = "\n\n".join(body_parts)

    if polish:
        try:
            from intelligence import llm
            if llm.available():
                want = len(re.findall(r"(?m)^\s*\d+\.", body))   # how many numbered steps
                refined = llm.ask_text(
                    "Rewrite this step-by-step guide to read smoothly and concisely. "
                    "Keep EVERY numbered step - do not drop, merge, or stop early - and keep "
                    "all concrete values. Return the COMPLETE numbered list.\n\n" + body,
                    system="You are the DISH POS documentation assistant.",
                    max_tokens=3500)
                got = len(re.findall(r"(?m)^\s*\d+\.", refined or ""))
                # Only accept the polished text if it kept ALL the steps. If the model
                # truncated (fewer steps), keep the complete deterministic body so the
                # user never gets a half-finished guide. The personalised header is kept
                # OUTSIDE the polish so it is never rewritten away.
                if refined and len(refined) > 40 and got >= want:
                    body = refined.strip()
        except Exception:
            pass

    ans = header + body

    return {"answer": ans, "qid": primary,
            "title": cat.get(primary, {}).get("title", ""),
            "guides": guides, "params": params, "action": pl["action"],
            "section": pl.get("section"),
            "sources": sources, "recipe_vars": recipe_vars(primary, params)}


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or \
        "I want to add apple juice cocktail as a drink and bring it to the menu"
    res = answer(q)
    print("Q:", q)
    print("action:", res["action"], "| guides:", res["guides"],
          "| params:", {k: res["params"][k] for k in
                        ("product_name", "type", "price", "price_auto")})
    print("-" * 70)
    print(res["answer"])
