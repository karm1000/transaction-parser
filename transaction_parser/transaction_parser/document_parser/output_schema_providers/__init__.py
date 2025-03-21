import frappe
from frappe import _

from transaction_parser.transaction_parser.regional_overrides.utils import get_class


def get_output_schema_provider(country, doctype):
    try:
        return get_class(country, doctype, "Schema")

    except Exception:
        frappe.throw(_(f"{doctype} Schema Provider not found for {country}"))
