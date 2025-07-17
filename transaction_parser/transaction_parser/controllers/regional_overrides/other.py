import frappe

from transaction_parser.transaction_parser.controllers.sales_order import SalesOrder
from transaction_parser.transaction_parser.controllers.transaction import Transaction

TAX_ID_SCORE_CUTOFF = 90


class OtherTransaction(Transaction):
    ###################################
    ########## Output Schema ##########
    ###################################

    def get_default_party_schema(self):
        return {
            **super().get_default_party_schema(),
            "tax_id": "string (Country Specific Unique Tax Identifier)",
        }

    ##################################
    ########## Data Mapping ##########
    ##################################

    def search_party(self, party, party_type):
        if self.is_valid_tax_id(party.tax_id) and (
            found := frappe.db.get_value(party_type, {"tax_id": party.tax_id})
        ):
            return found

        return super().search_party(party, party_type)

    def is_valid_tax_id(self, tax_id):
        if not tax_id:
            return False

        # TODO: check length of tax_id ?

        return True

    def guess_party(self, party, party_type, party_names=None):
        if party.tax_id:
            party_tax_ids = frappe._dict(
                frappe.db.get_all(
                    party_type,
                    filters={"tax_id": ["!=", ""]},
                    fields=["tax_id", "name"],
                    as_list=True,
                )
            )

            if found := self.guess_value(
                party.tax_id, party_tax_ids.keys(), score_cutoff=TAX_ID_SCORE_CUTOFF
            ):
                return party_tax_ids.get(found)

        return super().guess_party(party, party_type, party_names)


class OtherSalesOrder(SalesOrder, OtherTransaction):
    pass
