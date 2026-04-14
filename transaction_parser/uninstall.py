import frappe

from transaction_parser.install import CUSTOM_FIELDS, INDIA_SPECIFIC_CUSTOM_FIELDS


def before_uninstall():
    delete_custom_fields(CUSTOM_FIELDS)
    delete_custom_fields(INDIA_SPECIFIC_CUSTOM_FIELDS)


def before_app_uninstall(app_name):
    if app_name == "india_compliance":
        delete_custom_fields(INDIA_SPECIFIC_CUSTOM_FIELDS)


def delete_custom_fields(custom_fields):
    for doctype, fields in custom_fields.items():
        fieldnames = [field["fieldname"] for field in fields]
        frappe.db.delete(
            "Custom Field", {"dt": doctype, "fieldname": ("in", fieldnames)}
        )
        frappe.clear_cache(doctype=doctype)
