import frappe

from transaction_parser.transaction_parser.document_generators.transaction import (
    TransactionGenerator,
)

GSTIN_SCORE_CUTOFF = 93
PAN_SCORE_CUTOFF = 90


class IndiaTransactionGenerator(TransactionGenerator):
    def __init__(self):
        # TODO: Design Decision - `Throw error if India Compliance is not installed` OR `silently ignore and continue basic stuffs`

        if "india_compliance" not in frappe.get_installed_apps():
            frappe.throw("Please install India Compliance app for India transactions")

        super().__init__()

    def initialize(self, parsed_data):
        super().initialize(parsed_data)

        self.company_gstins = None
        self.company_pans = None
        self.party_gstins = None
        self.party_pans = None

    ### Company
    def search_company(self, company):
        if found := self.search_company_by_gstin(company.gstin):
            return found

        if found := self.search_company_by_pan(company.pan):
            return found

        return super().search_company(company)

    def search_company_by_gstin(self, gstin):
        return self.search_business_by_gstin(gstin, "Company")

    def search_business_by_gstin(self, gstin, doctype):
        from india_compliance.gst_india.utils import get_party_for_gstin, validate_gstin

        if not gstin:
            return

        try:
            if validate_gstin(gstin):
                return get_party_for_gstin(gstin, doctype)

        except Exception:
            return

    def search_company_by_pan(self, pan):
        return self.search_business_by_pan(pan, "Company")

    def search_business_by_pan(self, pan, doctype):
        from india_compliance.gst_india.utils import is_valid_pan

        if not pan:
            return

        if is_valid_pan(pan):
            return frappe.db.get_value(doctype, {"pan": pan}, fieldname="name")

    def guess_company(self, company):
        if found := self.guess_company_by_gstin(company.gstin):
            return found

        if found := self.guess_company_by_pan(company.pan):
            return found

        return super().guess_company(company)

    def guess_company_by_gstin(self, gstin):
        if found := self.guess_value(
            gstin, self._get_all_company_gstins(), score_cutoff=GSTIN_SCORE_CUTOFF
        ):
            return self._get_all_company_gstins().get(found)

    def _get_all_company_gstins(self):
        if not self.company_gstins:
            self.company_gstins = self._get_all_gstins("Company")

        return self.company_gstins

    def _get_all_gstins(self, doctype):
        return frappe._dict(
            frappe.db.get_all(
                doctype,
                filters={"gstin": ["!=", ""]},
                fields=["gstin", "name"],
                as_list=True,
            )
        )

    def guess_company_by_pan(self, pan):
        if found := self.guess_value(
            pan, self._get_all_company_pans(), score_cutoff=PAN_SCORE_CUTOFF
        ):
            return self._get_all_company_pans().get(found)

    def _get_all_company_pans(self):
        if not self.company_pans:
            self.company_pans = self._get_all_pans("Company")

        return self.company_pans

    def _get_all_pans(self, doctype):
        return frappe._dict(
            frappe.db.get_all(
                doctype,
                filters={"pan": ["!=", ""]},
                fields=["pan", "name"],
                as_list=True,
            )
        )

    ### Party
    def search_party(self, party):
        if found := self.search_party_by_gstin(party.gstin):
            return found

        if found := self.search_party_by_pan(party.pan):
            return found

        return super().search_party(party)

    def search_party_by_gstin(self, gstin):
        return self.search_business_by_gstin(gstin, self.PARTY_DOCTYPE)

    def search_party_by_pan(self, pan):
        return self.search_business_by_pan(pan, self.PARTY_DOCTYPE)

    def guess_party(self, party):
        if found := self.guess_party_by_gstin(party.gstin):
            return found

        if found := self.guess_party_by_pan(party.pan):
            return found

        return super().guess_party(party)

    def guess_party_by_gstin(self, gstin):
        if found := self.guess_value(
            gstin, self._get_all_party_gstins(), score_cutoff=GSTIN_SCORE_CUTOFF
        ):
            return self._get_all_party_gstins().get(found)

    def _get_all_party_gstins(self):
        if not self.party_gstins:
            self.party_gstins = self._get_all_gstins(self.PARTY_DOCTYPE)

        return self.party_gstins

    def guess_party_by_pan(self, pan):
        if found := self.guess_value(
            pan, self._get_all_party_pans(), score_cutoff=PAN_SCORE_CUTOFF
        ):
            return self._get_all_party_pans().get(found)

    def _get_all_party_pans(self):
        if not self.party_pans:
            self.party_pans = self._get_all_pans(self.PARTY_DOCTYPE)

        return self.party_pans
