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

    ### Company and Party

    def search_business(self, business, doctype):
        if found := super().search_business(business, doctype):
            return found

        if (business.gstin) and (
            found := self.search_business_by_gstin(business.gstin, doctype)
        ):
            return found

        if (business.pan) and (
            found := self.search_business_by_pan(business.pan, doctype)
        ):
            return found

    def search_business_by_gstin(self, gstin, doctype):
        if not self.is_valid_gstin(gstin):
            return

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

    def search_business_by_pan(self, pan, doctype):
        if not self.is_valid_pan(pan):
            return

        return self.get_business_for_pan(pan, doctype)

    def is_valid_pan(self, pan):
        from india_compliance.gst_india.utils import is_valid_pan

        return is_valid_pan(pan)

    def get_business_for_pan(self, pan, doctype):
        return frappe.db.get_value(doctype, {"pan": pan}, fieldname="name")

    def guess_business(self, business, doctype):
        if found := super().guess_business(business, doctype):
            return found

        if (business.gstin) and (
            found := self.guess_business_by_gstin(business.gstin, doctype)
        ):
            return found

        if (business.pan) and (
            found := self.guess_business_by_pan(business.pan, doctype)
        ):
            return found

    def guess_business_by_gstin(self, gstin, doctype):
        gstins = self._get_all_business_gstins(doctype)

        if found := self.guess_value(
            gstin, gstins.keys(), score_cutoff=GSTIN_SCORE_CUTOFF
        ):
            return gstins.get(found)

    def _get_all_business_gstins(self, doctype):
        """
        Get all GSTINs from the given doctype.

        Example:
        {
            "GSTIN_1": "business_1",
            "GSTIN_2": "business_2",
            ...
        }
        """
        return frappe._dict(
            frappe.db.get_all(
                doctype,
                filters={"gstin": ["!=", ""]},
                fields=["gstin", "name"],
                as_list=True,
            )
        )

    def guess_business_by_pan(self, pan, doctype):
        pans = self._get_all_business_pans(doctype)

        if found := self.guess_value(pan, pans.keys(), score_cutoff=PAN_SCORE_CUTOFF):
            return pans.get(found)

    def _get_all_business_pans(self, doctype):
        """
        Get all PANs from the given doctype.

        Example:
        {
            "PAN_1": "business_1",
            "PAN_2": "business_2",
            ...
        }
        """
        return frappe._dict(
            frappe.db.get_all(
                doctype,
                filters={"pan": ["!=", ""]},
                fields=["pan", "name"],
                as_list=True,
            )
        )

    ### Address

    def search_address(self, business, address, address_type, doctype):
        if found := super().search_address(business, address, address_type, doctype):
            return found

        if (business.gstin) and (found := self.search_address_by_gstin(business.gstin)):
            return found

    def search_address_by_gstin(self, gstin):
        if not self.is_valid_gstin(gstin):
            return

        return self.get_address_for_gstin(gstin)

    def get_address_for_gstin(self, gstin):
        return frappe.db.get_value("Address", {"gstin": gstin})

    ### Item

    def get_item(self, item, company, currency):
        _item = super().get_item(item, company, currency)

        if not item.hsn_code:
            return _item

        return {
            **_item,
            "gst_hsn_code": self.get_hsn_code(item.hsn_code),
        }

    def get_hsn_code(self, hsn_code):
        if found := self.search_hsn_code(hsn_code):
            return found

        return self.guess_hsn_code(hsn_code)

    def search_hsn_code(self, hsn_code):
        return frappe.db.exists("GST HSN Code", {"name": hsn_code})

    def guess_hsn_code(self, hsn_code):
        return self.guess_value(
            hsn_code, self._get_all_hsn_codes(), score_cutoff=HSN_SCORE_CUTOFF
        )

    def _get_all_hsn_codes(self):
        return frappe.get_all("GST HSN Code", pluck="name")


class IndiaSalesOrder(SalesOrder, IndiaTransaction):
    pass
