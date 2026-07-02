# Q1 Recipe — Adding a product and assigning it to a menu

**Source of truth:** `booqsoftware-dish.bo.cm.front-end` (Angular). Selectors are taken
from component templates, so they're stable across UI text/locale changes.

> ⚠️ Why the previous run failed: the old `manifest.json` ended at "FORM CLOSED
> UNEXPECTEDLY" / "ERROR state". The old script used a drag-and-drop "Turnover →
> Menukaart/Drinks" flow that no longer matches this UI. In the current front-end,
> menu assignment happens inside the product form via a dialog. This recipe reflects
> the real, current flow.

## Field model (`product-detail.component.html`)
| Field            | formControlName     | data-testid                        |
|------------------|---------------------|------------------------------------|
| Name             | `name`              | `input-name`                       |
| Short name       | `shortName`         | `input-short-name`                 |
| VAT rate         | `basePriceVatRate`  | `dropdown-vat-rate`                |
| Price            | `basePriceAmount`   | `input-price`                      |
| Open price       | `openPrice`         | `switch-open-price`               |
| Product category | `productCategory`   | `dropdown-product-category`       |
| Course           | `course`            | `dropdown-course`                 |
| Recycling deposit| `recyclingDeposit`  | `dropdown-recycling-deposit`      |
| Menu assignment  | `menus`             | section `app-product-detail-menus` |

## Menu assignment (`product-detail-menus.component.html`)
- Add button: `data-testid="product-add-menu-assignment-button"` → opens menu dialog.
- Existing assignments render in `dish-assignment-list` (`assignment-list-menu`).

## Step sequence (screenshot after each)
1. Login at `/cm/login` (email + password + submit) — *login selectors confirmed at runtime*
2. Accept cookie banner if present (CM repo has none → likely absent on sandbox)
3. Open `/cm/products`
4. Open create form via `/cm/products/(aside_content:createproduct)`
5. Fill `input-name`
6. Pick VAT in `dropdown-vat-rate`
7. Fill `input-price`
8. Pick category in `dropdown-product-category`
9. Click `product-add-menu-assignment-button`, pick menu in dialog, confirm
10. Save (page Save button)
11. Confirm product appears in list

_Implemented in `capture/playwright_agent.py`._
