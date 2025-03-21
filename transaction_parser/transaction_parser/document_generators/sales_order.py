import frappe

from transaction_parser.transaction_parser.document_generators.transaction import (
    Transaction,
)


class SalesOrder(Transaction):
    DOCTYPE = "Sales Order"

    def set_details(self):
        pass

    ### Company
    def get_company(self, parsed_company_name):
        pass
