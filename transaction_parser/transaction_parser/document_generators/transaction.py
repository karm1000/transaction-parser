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

        self.parsed_data = None
        self.doc = None

        self.companies = None
        self.parties = None
        self.addresses = {}

        self.is_company_party_inverted = False

    def generate(self, parsed_data):
        self.parsed_data = parsed_data
        self.doc = frappe.new_doc(self.DOCTYPE)

        self.set_details()
        self.set_attachment()
        self.set_flags()

        return self.doc.save()

    def set_details(self):
        raise NotImplementedError(
            "set_details() method must be implemented by subclass"
        )

    def set_attachment(self):
        # TODO: Implement
        pass

    def set_flags(self):
        self.doc.flags.ignore_permissions = True
        self.doc.flags.ignore_mandatory = True
        self.doc.flags.ignore_validate = True
        self.doc.flags.ignore_links = True

    ### Company
    def get_company(self, company):
        if found := frappe.db.exists("Company", {"name": company}):
            return found

        return self.guess_company(company)

    def guess_company(self, company):
        return self.guess_value(company, self._get_all_companies())

    def _get_all_companies(self):
        if not self.companies:
            self.companies = frappe.db.get_all("Company", pluck="name")

        return self.companies

    ### Party
    def get_party(self, party):
        if found := frappe.db.exists(self.PARTY_DOCTYPE, {"name": party}):
            return found

        return self.guess_party(party)

    def guess_party(self, party):
        return self.guess_value(party, self._get_all_parties())

    def _get_all_parties(self):
        if not self.parties:
            self.parties = frappe.db.get_all(self.PARTY_DOCTYPE, pluck="name")

        return self.parties

    ### Address
    def get_company_address(self, company, address, address_type=None):
        return self.get_address(company, address, address_type, "Company")

    def get_party_address(self, party, address, address_type=None):
        return self.get_address(party, address, address_type, self.PARTY_DOCTYPE)

    def get_address(self, company, address, address_type, linked_doctype):
        addresses = self._get_all_addresses(company, linked_doctype)

        filters = {
            "pincode": address.postal_code,
            "name": ["in", addresses],
        }

        if address_type:
            filters["address_type"] = address_type

        return frappe.db.exists("Address", filters)

    def _get_all_addresses(self, company, linked_doctype):
        # TODO: make key as a combination of company and linked_doctype
        if self.addresses.get(company) is None:
            self.addresses[company] = frappe.get_all(
                "Dynamic Link",
                filters={
                    "parenttype": "Address",
                    "link_doctype": linked_doctype,
                    "link_name": company,
                },
                pluck="parent",
            )

        return self.addresses[company]

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
        return self.parsed_data.document_details.number

    ### Document Date
    def get_document_date(self):
        return self.parsed_data.document_details.date

    ### Currency
    def set_currency(self):
        self.doc.currency = self.get_currency()

    def get_currency(self):
        return self.parsed_data.document_details.currency

    ### Utility
    def guess_value(self, parsed_value, options, score_cutoff=80):
        if result := process.extractOne(
            parsed_value, options, score_cutoff=score_cutoff
        ):
            return result[0]
