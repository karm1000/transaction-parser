import frappe
from frappe import _

from transaction_parser.transaction_parser.controllers.sales_order import SalesOrder
from transaction_parser.transaction_parser.controllers.transaction import Transaction

GSTIN_SCORE_CUTOFF = 93
PAN_SCORE_CUTOFF = 90
HSN_SCORE_CUTOFF = 90


class IndiaTransaction(Transaction):
    def __init__(self):
        if "india_compliance" not in frappe.get_installed_apps():
            frappe.throw(
                _("Please install India Compliance app for India transactions")
            )

        super().__init__()

    def initialize(self):
        super().initialize()

        self.company_gstins = None
        self.company_pans = None
        self.party_gstins = None
        self.party_pans = None
        self.hsn_codes = None

    ###################################
    ########## Output Schema ##########
    ###################################

    def get_default_party_schema(self):
        return {
            **super().get_default_party_schema(),
            "gstin": "string (GST Identification Number)",
            "pan": "string (Permanent Account Number)",
        }

    ##################################
    ########## Data Mapping ##########
    ##################################

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
        if not gstin:
            return

        if self.is_valid_gstin(gstin):
            return self.get_business_for_gstin(gstin, doctype)

    def is_valid_gstin(self, gstin):
        from india_compliance.gst_india.utils import validate_gstin

        try:
            return validate_gstin(gstin)

        except Exception:
            return False

    def get_business_for_gstin(self, gstin, doctype):
        from india_compliance.gst_india.utils import get_party_for_gstin

        return get_party_for_gstin(gstin, doctype)

    def search_company_by_pan(self, pan):
        return self.search_business_by_pan(pan, "Company")

    def search_business_by_pan(self, pan, doctype):
        if not pan:
            return

        if self.is_valid_pan(pan):
            return self.get_business_for_pan(pan, doctype)

    def is_valid_pan(self, pan):
        from india_compliance.gst_india.utils import is_valid_pan

        return is_valid_pan(pan)

    def get_business_for_pan(self, pan, doctype):
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

    ### Address

    def search_address(self, business, address, address_type, doctype):
        if found := self.search_address_by_gstin(business.gstin):
            return found

        return super().search_address(business, address, address_type, doctype)

    def search_address_by_gstin(self, gstin):
        if not gstin:
            return

        if self.is_valid_gstin(gstin):
            return self.get_address_for_gstin(gstin)

    def get_address_for_gstin(self, gstin):
        return frappe.db.get_value("Address", {"gstin": gstin})

    ### Item

    def get_item(self, item, company, currency):
        return {
            **super().get_item(item, company, currency),
            "gst_hsn_code": self.get_hsn_code(item.hsn_code),
        }

    def get_hsn_code(self, hsn_code):
        if found := self.search_hsn_code(hsn_code):
            return found

        return self.guess_hsn_code(hsn_code)

    def search_hsn_code(self, hsn_code):
        return hsn_code if hsn_code in self._get_all_hsn_codes() else None

    def guess_hsn_code(self, hsn_code):
        return self.guess_value(
            hsn_code, self._get_all_hsn_codes(), score_cutoff=HSN_SCORE_CUTOFF
        )

    def _get_all_hsn_codes(self):
        if not self.hsn_codes:
            self.hsn_codes = set(frappe.get_all("GST HSN Code", pluck="name"))

        return self.hsn_codes


class IndiaSalesOrder(SalesOrder, IndiaTransaction):
    pass
