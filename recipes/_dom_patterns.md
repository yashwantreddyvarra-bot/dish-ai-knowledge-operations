# DISH POS Back-office — verified DOM patterns (memory)

This file is the project's **memory of how to drive the DISH POS back-office**, learned from
live DOM dumps and verified runs. It is **product-agnostic**: the product always comes from
the current question via the `{NAME}` / `{PRICE}` / `{MENUGROUP}` / `{PRODUCTGROUP}`
placeholders — no product is ever hard-coded into a recipe. Reuse these selectors when
building or fixing any of the 25 question recipes.

## Left sidebar (navigation)
Sidebar items are `<app-nav-link>` components with a stable `l10n` key — NOT `<button>` or
`<a>`, so target by the component + key:

- Products (section + sub-item): `app-nav-link[l10n="LAYOUT.LEFT_MENU.PRODUCTS"]`
- Menus: `app-nav-link[l10n="LAYOUT.LEFT_MENU.MENUS"]`
- Other items follow the same pattern: `LAYOUT.LEFT_MENU.PRODUCT_GROUPS`, `...PRICE_LEVELS`,
  `...PROMOTIONS`, `...PERIODS`, `...FACILITIES`, etc.
- The parent section header and its first sub-item can share a label (e.g. two "Products");
  the `l10n` attribute resolves to the clickable sub-item, avoiding the parent/child mix-up.

## Create-product form
Stable `formcontrolname` hooks:
- Name: `input[formcontrolname="name"]`
- Product group (tree input): `app-productgroup-tree-input[formcontrolname="productGroup"]`
  → pick the group from `{PRODUCTGROUP}` (drink→"Soft Drinks", food→"Food", …)
- Turnover group: `app-turnover-tree-input[formcontrolname="turnoverGroup"]`
- Price: `app-price-input[formcontrolname="price"] input`
- VAT: `p-select[formcontrolname="vatId"]`
- Save: `button:has-text("Save"):not(:has-text("add new"))`

## Menus screen (three columns)
- Left "Menus" list: `app-menu-tree`, rows toggle via `.p-tree-node-toggle-button`.
- Middle "Menukaart" contents (DROP target): `app-menu-item-tree`, group rows are
  `.p-tree-node` (e.g. Food / Drinks / Other / Popular Items), drop zones are
  `.p-tree-node-droppoint`. Target the right group with `{MENUGROUP}`:
  `app-menu-item-tree .p-tree-node:has-text("{MENUGROUP}")`.
- Right "Products" column (DRAG source): `app-product-tree`. Products are HTML5-native
  **`draggable="true"`** rows with class `.draggable-row` — this app is **not** Angular CDK.
  Source: `app-product-tree .draggable-row:has-text("{NAME}")`.

## Drag-and-drop
Because rows are native `draggable="true"` (not CDK), use Playwright's `locator.drag_to()`
(it dispatches real `dragstart`/`dragover`/`drop`). A plain mouse down/move/up does NOT fire
HTML5 DnD. The engine tries `drag_to` first, then falls back to a stepped mouse drag.
Verified: `app-product-tree .draggable-row:has-text("{NAME}") -> app-menu-item-tree .p-tree-node:has-text("{MENUGROUP}")`.

## Highlight boxes
The orange highlight box comes from the matched element's bounding box at capture time. If a
selector matches the wrong element, the box is wrong — prefer the specific hooks above. When a
selector can't be found, the engine falls back to a vision model pick (with a self-check).
