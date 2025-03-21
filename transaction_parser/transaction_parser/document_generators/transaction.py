import frappe
from erpnext import get_default_company, get_default_currency
from erpnext.stock.get_item_details import get_item_details
from rapidfuzz import process


class TransactionGenerator:
    DOCTYPE = None

    def __init__(self):
        if not self.DOCTYPE:
            raise NotImplementedError("DOCTYPE is not defined")

        self.parsed_data = None
        self.doc = None
        self.company_names = None
        self.item_names = None
        self.uoms = None

    def generate(self, parsed_data):
        self.parsed_data = parsed_data
        self.doc = frappe.new_doc(self.DOCTYPE)

        self.set_details()
        self.set_flags()

        return self.doc.save()

    def set_details(self):
        raise NotImplementedError(
            "set_details() method must be implemented by subclass"
        )

    def set_flags(self):
        self.doc.flags.ignore_permissions = True
        self.doc.flags.ignore_mandatory = True
        self.doc.flags.ignore_validate = True
        self.doc.flags.ignore_links = True

    ### Company
    def get_company(self, company_name, party_name):
        # TODO: review required
        # PROPOSED IDEA:
        # Each transaction will have company in their own specific format
        # E.g.: Sales Order has company in `vendor`, `buyer.billing` and `buyer.shipping` fields
        # So, we can return default company from here
        # Each transaction should have their own implementation of `get_company` method

        parsed_company_name = self.parsed_data.company

        if found := frappe.db.exists(
            "Company", {"name": ["in", [company_name, party_name]]}
        ):
            if found == party_name:
                self.is_company_party_inverted = True

            return found

        if not parsed_company_name:
            return get_default_company()

        return frappe.get_doc("Company", self.guess_company_name(parsed_company_name))

    def guess_company_name(self, parsed_company_name):
        return self.guess_value(parsed_company_name, self._get_company_names())

    def _get_company_names(self):
        if not self.company_names:
            self.company_names = frappe.db.get_all("Company", pluck="name")

        return self.company_names

    ### Currency
    def get_currency(self):
        # TODO: Implement
        pass

    def guess_currency(self, parsed_currency):
        return self.guess_value(parsed_currency, self._get_currencies())

    def _get_currencies(self):
        return frappe.db.get_all("Currency", pluck="name")

    ### Items
    def get_items(self):
        return [self.get_item(parsed_item) for parsed_item in self.parsed_data.items]

    def get_item(self, parsed_item):
        # TODO: Implement
        item = frappe._dict()

        # item.item_name = self.guess_item_name(parsed_item.description)
        item.item_code = self.get_item_code(item.item_name)
        # item.uom = self.guess_item_uom(parsed_item.unit)
        # TODO: customer item code
        item.qty = parsed_item.quantity
        item.rate = parsed_item.rate
        item.amount = parsed_item.amount

        # rate company currency
        # amount company currency
        # net rate
        # net amount
        # net rate company currency
        # net amount company currency
        # item tax template

        return {
            **self._get_item_details(item),
            **item,
        }

    ### Item Name
    def guess_item_name(self, parsed_item_name):
        return self.guess_value(parsed_item_name, self._get_item_names())

    def _get_item_names(self):
        if not self.item_names:
            self.item_names = frappe.db.get_all("Item", pluck="item_name")

        return self.item_names

    ### Item Code
    def get_item_code(self, item_name):
        return frappe.db.get_value(
            "Item",
            filters={"item_name": item_name},
            fieldname="name",
        )

    ### Item UOM
    def guess_item_uom(self, parsed_uom):
        return self.guess_value(parsed_uom, self._get_uoms())

    def _get_uoms(self):
        if not self.uoms:
            self.uoms = frappe.db.get_all("UOM", pluck="name")

        return self.uoms

    ### Item Details from ERP
    def _get_item_details(self, item):
        return get_item_details(
            {
                "item_code": item.item_code,
                "qty": item.qty,
                "rate": item.rate,
                "company": self.doc.company,
                "currency": self.doc.currency,
                "doctype": self.DOCTYPE,
            }
        )

    ### Utility
    def guess_value(self, parsed_value, options, score_cutoff=80):
        # TODO: default `score_cutoff` to some predefined value ???
        return process.extractOne(parsed_value, options, score_cutoff=score_cutoff)[0]
