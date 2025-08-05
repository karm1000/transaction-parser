import frappe
from frappe.custom.doctype.custom_field.custom_field import (
    create_custom_fields,
)

CUSTOM_FIELDS = {
    "Sales Order": [
        {
            "fieldname": "is_created_by_transaction_parser",
            "fieldtype": "Check",
            "label": "Is Created By Transaction Parser",
            "read_only": 1,
            "insert_after": "is_internal_customer",
        }
    ],
    "Communication": [
        {
            "fieldname": "is_processed_by_transaction_parser",
            "fieldtype": "Check",
            "label": "Is Processed By Transaction Parser",
            "read_only": 1,
            "insert_after": "seen",
        }
    ],
}

INDIA_SPECIFIC_CUSTOM_FIELDS = {
    "Transaction Parser Settings": [
        {
            "fieldname": "in_auto_create_supplier",
            "fieldtype": "Check",
            "label": "Auto Create Supplier",
            "insert_after": "invoice_lookback_count",
            "description": "Automatically create a supplier based on GSTIN from the invoice",
        }
    ]
}


def after_install():
    create_custom_fields(CUSTOM_FIELDS)
    if "india_compliance" in frappe.get_installed_apps():
        create_custom_fields(INDIA_SPECIFIC_CUSTOM_FIELDS)
