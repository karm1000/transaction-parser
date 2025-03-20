import frappe

from transaction_parser.transaction_parser.document_generators.transaction import (
    Transaction,
)


class SalesOrder(Transaction):
    DOCTYPE = "Sales Order"

    def set_details(self):
        super().set_details()
        # Add Sales Order specific details here
