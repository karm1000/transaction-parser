import frappe


def execute():
    frappe.db.set_single_value(
        "Transaction Parser Settings", "process_one_document_per_communication", 1
    )
