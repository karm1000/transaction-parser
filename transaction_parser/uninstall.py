import frappe

FIELDS_TO_DELETE = {
    "Transaction Parser Settings": ["in_auto_create_supplier"],
    "Sales Order": ["is_created_by_transaction_parser"],
    "Purchase Invoice": ["is_created_by_transaction_parser"],
}


def before_uninstall():
    for doctype, fieldnames in FIELDS_TO_DELETE.items():
        frappe.db.delete(
            "Custom Field", {"dt": doctype, "fieldname": ("in", fieldnames)}
        )
        frappe.clear_cache(doctype=doctype)
