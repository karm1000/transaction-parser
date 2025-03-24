import frappe

from transaction_parser.transaction_parser.document_generators.transaction import (
    TransactionGenerator,
)


class SalesOrderGenerator(TransactionGenerator):
    # TODO: remove dependency of methods on each other

    DOCTYPE = "Sales Order"
    PARTY_DOCTYPE = "Customer"

    def __init__(self):
        super().__init__()

        self.vendor = None
        self.buyer_billing = None
        self.buyer_shipping = None
        self.items = None

    def set_details(self):
        self.initialize()
        self.set_po_number()
        self.set_po_date()
        self.set_delivery_date()
        self.set_currency()
        self.set_company()
        self.set_customer()
        self.set_company_address()
        self.set_customer_address()
        self.set_shipping_address()
        self.set_items()

    def initialize(self):
        _document_details = self.parsed_data.document_details
        _buyer = self.parsed_data.document_details.buyer

        self.vendor = _document_details.vendor
        self.buyer_billing = _buyer.billing
        self.buyer_shipping = _buyer.shipping
        self.items = self.parsed_data.document_items

    def set_po_number(self):
        self.doc.po_no = self.get_document_number()

    def set_po_date(self):
        self.doc.po_date = self.get_document_date()

    def set_delivery_date(self):
        self.doc.delivery_date = self.get_delivery_date()

    def get_delivery_date(self):
        return self.parsed_data.document_details.delivery_date

    def set_company(self):
        self.doc.company = self.get_company()

    def get_company(self):
        if found := super().get_company(self.vendor.name):
            return found

        if found := super().get_company(self.buyer_billing.name):
            self.vendor, self.buyer_billing = self.buyer_billing, self.vendor
            return found

        if found := super().get_company(self.buyer_shipping.name):
            self.vendor, self.buyer_shipping = self.buyer_shipping, self.vendor
            return found

    def set_customer(self):
        self.doc.customer = self.get_customer()

    def get_customer(self):
        if found := super().get_party(self.buyer_billing.name):
            return found

        if found := super().get_party(self.buyer_shipping.name):
            return found

        if found := super().get_party(self.vendor.name):
            # TODO: some flag to remember inversion state
            return found

    def set_company_address(self):
        self.doc.company_address = self.get_company_address()

    def get_company_address(self):
        _company = self.doc.company

        if not _company:
            return

        if found := super().get_company_address(_company, self.vendor.address):
            return found

    def set_customer_address(self):
        self.doc.customer_address = self.get_customer_address()

    def get_customer_address(self):
        _customer = self.doc.customer

        if not _customer:
            return

        if found := super().get_party_address(
            _customer, self.buyer_billing.address, "Billing"
        ):
            return found

        if found := super().get_party_address(
            _customer, self.buyer_billing.address, "Shipping"
        ):
            self.buyer_billing, self.buyer_shipping = (
                self.buyer_shipping,
                self.buyer_billing,
            )
            return found

    def set_shipping_address(self):
        self.doc.shipping_address_name = self.get_shipping_address()

    def get_shipping_address(self):
        _customer = self.doc.customer

        if not _customer:
            return

        if found := super().get_party_address(
            _customer, self.buyer_shipping.address, "Shipping"
        ):
            return found

        if found := super().get_party_address(
            _customer, self.buyer_shipping.address, "Billing"
        ):
            # TODO: some flag to remember inversion state
            return found

    def set_items(self):
        self.doc.items = self.get_items()

    def get_items(self):
        return [self.get_item(item) for item in self.items]

    def get_item(self, item):
        _item = super().get_item(item, self.doc.company, self.doc.currency)
        _item.customer_item_code = item.party_item_code

        return frappe.get_doc(
            {
                "doctype": "Sales Order Item",
                "parentfield": "items",
                **_item,
            }
        )

    def get_item_code(self, item):
        return frappe.db.get_value(
            "Item Customer Detail",
            filters={
                "parenttype": "Item",
                "customer_name": self.doc.customer,
                "ref_code": item.party_item_code,
            },
            fieldname="parent",
        )
