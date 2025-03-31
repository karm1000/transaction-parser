import frappe

from transaction_parser.transaction_parser.controllers.sales_order import SalesOrder
from transaction_parser.transaction_parser.controllers.transaction import Transaction

TAX_ID_SCORE_CUTOFF = 90


class OtherTransaction(Transaction):
    ###################################
    ########## Output Schema ##########
    ###################################

    def get_default_business_schema(self):
        return {
            **super().get_default_business_schema(),
            "tax_id": "string (Country Specific Unique Tax Identifier)",
        }

    ##################################
    ########## Data Mapping ##########
    ##################################

    ### Company and Party
    def search_business(self, business, doctype):
        if found := super().search_business(business, doctype):
            return found

        if (business.tax_id) and (
            found := self.search_business_by_tax_id(business.tax_id, doctype)
        ):
            return found

    def search_business_by_tax_id(self, tax_id, doctype):
        if not self.is_valid_tax_id(tax_id):
            return

        return self.get_business_for_tax_id(tax_id, doctype)

    def is_valid_tax_id(self, tax_id):
        # TODO: Implement
        return True

    def get_business_for_tax_id(self, tax_id, doctype):
        return frappe.db.get_value(doctype, {"tax_id": tax_id})

    def guess_business(self, business, doctype):
        if found := super().guess_business(business, doctype):
            return found

        if (business.tax_id) and (
            found := self.guess_business_by_tax_id(business.tax_id, doctype)
        ):
            return found

    def guess_business_by_tax_id(self, tax_id, doctype):
        tax_ids = self._get_all_business_tax_ids(doctype)

        if found := self.guess_value(
            tax_id, tax_ids.keys(), score_cutoff=TAX_ID_SCORE_CUTOFF
        ):
            return tax_ids.get(found)

    def _get_all_business_tax_ids(self, doctype):
        """
        Get all tax IDs for a given doctype.

        Example:
        {
            "TAX_ID_1": "business_1",
            "TAX_ID_2": "business_2",
            ...
        }
        """
        return frappe._dict(
            frappe.db.get_all(
                doctype,
                filters={"tax_id": ["!=", ""]},
                fields=["tax_id", "name"],
                as_list=True,
            )
        )


class OtherSalesOrder(SalesOrder, OtherTransaction):
    pass
