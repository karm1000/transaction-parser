import frappe

from transaction_parser.transaction_parser.document_generators.transaction import (
    Transaction,
)


class SalesOrder(Transaction):
    DOCTYPE = "Sales Order"

    def set_details(self):
        company_name = self.get_company()

        if not company_name:
            # Notification with link to error log
            raise ValueError("Company {0} not found".format(self.parsed_data.company))

    ### Company
    def get_company(self, parsed_company_name):
        pass
