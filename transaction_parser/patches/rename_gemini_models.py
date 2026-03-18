import frappe

RENAME_MAP = {
    "Google Gemini Pro": "Google Gemini Pro-2.5",
    "Google Gemini Flash": "Google Gemini Flash-2.5",
}

DOCTYPE = "Transaction Parser Settings"
FIELD = "default_ai_model"


def execute():
    current = frappe.db.get_single_value(DOCTYPE, FIELD)

    if current in RENAME_MAP:
        frappe.db.set_single_value(DOCTYPE, FIELD, RENAME_MAP[current])
