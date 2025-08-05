import frappe
from frappe import _

from transaction_parser.transaction_parser.controllers.transaction import Transaction


class Expense(Transaction):
    DOCTYPE = "Purchase Invoice"
    PARTY_DOCTYPE = "Supplier"

    ###################################
    ########## Output Schema ##########
    ###################################

    def get_default_schema(self):
        return {
            **super().get_default_schema(),
            "purchase_order_date": "date | null (Also called `Order Date`. It can be different than Document Date)",
            "company": {
                "shipping": self.get_party_schema(),
                "billing": self.get_party_schema(),
            },
            "supplier": self.get_party_schema(),
        }

    ##################################
    ########## Data Mapping ##########
    ##################################

    def set_details(self):
        self.doc.company = self.get_company()
        if not self.doc.company:
            frappe.throw(_("Company not found"))

        self.doc.supplier = self.get_supplier()

        self.doc.bill_no = self.data.document_number

        if existing_invoice := frappe.db.exists(
            "Purchase Invoice", {"bill_no": self.doc.bill_no, "docstatus": 1}
        ):
            frappe.throw(
                _(
                    "Duplicate Purchase Invoice {existing_invoice} found with Bill number {bill_no}"
                ).format(existing_invoice=existing_invoice, bill_no=self.doc.bill_no)
            )

        self.doc.bill_date = self.data.purchase_order_date
        self.doc.currency = self.data.currency or None

        self.doc.billing_address = self.get_company_billing_address()
        self.doc.shipping_address = self.get_company_shipping_address()
        self.doc.supplier_address = self.get_supplier_address()

        self.doc.contact_person = self.get_contact(
            emails=(
                self.data.company.billing.contact.email
                + self.data.company.shipping.contact.email
            ),
            phones=(
                self.data.company.billing.contact.phone
                + self.data.company.shipping.contact.phone
            ),
        )

        self.doc.items = self.get_items()
        self.doc.terms = self.get_terms()

    def set_missing_values(self):
        self.doc.set_missing_values()
        self.doc.calculate_taxes_and_totals()

    def get_company(self):
        self.company_found_against = "company"
        if self.company:
            return self.company

        party_type = "Company"
        fieldname = "name"

        company_identification_order = (
            ("company", self.data.company.billing),
            ("company", self.data.company.shipping),
            ("supplier", self.data.supplier),
        )

        # search
        for key, party in company_identification_order:
            if found := self.search_party(party, party_type, fieldname):
                self.company_found_against = key
                return found

        # guess
        party_names = frappe.get_all(party_type, pluck="name")
        for key, party in company_identification_order:
            if found := self.guess_party(party, party_type, party_names):
                self.company_found_against = key
                return found

    def get_supplier(self):
        self.supplier_found_against = "supplier"
        if self.party:
            return self.party

        party_type = "Supplier"
        fieldname = "supplier_name"

        supplier_identification_order = (
            ("supplier", self.data.supplier),
            ("company", self.data.company.billing),
            ("company", self.data.company.shipping),
        )

        # search
        for key, party in supplier_identification_order:
            if key == self.company_found_against:
                continue

            if found := self.search_party(party, party_type, fieldname):
                self.supplier_found_against = key
                return found

        # guess
        party_names = dict(
            frappe.get_all(party_type, fields=["name", fieldname], as_list=True)
        )
        for key, party in supplier_identification_order:
            if key == self.company_found_against:
                continue

            if found := self.guess_party(party, party_type, party_names):
                self.supplier_found_against = key
                return found

    def get_company_billing_address(self):
        return self._get_company_address("billing")

    def get_company_shipping_address(self):
        return self._get_company_address("shipping")

    def _get_company_address(self, address_type):
        address_details = (
            getattr(self.data.company, address_type)
            if self.company_found_against == "company"
            else self.data.supplier
        )

        return self.get_address(
            frappe._dict({**address_details, "name": self.doc.company}),
            "Company",
            address_details,
        )

    def get_supplier_address(self):
        supplier_address_details = (
            (self.data.supplier,)
            if self.supplier_found_against == "supplier"
            else (self.data.company.billing, self.data.company.shipping)
        )

        for detail in supplier_address_details:
            if found := self.get_address(
                frappe._dict({**detail, "name": self.doc.supplier}),
                "Supplier",
                detail,
            ):
                return found

    def get_items(self):
        # TODO: Complex logic to handle items
        if not self.data.item_list:
            return []

        # Main logic

        return []

    def get_item(self, item, item_code, **kwargs):
        kwargs["supplier"] = self.doc.supplier

        return frappe.get_doc(
            {
                **super().get_item(item, item_code, **kwargs),
                "doctype": "Purchase Invoice Item",
                "parentfield": "items",
            }
        )
