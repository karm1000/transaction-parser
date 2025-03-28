import frappe

from transaction_parser.transaction_parser.controllers.transaction import Transaction


class SalesOrder(Transaction):
    DOCTYPE = "Sales Order"
    PARTY_DOCTYPE = "Customer"

    ###################################
    ########## Output Schema ##########
    ###################################

    def get_default_document_schema(self):
        return {
            **super().get_default_document_schema(),
            "delivery_date": "date | null",
            "payment_terms": "string (e.g., '30 days from invoice')",
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
        self.set_po_number()
        self.set_po_date()
        self.set_delivery_date()
        self.set_currency()
        self.set_company()
        self.set_customer()
        self.set_company_address()
        self.set_billing_address()
        self.set_shipping_address()
        self.set_items()

    def set_po_number(self):
        self.doc.po_no = self.get_document_number()

    def set_po_date(self):
        self.doc.po_date = self.get_document_date()

    def set_delivery_date(self):
        self.doc.delivery_date = self.get_delivery_date()

    def get_delivery_date(self):
        return self.data.document_details.delivery_date

    def set_currency(self):
        self.doc.currency = self.get_currency()

    ### Company

    def set_company(self):
        self.doc.company = self.get_company()

    def get_company(self):
        # search
        if found := self.search_company(self.data.document_details.vendor):
            return found

        if found := self.search_company(self.data.document_details.buyer.billing):
            # TODO: some flag to remember inversion state
            return found

        if found := self.search_company(self.data.document_details.buyer.shipping):
            # TODO: some flag to remember inversion state
            return found

        # guess
        if found := self.guess_company(self.data.document_details.vendor):
            return found

        if found := self.guess_company(self.data.document_details.buyer.billing):
            # TODO: some flag to remember inversion state
            return found

        if found := self.guess_company(self.data.document_details.buyer.shipping):
            # TODO: some flag to remember inversion state
            return found

    ### Customer

    def set_customer(self):
        self.doc.customer = self.get_party()

    def get_party(self):
        # search
        if found := self.search_party(self.data.document_details.buyer.billing):
            return found

        if found := self.search_party(self.data.document_details.buyer.shipping):
            return found

        if found := self.search_party(self.data.document_details.vendor):
            # TODO: some flag to remember inversion state
            return found

        # guess
        if found := self.guess_party(self.data.document_details.buyer.billing):
            return found

        if found := self.guess_party(self.data.document_details.buyer.shipping):
            return found

        if found := self.guess_party(self.data.document_details.vendor):
            # TODO: some flag to remember inversion state
            return found

    ### Address

    def set_company_address(self):
        self.doc.company_address = self.get_company_address()

    def get_company_address(self):
        _company = self.doc.company

        if not _company:
            return

        _company = frappe._dict({**self.data.document_details.vendor, "name": _company})

        if found := super().get_company_address(
            _company, self.data.document_details.vendor.address
        ):
            return found

    def set_billing_address(self):
        self.doc.customer_address = self.get_billing_address()

    def get_billing_address(self):
        _customer = self.doc.customer

        if not _customer:
            return

        _customer = frappe._dict(
            {**self.data.document_details.buyer.billing, "name": _customer}
        )

        if found := super().get_party_address(
            _customer, self.data.document_details.buyer.billing.address, "Billing"
        ):
            return found

        if found := super().get_party_address(
            _customer, self.data.document_details.buyer.billing.address, "Shipping"
        ):
            # TODO: some flag to remember inversion state
            return found

    def set_shipping_address(self):
        self.doc.shipping_address_name = self.get_shipping_address()

    def get_shipping_address(self):
        _customer = self.doc.customer

        if not _customer:
            return

        _customer = frappe._dict(
            {**self.data.document_details.buyer.shipping, "name": _customer}
        )

        if found := super().get_party_address(
            _customer, self.data.document_details.buyer.shipping.address, "Shipping"
        ):
            return found

        if found := super().get_party_address(
            _customer, self.data.document_details.buyer.shipping.address, "Billing"
        ):
            # TODO: some flag to remember inversion state
            return found

    ### Items

    def set_items(self):
        self.doc.items = self.get_items()

    def get_items(self):
        return [self.get_item_doc(item) for item in self.data.document_items]

    def get_item_doc(self, item):
        return frappe.get_doc(
            {
                "doctype": "Sales Order Item",
                "parentfield": "items",
                **self.get_item(item),
            }
        )

    def get_item(self, item):
        # NOTE: This method assumes that company and currency have been set in the document.
        return {
            **super().get_item(item, self.doc.company, self.doc.currency),
            "customer_item_code": item.party_item_code,
        }

    def get_item_code(self, item):
        # TODO: reduce to a single database call
        return frappe.db.get_value(
            "Item Customer Detail",
            filters={
                "parenttype": "Item",
                "customer_name": self.doc.customer,
                "ref_code": item.party_item_code,
            },
            fieldname="parent",
        )
