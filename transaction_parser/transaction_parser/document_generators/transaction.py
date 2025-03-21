import frappe
from erpnext.stock.get_item_details import get_item_details
from frappe import _
from rapidfuzz import process


class TransactionGenerator:
    DOCTYPE = None

    def __init__(self):
        if not self.DOCTYPE:
            raise NotImplementedError("DOCTYPE is not defined")

        self.parsed_data = None
        self.doc = None

        self.is_company_party_inverted = False
        self.companies = None
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
    def get_company(self, company, party):
        if found := frappe.db.exists("Company", {"name": ["in", [company, party]]}):
            if found == party:
                self.is_company_party_inverted = True

            return found

        if found := self.guess_company(company):
            return found

        if found := self.guess_company(party):
            self.is_company_party_inverted = True
            return found

        frappe.throw(_("Could not find Company"))

    def guess_company(self, company):
        return self.guess_value(company, self._get_all_companies())

    def _get_all_companies(self):
        if not self.companies:
            self.companies = frappe.db.get_all("Company", pluck="name")

        return self.companies

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
        if result := process.extractOne(
            parsed_value, options, score_cutoff=score_cutoff
        ):
            return result[0]
