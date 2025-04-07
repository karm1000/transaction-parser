from frappe.custom.doctype.custom_field.custom_field import (
    create_custom_fields,
)

custom_fields = {
    "Sales Order": [
        {
            "fieldname": "is_created_by_transaction_parser",
            "fieldtype": "Check",
            "label": "Is Created By Transaction Parser",
            "read_only": 1,
            "insert_after": "is_internal_customer",
        }
    ]
}


def after_install():
    create_custom_fields(custom_fields)
