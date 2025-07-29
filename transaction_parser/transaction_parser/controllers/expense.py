import frappe

from transaction_parser.transaction_parser.controllers.transaction import Transaction


class Expense(Transaction):
    DOCTYPE = "Purchase Invoice"
    PARTY_DOCTYPE = "Supplier"

    def set_details(self):
        pass

    def set_missing_values(self):
        pass
