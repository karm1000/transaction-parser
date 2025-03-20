import frappe

from transaction_parser.transaction_parser.document_generators.transaction import (
    Transaction,
)


class SalesOrder(Transaction):
    DOCTYPE = "Sales Order"

    def generate(self, parsed_data):
        pass
