import frappe
from frappe import _
from india_compliance.gst_india.overrides.party import create_primary_address
from india_compliance.gst_india.utils.gstin_info import _get_gstin_info

from transaction_parser.transaction_parser.controllers.expense import Expense
from transaction_parser.transaction_parser.controllers.sales_order import SalesOrder
from transaction_parser.transaction_parser.controllers.transaction import Transaction

GSTIN_SCORE_CUTOFF = 93
PAN_SCORE_CUTOFF = 90
HSN_SCORE_CUTOFF = 90


class IndiaTransaction(Transaction):
    def __init__(self, party=None, company=None):
        if "india_compliance" not in frappe.get_installed_apps():
            frappe.throw(
                _("Please install India Compliance app for India transactions")
            )

        super().__init__(party=party, company=company)

    ###################################
    ########## Output Schema ##########
    ###################################

    def get_default_item_schema(self):
        return {
            **super().get_default_item_schema(),
            "hsn_code": "string",
        }

    def get_default_party_schema(self):
        return {
            **super().get_default_party_schema(),
            "gstin": "string (GST Identification Number)",
            "pan": "string (Permanent Account Number)",
        }

    ##################################
    ########## Data Mapping ##########
    ##################################

    ### Party

    def search_party(self, party, party_type, fieldname="name"):
        from india_compliance.gst_india.utils import get_party_for_gstin

        if self.is_valid_gstin(party.gstin):
            return get_party_for_gstin(party.gstin, party_type)

        if self.is_valid_pan(party.pan) and (
            found := frappe.db.get_value(party_type, {"pan": party.pan})
        ):
            return found

        return super().search_party(party, party_type, fieldname)

    def is_valid_gstin(self, gstin):
        from india_compliance.gst_india.utils import validate_gstin

        try:
            return validate_gstin(gstin)

        except frappe.ValidationError:
            return False

    def is_valid_pan(self, pan):
        from india_compliance.gst_india.utils import is_valid_pan

        if not pan:
            return False

        return is_valid_pan(pan)

    def guess_party(self, party, party_type, party_names=None):
        if party.gstin:
            party_gstins = frappe._dict(
                frappe.db.get_all(
                    party_type,
                    filters={"gstin": ["!=", ""]},
                    fields=["gstin", "name"],
                    as_list=True,
                )
            )

            if found := self.guess_value(
                party.gstin, party_gstins.keys(), score_cutoff=GSTIN_SCORE_CUTOFF
            ):
                return party_gstins.get(found)

        if party.pan:
            party_pans = frappe._dict(
                frappe.db.get_all(
                    party_type,
                    filters={"pan": ["!=", ""]},
                    fields=["pan", "name"],
                    as_list=True,
                )
            )

            if found := self.guess_value(
                party.pan, party_pans.keys(), score_cutoff=PAN_SCORE_CUTOFF
            ):
                return party_pans.get(found)

        return super().guess_party(party, party_type, party_names)

    ### Address

    def search_address(self, party, address, erp_address):
        if self.is_valid_gstin(party.gstin) and (party.gstin == erp_address.gstin):
            return erp_address.name

        return super().search_address(party, address, erp_address)

    def guess_address(self, party, address, erp_addresses):
        gstin_map = {
            erp_address.gstin: erp_address.name for erp_address in erp_addresses
        }

        if found := self.guess_value(
            party.gstin, gstin_map.keys(), score_cutoff=GSTIN_SCORE_CUTOFF
        ):
            return gstin_map.get(found)

        return super().guess_address(party, address, erp_addresses)

    ### Item

    def get_item(self, item, item_code, **kwargs):
        return {
            **super().get_item(item, item_code, **kwargs),
            "gst_hsn_code": (
                item.hsn_code if self.is_valid_hsn_code(item.hsn_code) else None
            ),
        }

    def is_valid_hsn_code(self, hsn_code):
        from india_compliance.gst_india.doctype.gst_hsn_code.gst_hsn_code import (
            validate_hsn_code,
        )

        try:
            validate_hsn_code(hsn_code)
            return True

        except frappe.ValidationError:
            return False


class IndiaSalesOrder(SalesOrder, IndiaTransaction):
    pass


class IndiaExpense(Expense, IndiaTransaction):
    def get_supplier(self):
        if found := super().get_supplier():
            return found

        if not self.settings.in_auto_create_supplier:
            return

        return self.create_supplier()

    def create_supplier(self):
        gstin = self.data.supplier.gstin
        if not gstin:
            return

        try:
            gstin_info = _get_gstin_info(gstin)
            address = gstin_info.permanent_address
            if not address:
                return

            address = frappe._dict(address)

            supplier = frappe.new_doc("Supplier")
            supplier.update(
                {
                    "supplier_name": gstin_info.business_name,
                    "gstin": gstin_info.gstin,
                    "_address_line1": address.address_line1,
                    "address_line2": address.address_line2,
                    "city": address.city,
                    "state": address.state,
                    "country": address.country,
                    "pincode": address.pincode,
                }
            )
            supplier.save(ignore_permissions=True)
            create_primary_address(supplier)

            return supplier.name

        except Exception as e:
            frappe.log_error(title="Error creating supplier from GSTIN")
            raise e
