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

        if not self.PARTY_DOCTYPE:
            raise NotImplementedError("PARTY_DOCTYPE is not defined")

    def generate(self, parsed_data):
        self.initialize(parsed_data)
        self.set_details()
        self.set_flags()

        return self.doc.save()

    def initialize(self, parsed_data):
        self.doc = frappe.new_doc(self.DOCTYPE)

        self.parsed_data = parsed_data
        self.document = parsed_data.document_details
        self.items = parsed_data.document_items
        self.totals = parsed_data.totals

        self.companies = None
        self.parties = None
        self.addresses = {}

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
    def get_company(self, company):
        if found := self.search_company(company):
            return found

        return self.guess_company(company)

    def search_company(self, company):
        _company = company.name

        return _company if _company in self._get_all_companies() else None

    def guess_company(self, company):
        return self.guess_value(company.name, self._get_all_companies())

    def _get_all_companies(self):
        if not self.companies:
            self.companies = self._get_all_businesses("Company")

        return self.companies

    def _get_all_businesses(self, doctype):
        return set(frappe.db.get_all(doctype, pluck="name"))

    ### Party
    def get_party(self, party):
        if found := self.search_party(party):
            return found

        return self.guess_party(party)

    def search_party(self, party):
        _party = party.name

        return _party if _party in self._get_all_parties() else None

    def guess_party(self, party):
        return self.guess_value(party.name, self._get_all_parties())

    def _get_all_parties(self):
        if not self.parties:
            self.parties = self._get_all_businesses(self.PARTY_DOCTYPE)

        return self.parties

    ### Address
    def get_company_address(self, company, address, address_type=None):
        if found := self.get_address(company, address, address_type, "Company"):
            return found

        return frappe.db.get_value("Address", filters={"is_your_company_address": 1})

    def get_party_address(self, party, address, address_type=None):
        return self.get_address(party, address, address_type, self.PARTY_DOCTYPE)

    def get_address(self, business, address, address_type, doctype):
        if found := self.search_address(business, address, address_type, doctype):
            return found

        # TODO: fuzzy match address

    def search_address(self, business, address, address_type, doctype):
        addresses = self._get_all_addresses(business, doctype)

        filters = {
            "pincode": address.postal_code,
            "name": ["in", addresses],
        }

        if address_type:
            filters["address_type"] = address_type

        return frappe.db.exists("Address", filters)

    def _get_all_addresses(self, business, linked_doctype):
        # TODO: make key as a combination of business and linked_doctype
        _business = business.name

        if self.addresses.get(_business) is None:
            self.addresses[_business] = set(
                frappe.get_all(
                    "Dynamic Link",
                    filters={
                        "parenttype": "Address",
                        "link_doctype": linked_doctype,
                        "link_name": _business,
                    },
                    pluck="parent",
                )
            )

        return self.addresses[_business]

    ### Item
    def get_item(self, item, company, currency):
        _item = frappe._dict()

        _item.qty = item.quantity
        _item.rate = item.rate
        _item.amount = item.amount
        _item.party_item_code = item.party_item_code
        _item.item_code = self.get_item_code(_item)

        return frappe._dict(
            {
                **self._get_item_details(_item, company, currency),
                **_item,
            }
        )

    def get_item_code(self, item):
        # TODO: Implement
        pass

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

    ### Document Number
    def get_document_number(self):
        return self.document.number

    ### Document Date
    def get_document_date(self):
        return self.document.date

    ### Currency
    def set_currency(self):
        self.doc.currency = self.get_currency()

    def get_currency(self):
        return self.document.currency

    ### Utility
    def guess_value(self, value, options, score_cutoff=80):
        if result := process.extractOne(value, options, score_cutoff=score_cutoff):
            return result[0]
