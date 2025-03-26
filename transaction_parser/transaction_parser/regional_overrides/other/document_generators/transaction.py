import frappe

from transaction_parser.transaction_parser.document_generators.transaction import (
    TransactionGenerator,
)

TAX_ID_SCORE_CUTOFF = 90


class OtherTransactionGenerator(TransactionGenerator):
    def initialize(self, parsed_data):
        super().initialize(parsed_data)

        self.company_tax_ids = None
        self.party_tax_ids = None

    ### Company
    def search_company(self, company):
        if found := self.search_company_by_tax_id(company.tax_id):
            return found

        return super().search_company(company)

    def search_company_by_tax_id(self, tax_id):
        return self.search_business_by_tax_id(tax_id, "Company")

    def search_business_by_tax_id(self, tax_id, doctype):
        if self.is_valid_tax_id(tax_id):
            return self.get_business_for_tax_id(tax_id, doctype)

    def is_valid_tax_id(self, tax_id):
        # TODO: Implement
        return True

    def get_business_for_tax_id(self, tax_id, doctype):
        return frappe.db.get_value(doctype, {"tax_id": tax_id})

    def guess_company(self, company):
        if found := self.guess_company_by_tax_id(company.tax_id):
            return found

        return super().guess_company(company)

    def guess_company_by_tax_id(self, tax_id):
        if found := self.guess_value(
            tax_id, self._get_all_company_tax_ids(), score_cutoff=TAX_ID_SCORE_CUTOFF
        ):
            return self._get_all_company_tax_ids().get(found)

    def _get_all_company_tax_ids(self):
        if not self.company_tax_ids:
            self.company_tax_ids = self._get_all_tax_ids("Company")

        return self.company_tax_ids

    def _get_all_tax_ids(self, doctype):
        return frappe._dict(
            frappe.db.get_all(
                doctype,
                filters={"tax_id": ["!=", ""]},
                fields=["tax_id", "name"],
                as_list=True,
            )
        )

    ### Party
    def search_party(self, party):
        if found := self.search_party_by_tax_id(party.tax_id):
            return found

        return super().search_party(party)

    def search_party_by_tax_id(self, tax_id):
        return self.search_business_by_tax_id(tax_id, self.PARTY_DOCTYPE)

    def guess_party(self, party):
        if found := self.guess_party_by_tax_id(party.tax_id):
            return found

        return super().guess_party(party)

    def guess_party_by_tax_id(self, tax_id):
        if found := self.guess_value(
            tax_id, self._get_all_party_tax_ids(), score_cutoff=TAX_ID_SCORE_CUTOFF
        ):
            return self._get_all_party_tax_ids().get(found)

    def _get_all_party_tax_ids(self):
        if not self.party_tax_ids:
            self.party_tax_ids = self._get_all_tax_ids(self.PARTY_DOCTYPE)

        return self.party_tax_ids
