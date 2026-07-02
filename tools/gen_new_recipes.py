# Generates step-recipes (Q{NN}_script.json) for the new Self-Service + Payment questions
# and registers them in questions.json. Steps are taken from the official DISH support
# articles. Capture (PDF/video) recipes are built per-flow separately.
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
REC = ROOT / "recipes"

NEW = [
 # ---------------- Self-service (26-38) ----------------
 {"qid":26,"title":"Time Schedules - Activating the Pay on pick up functionality",
  "wf":"Activating the Pay on pick up functionality","country":"FR",
  "steps":[
    "Welcome. This guide shows how to activate the Pay on pick up functionality for self-service.",
    "Go to Self-service, then Sales channels.",
    "Edit the sales channel for the Webshop (Order2POS).",
    "Tick the \"Payment on pickup\" option.",
    "Go to General, then General, and click Send to transmit the changes."]},
 {"qid":27,"title":"Time Schedules - Adding and managing time schedules for self-service",
  "wf":"Adding and managing time schedules for self-service","country":"",
  "steps":[
    "Welcome. This guide shows how to add and manage time schedules for self-service.",
    "In the Backoffice, go to Self-service.",
    "Click on Time schedules.",
    "Click + Add time schedule.",
    "Enter a name for your time schedule.",
    "Specify the open/close times for each day; use + to add slots and the bin icon to remove them.",
    "Use + Add exception to set alternative or closed times for specific dates or periods.",
    "Click Save.",
    "Go to Sales channels and edit the sales channel of your choice.",
    "Open the Opening hours tab and select your time schedule from the dropdown, then Save.",
    "Go to General, then General, and click Send to transmit the changes."]},
 {"qid":28,"title":"Sales Channels - Adjusting the appearance of the self-service QR shop",
  "wf":"Adjusting the appearance of the self-service QR shop","country":"",
  "steps":[
    "Welcome. This guide shows how to adjust the appearance of the self-service QR shop.",
    "In the Backoffice, under Self-service, click Sales channels.",
    "Click the pencil icon next to the store and open the Appearance tab.",
    "Under Colors, set a primary and secondary colour via Hex code or the colour picker.",
    "Under Standard product overview, choose grid view or list view as the default.",
    "Under Logo, add your logo by dragging it in or browsing.",
    "Under Images, customise the welcome, success, and error images.",
    "Go to General, then General, and click Send to transmit the changes."]},
 {"qid":29,"title":"Sales Channels - Adding cross-selling products at checkout",
  "wf":"Adding cross-selling products at checkout","country":"",
  "steps":[
    "Welcome. This guide shows how to add cross-selling products at checkout.",
    "In the Backoffice, open Self-service and click Sales channels.",
    "Click the pencil in front of the kiosk sales channel you want to change.",
    "Open the Cross-selling option.",
    "Click the toggle next to \"Enable cross-selling\" to activate it.",
    "Enter the title that shows on the kiosk.",
    "Next to Product, choose the product to cross-sell, then Save.",
    "Optionally add translations via General, then Translations, then Kiosk Cross-selling Text.",
    "Go to General, then General, and click Send to transmit the changes."]},
 {"qid":30,"title":"Sales Channels - Setting up the imprint for web shops and QR sales channels",
  "wf":"Setting up the imprint for web shops and QR sales channels","country":"",
  "steps":[
    "Welcome. This guide shows how to set up the imprint for web shops and QR sales channels.",
    "In the Backoffice, go to Self-service and click Sales channels.",
    "Click the pencil icon of your desired QR sales channel.",
    "Open the Legal notice tab.",
    "Scroll to the Imprint field and insert your imprint text.",
    "Click Save.",
    "Go to General, then General, and click Send to transmit the changes."]},
 {"qid":31,"title":"Sales Channels - Adjusting the appearance of the kiosk",
  "wf":"Adjusting the appearance of the kiosk","country":"",
  "steps":[
    "Welcome. This guide shows how to adjust the appearance of the kiosk.",
    "In the Backoffice, go to Self-service and click Sales channels.",
    "Click the edit icon of your kiosk.",
    "Adjust the general settings: fulfilment options, languages, welcome/content text, and appearance.",
    "Set the opening hours if needed.",
    "Click Save.",
    "Go to General, then General, and click Send to transmit the changes."]},
 {"qid":32,"title":"Sales Channels - Changing settings for DISH Payment",
  "wf":"Changing settings for DISH Payment","country":"",
  "steps":[
    "Welcome. This guide shows how to change the settings for DISH Payment.",
    "In the Backoffice, go to Self-service and click Sales channels.",
    "Click the edit icon of your Payment site.",
    "Adjust the general settings: order comments, languages, content, appearance, and tipping.",
    "Set the legal information and opening hours if needed.",
    "Click Save.",
    "Go to General, then General, and click Send to transmit the changes."]},
 {"qid":33,"title":"Sales Channels - Configuring random spot checks on self-service POS/Grab and Go POS",
  "wf":"Configuring random spot checks on self-service POS/Grab and Go POS","country":"",
  "steps":[
    "Welcome. This guide shows how to configure random spot checks on self-service POS/Grab and Go POS.",
    "In the Backoffice, go to Self-service and click Sales channels.",
    "Edit a Self-scan or Self-service checkout by clicking the pencil icon.",
    "Switch on the Enable checks toggle.",
    "Configure the settings: Frequency, Expiration, an 8-digit Pin code, and an explanatory note.",
    "Click Save.",
    "Go to General, then General, and click Send to transmit the changes."]},
 {"qid":34,"title":"Webshop - Adjusting and personalising the webshop",
  "wf":"Adjusting and personalising the webshop","country":"",
  "steps":[
    "Welcome. This guide shows how to adjust and personalise the webshop.",
    "In the Backoffice, click Sales channels under Self-service.",
    "Click the edit button next to your webshop's name.",
    "In General, set the name, facility, default language, and order comments.",
    "In Content, edit the welcome text and general information.",
    "In Appearance, choose colours, product layout, logo, and images.",
    "In Legal information, add terms and conditions and a privacy statement.",
    "In Company information, edit company name, address, and contact info.",
    "In Pick-up time slots, set the available days and hours, then Save.",
    "Go to General, then General, and click Send to transmit the changes."]},
 {"qid":35,"title":"Menus - Linking two different menus in the kiosk (Eat-in or Takeaway)",
  "wf":"Linking two different menus in the kiosk (Eat-in or Takeaway)","country":"",
  "steps":[
    "Welcome. This guide shows how to link two different menus in the kiosk for Eat-in or Takeaway.",
    "In the Backoffice, click Products, then Menus.",
    "Click + Add menu, enter a name, and tick the Derived menu checkbox.",
    "Select the Menu and Store to derive from (e.g. Kiosk), then Save.",
    "Repeat to create the second menu (e.g. Takeaway).",
    "Click General, then Facilities, and expand the desired facility and E-Commerce.",
    "Click the pencil next to a facility, open the Menu setting, and select the created menu as the POS menu, then Save.",
    "Repeat for the second facility (Eat-in).",
    "Click Self-service, then Sales channels, edit the ordering kiosk, and set the fulfilment options to the desired facilities.",
    "Go to General, then General, and click Send to transmit the changes."]},
 {"qid":36,"title":"QR Codes - Reordering via QR code on the table (customer perspective)",
  "wf":"Reordering via QR code on the table (customer perspective)","country":"",
  "steps":[
    "Welcome. This guide shows reordering via a QR code on the table from the customer perspective.",
    "In the Backoffice, go to Self-service and click QR codes.",
    "Click the link of a QR code to open the order portal.",
    "Click Place order and choose a few items.",
    "Click View order.",
    "Select the \"Pay later\" option (when reorder via QR on the table is enabled).",
    "Choose Complete order.",
    "Open the same QR link again and use \"Order more\" or \"Pay order\" to add to or settle the table."]},
 {"qid":37,"title":"Product - QR Code - Creating QR codes for self-service",
  "wf":"Creating QR codes for self-service","country":"",
  "steps":[
    "Welcome. This guide shows how to create QR codes for self-service.",
    "In the Backoffice, under Self-service, click QR codes.",
    "Click Add QR codes in the top right corner.",
    "Select the correct sales channel and an entire area or specific sales points.",
    "Click the Add QR code button.",
    "Tick the box in front of the sales points to select them.",
    "Click the download button and choose CSV (for QR printing) or PDF (ready-to-print).",
    "Go to General, then General, and click Send to transmit the changes."]},
 {"qid":38,"title":"Sales Channels - Configuring Buzzer/Pager support for your kiosk",
  "wf":"Configuring Buzzer/Pager support for your kiosk","country":"NL-BE",
  "steps":[
    "Welcome. This guide shows how to configure Buzzer/Pager support for your kiosk.",
    "In the Backoffice, go to Self-service and click Sales channels.",
    "Click the edit icon next to your kiosk.",
    "Open the buzzer configuration tab.",
    "Select the buzzer mode: No Buzzers, Optional, or Mandatory.",
    "Enter the instruction texts (when entering the buzzer number, and after payment).",
    "Add an image of your buzzer, stand, or number holder.",
    "Optionally translate via the Translation link and the order indicator instructions.",
    "Go to General, then General, and click Send to transmit the changes."]},
 # ---------------- Payment (39-44) ----------------
 {"qid":39,"title":"Payment Methods - Adding a Pagamento non riscosso",
  "wf":"Adding a Pagamento non riscosso","country":"IT",
  "steps":[
    "Welcome. This guide shows how to add a Pagamento non riscosso payment method.",
    "In the Dashboard, select Payment from the left menu.",
    "Select Payment methods.",
    "Click + Add payment method in the top right corner.",
    "Set the Name to \"Pagamento non riscosso\".",
    "Set the Payment method type to Cash and the Currency to Euro.",
    "Set the Fiscal reference to No payment.",
    "Click Save."]},
 {"qid":40,"title":"Payment Methods - Adding and managing payment methods (incl. payment menus)",
  "wf":"Adding and managing payment methods (incl. payment menus)","country":"",
  "steps":[
    "Welcome. This guide shows how to add and manage payment methods, including payment menus.",
    "Go to Payment, then Payment method, and click + Add payment method in the top right corner.",
    "Fill in the name of the payment method.",
    "Choose the type.",
    "Choose the currency (default Euro).",
    "Add the store configuration and choose whether to open a cash drawer.",
    "Choose whether to show the amount dialogue, then click Save and Save again.",
    "To add it to the cashier screen, go to Payment, then Payment menus, click Payment methods, and drag the new method in.",
    "To adjust a method, click the pencil icon, make changes, and Save; to delete, click the trash icon and confirm.",
    "Go to General, then General, and click Send to transmit the changes."]},
 {"qid":41,"title":"EFT Devices - Managing EFT devices",
  "wf":"Managing EFT devices","country":"",
  "steps":[
    "Welcome. This guide shows how to manage EFT devices.",
    "In the Backoffice, go to Payment and open EFT devices to view all configured payment terminals.",
    "Review the listed EFT devices.",
    "To make changes to EFT devices, contact the DISH POS service desk for advice on the impact.",
    "Go to General, then General, and click Send to transmit the changes."]},
 {"qid":42,"title":"EFT Devices - Setting up a stand-alone EFT terminal",
  "wf":"Setting up a stand-alone EFT terminal","country":"DE",
  "steps":[
    "Welcome. This guide shows how to set up a stand-alone EFT terminal.",
    "In the Backoffice, go to Payment, then EFT devices, to check compatibility (no EFT devices should be listed).",
    "Go to Payment methods and click + Add payment method.",
    "Enter a Name and set the Method type to Payment terminal.",
    "Set the Currency to EUR and click + Add store configuration.",
    "Click Save, then Save again.",
    "Open the Payment methods menu, remove the old EFT type, and add the new EFT payment method.",
    "Go to General, then General, and transmit the changes; then verify it appears in the POS app.",
    "Create a support ticket to enable the reopen function for stand-alone terminals."]},
 {"qid":43,"title":"Payment Methods - Adding a payment method: On account",
  "wf":"Adding a payment method: On account","country":"DE",
  "steps":[
    "Welcome. This guide shows how to add the On account payment method.",
    "In the Backoffice, open the Payment section in the left navigation bar.",
    "Go to Payment methods to see all existing methods.",
    "Click + Add payment method.",
    "Enter a name (for example, \"On account\").",
    "Set the Payment method type to Non-integrated payment terminal.",
    "Select the appropriate currency.",
    "Set the Fiscal reference to Other transfer, then click Save.",
    "Add it to the cashier screen via Payment, then Payment menus, by dragging the new method in."]},
 {"qid":44,"title":"Payment Methods - Configuring the Smart Voucher",
  "wf":"Configuring the Smart Voucher","country":"",
  "steps":[
    "Welcome. This guide shows how to configure the Smart Voucher payment method.",
    "Go to Payment, then Payment method.",
    "Click + Add payment method.",
    "Select Smart voucher as the Payment method type.",
    "Name the voucher.",
    "Add the maximum value to the voucher.",
    "If you need to invoice the vouchers, select by User or a pre-selected customer.",
    "Click Save."]},
]

def mk_script(q):
    steps = []
    n = len(q["steps"])
    for i, cap in enumerate(q["steps"]):
        action = "info" if (i == 0 or i == n - 1) else "click"
        steps.append({"step": i + 1, "action": action, "caption": cap, "highlight": ""})
    return {"id": q["qid"], "title": q["title"], "workflow_title": q["wf"],
            "backoffice": "old", "country": q.get("country", ""), "steps": steps}

written = 0
for q in NEW:
    p = REC / ("Q%02d_script.json" % q["qid"])
    p.write_text(json.dumps(mk_script(q), indent=2, ensure_ascii=False), encoding="utf-8")
    written += 1

# register in questions.json
qf = ROOT / "questions.json"
data = json.loads(qf.read_text(encoding="utf-8"))
existing = {x["id"] for x in data["questions"]}
added = 0
for q in NEW:
    if q["qid"] not in existing:
        data["questions"].append({"id": q["qid"], "title": q["title"], "status": "ready",
                                  "recipe": "recipes/Q%02d_script.json" % q["qid"], "pdf": "", "video": ""})
        added += 1
data["questions"].sort(key=lambda x: x["id"])
qf.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print("scripts written:", written, "| questions added:", added, "| total questions:", len(data["questions"]))
