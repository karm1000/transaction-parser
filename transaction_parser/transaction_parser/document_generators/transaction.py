import frappe
from erpnext.stock.get_item_details import get_item_details
from frappe import _
from rapidfuzz import process


class TransactionGenerator:
    DOCTYPE = None
    PARTY_DOCTYPE = None

    def __init__(self):
        if not self.DOCTYPE:
            raise NotImplementedError("DOCTYPE is not defined")

        self.parsed_data = None
        self.doc = None
        self.is_company_party_inverted = False

        self.companies = None
        self.parties = None
        self.currencies = None

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

    ### Party
    def get_party(self, company, party):
        if not self.PARTY_DOCTYPE:
            raise NotImplementedError("PARTY_DOCTYPE is not defined")

        if found := frappe.db.exists(
            self.PARTY_DOCTYPE, {"name": ["in", [company, party]]}
        ):
            if found == company:
                self.is_company_party_inverted = True

            return found

        if found := self.guess_party(party):
            return found

        if found := self.guess_party(company):
            self.is_company_party_inverted = True
            return found

        frappe.throw(_("Could not find Party"))

    def guess_party(self, party):
        return self.guess_value(party, self._get_all_parties())

    def _get_all_parties(self):
        if not self.parties:
            self.parties = frappe.db.get_all(self.PARTY_DOCTYPE, pluck="name")

        return self.parties

    ### Address
    def get_company_address(self, company, address):
        return self.get_address(company, address, "Company")

    def get_party_address(self, party, address):
        return self.get_address(party, address, self.PARTY_DOCTYPE)

    def get_address(self, company, address, doctype):
        addresses = frappe.get_all(
            "Dynamic Link",
            filters={
                "parenttype": "Address",
                "link_doctype": doctype,
                "link_name": company,
            },
            pluck="parent",
        )

        if found := frappe.db.exists(
            "Address",
            {
                "pincode": address.postal_code,
                "name": ["in", addresses],
            },
        ):
            return found

        frappe.throw(_("Could not find Address"))

    ### Currency
    def get_currency(self, currency):
        if found := frappe.db.exists("Currency", {"name": currency}):
            return found

        # TODO: review => is guess required ???
        if found := self.guess_currency(currency):
            return found

        frappe.throw(_("Could not find Currency"))

    def guess_currency(self, currency):
        return self.guess_value(currency, self._get_all_currencies())

    def _get_all_currencies(self):
        if not self.currencies:
            self.currencies = frappe.db.get_all("Currency", pluck="name")

        return self.currencies

    ### Items
    def get_items(self, items, company=None, currency=None):
        return [self.get_item(item, company, currency) for item in items]

    def get_item(self, item, company, currency):
        _item = frappe._dict()

        _item.qty = item.quantity
        _item.rate = item.rate
        _item.amount = item.amount
        _item.party_item_code = item.party_item_code
        _item.item_code = self.get_item_code(_item)

        return {
            **self._get_item_details(_item, company, currency),
            **_item,
        }

    ### Item Code
    def get_item_code(self, item):
        # TODO: Implement
        pass

    ### Item Details from ERP
    def _get_item_details(self, item, company, currency):
        if not (item.item_code and company and currency):
            return {}

        return get_item_details(
            {
                "item_code": item.item_code,
                "qty": item.qty,
                "rate": item.rate,
                "company": company,
                "currency": currency,
                "doctype": self.DOCTYPE,
            }
        )

    ### Utility
    def guess_value(self, parsed_value, options, score_cutoff=80):
        if result := process.extractOne(
            parsed_value, options, score_cutoff=score_cutoff
        ):
            return result[0]
