import frappe
import frappe.utils
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
            "purchase_order_date": "date | null (Also called `Order Date`. It can be different than Document Date)",
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
        self.doc.company = self.get_company()
        if not self.doc.company:
            frappe.throw("Company not found")

        self.doc.customer = self.get_customer()
        # if not self.doc.customer:
        #     self.create_party()

        self.doc.po_no = self.data.document_number
        if so_name := frappe.db.exists(
            "Sales Order", {"po_no": self.doc.po_no, "docstatus": 1}
        ):
            frappe.throw(
                _(
                    f"Duplicate Sales Order {so_name} found with PO number {self.doc.po_no}"
                )
            )

        self.doc.po_date = self.data.purchase_order_date
        self.doc.delivery_date = self.data.delivery_date
        self.doc.currency = self.data.currency or None

        self.doc.company_address = self.get_company_address()
        self.doc.customer_address = self.get_billing_address()
        self.doc.shipping_address_name = self.get_shipping_address()

        self.doc.contact_person = self.get_contact(
            emails=(
                self.data.buyer.billing.contact.email
                + self.data.buyer.shipping.contact.email
            ),
            phones=(
                self.data.buyer.billing.contact.phone
                + self.data.buyer.shipping.contact.phone
            ),
        )

        self.doc.items = self.get_items()
        # self.doc.payment_schedule = self.get_payment_schedule()
        self.doc.terms = self.get_terms()

        today = frappe.utils.today()
        self.doc.transaction_date = (
            delivery_date
            if (delivery_date := self.doc.delivery_date) and (delivery_date < today)
            else today
        )

        # TODO: set a flag in SO (created from transaction parser)
        # TODO: validation of Sales Order on save.

    def set_missing_values(self):
        self.doc.set_missing_values()

    ### Company

    def get_company(self):
        party_type = "Company"

        # search

        if found := self.search_party(self.data.vendor, party_type):
            return found

        if found := self.search_party(self.data.buyer.billing, party_type):
            # TODO: some flag to remember inversion state
            return found

        if found := self.search_party(self.data.buyer.shipping, party_type):
            # TODO: some flag to remember inversion state
            return found

        # guess

        party_names = frappe.get_all(party_type, pluck="name")

        if found := self.guess_party(self.data.vendor, party_type, party_names):
            return found

        if found := self.guess_party(self.data.buyer.billing, party_type, party_names):
            # TODO: some flag to remember inversion state
            return found

        if found := self.guess_party(self.data.buyer.shipping, party_type, party_names):
            # TODO: some flag to remember inversion state
            return found

    ### Customer

    def get_customer(self):
        party_type = "Customer"

        # search

        if found := self.search_party(self.data.buyer.billing, party_type):
            return found

        if found := self.search_party(self.data.buyer.shipping, party_type):
            return found

        if found := self.search_party(self.data.vendor, party_type):
            # TODO: some flag to remember inversion state
            return found

        # guess

        party_names = frappe.get_all(party_type, pluck="name")

        if found := self.guess_party(self.data.buyer.billing, party_type, party_names):
            return found

        if found := self.guess_party(self.data.buyer.shipping, party_type, party_names):
            return found

        if found := self.guess_party(self.data.vendor, party_type, party_names):
            # TODO: some flag to remember inversion state
            return found

    # def create_party(self):
    #     # TODO: Implement
    #     # as a part of settings / only for india
    #     # from india_compliance API
    #     pass

    ### Address

    def get_company_address(self):
        if found := self.get_address(
            frappe._dict({**self.data.vendor, "name": self.doc.company}),
            "Company",
            self.data.vendor.address,
        ):
            return found

    def get_billing_address(self):
        if found := self.get_address(
            frappe._dict({**self.data.buyer.billing, "name": self.doc.customer}),
            "Customer",
            self.data.buyer.billing.address,
        ):
            return found

    def get_shipping_address(self):
        if found := self.get_address(
            frappe._dict({**self.data.buyer.shipping, "name": self.doc.customer}),
            "Customer",
            self.data.buyer.shipping.address,
        ):
            return found

    ### Items

    def get_items(self):
        if not self.data.item_list:
            return []

        customer_item_codes = [item.party_item_code for item in self.data.item_list]

        filters = {
            "parenttype": "Item",
            "customer_name": self.doc.customer,
            "ref_code": ["in", customer_item_codes],
        }

        item_codes = frappe._dict(
            frappe.get_all(
                "Item Customer Detail",
                filters=filters,
                fields=["ref_code", "parent"],
                as_list=True,
            )
        )

        items = [
            self.get_item(item, item_codes.get(item.party_item_code))
            for item in self.data.item_list
        ]

        for idx, item in enumerate(items):
            item.idx = idx + 1

        return items

    def get_item(self, item, item_code, **kwargs):
        kwargs["customer"] = self.doc.customer

        return frappe.get_doc(
            {
                **super().get_item(item, item_code, **kwargs),
                "doctype": "Sales Order Item",
                "parentfield": "items",
                "customer_item_code": item.party_item_code,
            }
        )
