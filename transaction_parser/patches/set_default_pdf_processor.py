import frappe

from transaction_parser.transaction_parser.utils.pdf_processor import (
    DEFAULT_PDF_PROCESSOR,
)


def execute():
    DOCTYPE = "Transaction Parser Settings"
    FIELD = "pdf_processor"

    if not frappe.db.get_single_value(DOCTYPE, FIELD):
        frappe.db.set_single_value(DOCTYPE, FIELD, DEFAULT_PDF_PROCESSOR)
