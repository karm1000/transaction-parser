import frappe
from frappe import _

from transaction_parser.transaction_parser.regional_overrides.utils import get_class


def get_document_generator(country, doctype):
    try:
        return get_class(country, doctype, "Generator")

    except Exception:
        frappe.throw(_(f"{doctype} Generator not found for {country}"))
