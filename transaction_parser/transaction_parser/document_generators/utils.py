import frappe
from frappe import _

from transaction_parser.transaction_parser.document_generators import (
    DOCUMENT_GENERATORS,
)


def get_document_generator(country, doctype):
    document_generator = DOCUMENT_GENERATORS.get(country, {}).get(doctype)

    if not document_generator:
        frappe.throw(_(f"No {doctype} Generator found for {country}"))

    return document_generator
