import frappe

from transaction_parser.transaction_parser.document_generators.transaction import (
    TransactionGenerator,
)


class SalesOrderGenerator(TransactionGenerator):
    DOCTYPE = "Sales Order"
    PARTY_DOCTYPE = "Customer"

    def set_details(self):
        pass

    def get_item_code(self, item):
        return frappe.db.get_value(
            "Item Customer Detail",
            filters={
                "parenttype": "Item",
                "ref_code": item.party_item_code,
            },
            fieldname="parent",
        )
