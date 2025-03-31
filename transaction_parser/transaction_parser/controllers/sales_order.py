import frappe
from frappe import _

from transaction_parser.transaction_parser.controllers.transaction import Transaction


class SalesOrder(Transaction):
    DOCTYPE = "Sales Order"
    PARTY_DOCTYPE = "Customer"

    ###################################
    ########## Output Schema ##########
    ###################################

    def get_default_schema(self):
        return {
            **super().get_default_schema(),
            "delivery_date": "date | null",
            "project_reference": "string | null",
            "buyer": {
                "shipping": self.get_party_schema(),
                "billing": self.get_party_schema(),
            },
            "vendor": self.get_party_schema(),
        }

    ##################################
    ########## Data Mapping ##########
    ##################################

    def set_details(self):
        self.set_company()
        if not self.doc.company:
            frappe.throw("Company not found")

        self.set_customer()
        # if not self.doc.customer:
        # self.create_party() # as a part of settings / only for india

        self.set_po_number()

        if so_name := frappe.db.exists(
            "Sales Order", {"po_no": self.doc.po_no, "docstatus": 1}
        ):
            frappe.throw(
                _(
                    f"Duplicate Sales Order {so_name} found with PO number {self.doc.po_no}"
                )
            )

        self.set_po_date()
        self.set_delivery_date()
        self.set_currency()
        self.set_company_address()
        self.set_billing_address()
        self.set_shipping_address()
        self.set_items()

        self.doc.set_missing_values()

        # TODO: set a flag in SO (created from transaction parser)
        # TODO: validation of Sales Order on save.

    def set_po_number(self):
        self.doc.po_no = self.get_document_number()

    def set_po_date(self):
        self.doc.po_date = self.get_document_date()

    def set_delivery_date(self):
        self.doc.delivery_date = self.get_delivery_date()

    def get_delivery_date(self):
        return self.data.delivery_date

    def set_currency(self):
        if currency := self.get_currency():
            self.doc.currency = currency

    ### Company

    def set_company(self):
        self.doc.company = self.get_company()

    def get_company(self):
        # search
        if found := self.search_company(self.data.vendor):
            return found

        if found := self.search_company(self.data.buyer.billing):
            # TODO: some flag to remember inversion state
            return found

        if found := self.search_company(self.data.buyer.shipping):
            # TODO: some flag to remember inversion state
            return found

        # guess
        if found := self.guess_company(self.data.vendor):
            return found

        if found := self.guess_company(self.data.buyer.billing):
            # TODO: some flag to remember inversion state
            return found

        if found := self.guess_company(self.data.buyer.shipping):
            # TODO: some flag to remember inversion state
            return found

    ### Customer

    def set_customer(self):
        self.doc.customer = self.get_party()

    def get_party(self):
        # search
        if found := self.search_party(self.data.buyer.billing):
            return found

        if found := self.search_party(self.data.buyer.shipping):
            return found

        if found := self.search_party(self.data.vendor):
            # TODO: some flag to remember inversion state
            return found

        # guess
        if found := self.guess_party(self.data.buyer.billing):
            return found

        if found := self.guess_party(self.data.buyer.shipping):
            return found

        if found := self.guess_party(self.data.vendor):
            # TODO: some flag to remember inversion state
            return found

    ### Address

    def set_company_address(self):
        self.doc.company_address = self.get_company_address()

    def get_company_address(self):
        _company = self.doc.company

        if not _company:
            return

        _company = frappe._dict({**self.data.vendor, "name": _company})

        if found := super().get_company_address(_company, self.data.vendor.address):
            return found

    def set_billing_address(self):
        self.doc.customer_address = self.get_billing_address()

    def get_billing_address(self):
        _customer = self.doc.customer

        if not _customer:
            return

        _customer = frappe._dict({**self.data.buyer.billing, "name": _customer})

        if found := super().get_party_address(
            _customer, self.data.buyer.billing.address, "Billing"
        ):
            return found

        if found := super().get_party_address(
            _customer, self.data.buyer.billing.address, "Shipping"
        ):
            # TODO: some flag to remember inversion state
            return found

    def set_shipping_address(self):
        self.doc.shipping_address_name = self.get_shipping_address()

    def get_shipping_address(self):
        _customer = self.doc.customer

        if not _customer:
            return

        _customer = frappe._dict({**self.data.buyer.shipping, "name": _customer})

        if found := super().get_party_address(
            _customer, self.data.buyer.shipping.address, "Shipping"
        ):
            return found

        if found := super().get_party_address(
            _customer, self.data.buyer.shipping.address, "Billing"
        ):
            # TODO: some flag to remember inversion state
            return found

    ### Items

    def set_items(self):
        self.doc.items = self.get_items()

    def get_items(self):
        if not self.data.item_list:
            return []

        item_codes = self._get_all_item_codes()

        return [
            self.get_item_doc(self.get_item(item, item_codes))
            for item in self.data.item_list
        ]

    def get_item(self, item, item_codes):
        # NOTE: This method assumes that company and currency have been set in the document.
        item.item_code = item_codes.get(item.party_item_code)

        return {
            **super().get_item(item, self.doc.company, self.doc.currency),
            "customer_item_code": item.party_item_code,
        }

    def _get_all_item_codes(self):
        """
        Returns a dictionary that maps customer item code to item code.

        Example:
        {
            "customer_item_code_1": "item_code_1",
            "customer_item_code_2": "item_code_2",
            ...
        }
        """
        customer_item_codes = [item.party_item_code for item in self.data.item_list]

        filters = {
            "parenttype": "Item",
            "customer_name": self.doc.customer,
            "ref_code": ["in", customer_item_codes],
        }

        return frappe._dict(
            frappe.get_all(
                "Item Customer Detail",
                filters=filters,
                fields=["ref_code", "parent"],
                as_list=True,
            )
        )

    def get_item_doc(self, item):
        return frappe.get_doc(
            {
                "doctype": "Sales Order Item",
                "parentfield": "items",
                **item,
            }
        )
