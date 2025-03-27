import frappe
from erpnext.stock.get_item_details import get_item_details
from rapidfuzz import process

from transaction_parser.transaction_parser.ai_integration.client import get_content
from transaction_parser.transaction_parser.ai_integration.parser import AIParser
from transaction_parser.transaction_parser.utils import to_dict
from transaction_parser.transaction_parser.utils.file_processor import FileProcessor
from transaction_parser.transaction_parser.utils.integration_request import SERVICE_NAME


class Transaction:
    DOCTYPE = None
    PARTY_DOCTYPE = None

    def __init__(self, settings=None):
        if not self.DOCTYPE:
            raise NotImplementedError("DOCTYPE is not defined")

        if not self.PARTY_DOCTYPE:
            raise NotImplementedError("PARTY_DOCTYPE is not defined")

        self.settings = settings or frappe.get_cached_doc("Transaction Parser Settings")

    def generate(self, file_url, page_limit=None):
        self.initialize()

        self.data = self.get_file_content(file_url, page_limit)
        self.doc = frappe.new_doc(self.DOCTYPE)

        self.set_details()
        self.set_flags()

        return self.doc.save()

    def initialize(self):
        # file processing
        self.file_details = None

        # output schema
        self.transaction_schema = None
        self.document_schema = None
        self.tax_schema = None
        self.address_schema = None
        self.party_schema = None
        self.item_schema = None

        # data mapping
        self.data = None
        self.companies = None
        self.parties = None
        self.addresses = {}

        # draft document
        self.doc = None

    #####################################
    ########## File Processing ##########
    #####################################

    def get_file_content(self, file_url, page_limit=None):
        if self.settings.reuse_previously_parsed_data and (
            content := self.get_saved_content(file_url)
        ):
            return content

        return self.parse_file_content(file_url, page_limit)

    def get_saved_content(self, file_url):
        duplicate_names = frappe.get_all(
            "File", filters={"file_url": file_url}, pluck="name"
        )

        filters = {
            "integration_request_service": SERVICE_NAME,
            "status": "Completed",
            "reference_doctype": "File",
            "reference_docname": ["in", duplicate_names],
        }

        response = frappe.db.get_value(
            "Integration Request", filters=filters, fieldname="output"
        )

        if not response:
            return

        response = to_dict(response, throw=False)

        return get_content(response)

    def parse_file_content(self, file_url, page_limit=None):
        processor = FileProcessor()
        file_details = processor.get_details(file_url, page_limit)

        schema = self.get_schema()

        parser = AIParser(self.settings)
        response = parser.parse(
            doctype=self.DOCTYPE,
            schema=schema,
            file_doc_name=file_details.docname,
            data=file_details.content,
        )

        self.file_details = file_details

        return get_content(response)

    ###################################
    ########## Output Schema ##########
    ###################################

    def get_schema(self):
        return self.get_transaction_schema()

    ### Transaction

    def get_transaction_schema(self):
        if not self.transaction_schema:
            self.transaction_schema = self._get_transaction_schema()

        return self.transaction_schema

    def _get_transaction_schema(self):
        return {
            **self.get_default_transaction_schema(),
            **self.get_custom_transaction_schema(),
        }

    def get_default_transaction_schema(self):
        return {
            "document_details": self.get_document_schema(),
            "document_items": [self.get_item_schema()],
            "totals": {
                "subtotal": "float",
                "taxes": [self.get_tax_schema()],
                "total_tax_percentage": "float | null",
                "total_tax_amount": "float | null",
                "grand_total": "float",
            },
            "local_terms": {
                "incoterms": "string (e.g., EXW, DDP, etc.)",
                "description": "string",
            },
        }

    def get_custom_transaction_schema(self):
        return to_dict(self.settings.transaction, throw=False)

    ### Document

    def get_document_schema(self):
        if not self.document_schema:
            self.document_schema = self._get_document_schema()

        return self.document_schema

    def _get_document_schema(self):
        return {
            **self.get_default_document_schema(),
            **self.get_custom_document_schema(),
        }

    def get_default_document_schema(self):
        return {
            "number": "string (unique identifier)",
            "date": "date | null",
            "currency": "ISO currency code (e.g., INR, USD, etc.)",
        }

    def get_custom_document_schema(self):
        return to_dict(self.settings.document, throw=False)

    ### Item

    def get_item_schema(self):
        if not self.item_schema:
            self.item_schema = self._get_item_schema()

        return self.item_schema

    def _get_item_schema(self):
        return {
            **self.get_default_item_schema(),
            **self.get_custom_item_schema(),
        }

    def get_default_item_schema(self):
        return {
            "serial_number": "int | null",
            "party_item_code": "string | null",
            "description": "string",
            "hsn_code": "string",
            "quantity": "float",
            "unit": "string (e.g., KG, MTR, PC, etc.)",
            "rate": "float",
            "amount": "float",
            "taxes": [self.get_tax_schema()],
            "total_tax_percentage": "float | null",
            "total_tax_amount": "float | null",
            "is_price_inclusive_of_taxes": "boolean",
        }

    def get_custom_item_schema(self):
        return to_dict(self.settings.item, throw=False)

    ### Tax

    def get_tax_schema(self):
        if not self.tax_schema:
            self.tax_schema = self._get_tax_schema()

        return self.tax_schema

    def _get_tax_schema(self):
        return {
            **self.get_default_tax_schema(),
            **self.get_custom_tax_schema(),
        }

    def get_default_tax_schema(self):
        return {
            "description": "string",
            "percentage": "float",
            "amount": "float",
        }

    def get_custom_tax_schema(self):
        return to_dict(self.settings.tax, throw=False)

    ### Party

    def get_party_schema(self):
        if not self.party_schema:
            self.party_schema = self._get_party_schema()

        return self.party_schema

    def _get_party_schema(self):
        return {
            **self.get_default_party_schema(),
            **self.get_custom_party_schema(),
        }

    def get_default_party_schema(self):
        return {
            "name": "string",
            "address": self.get_address_schema(),
            "contact": {
                "email": ["string"],
                "phone": ["string"],
            },
        }

    def get_custom_party_schema(self):
        return to_dict(self.settings.party, throw=False)

    ### Address

    def get_address_schema(self):
        if not self.address_schema:
            self.address_schema = self._get_address_schema()

        return self.address_schema

    def _get_address_schema(self):
        return {
            **self.get_default_address_schema(),
            **self.get_custom_address_schema(),
        }

    def get_default_address_schema(self):
        return {
            "address_line_1": "string",
            "address_line_2": "string",
            "city": "string",
            "state": "string",
            "postal_code": "string",
            "country": "ISO country code (e.g., IN, US, etc.)",
        }

    def get_custom_address_schema(self):
        return to_dict(self.settings.address, throw=False)

    ##################################
    ########## Data Mapping ##########
    ##################################

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

    def _get_all_companies(self):
        if not self.companies:
            self.companies = set(frappe.db.get_all("Company", pluck="name"))

        return self.companies

    def guess_company(self, company):
        return self.guess_value(company.name, self._get_all_companies())

    def guess_value(self, value, options, score_cutoff=80):
        if result := process.extractOne(value, options, score_cutoff=score_cutoff):
            return result[0]

    ### Party

    def get_party(self, party):
        if found := self.search_party(party):
            return found

        return self.guess_party(party)

    def search_party(self, party):
        _party = party.name

        return _party if _party in self._get_all_parties() else None

    def _get_all_parties(self):
        if not self.parties:
            self.parties = set(frappe.db.get_all(self.PARTY_DOCTYPE, pluck="name"))

        return self.parties

    def guess_party(self, party):
        return self.guess_value(party.name, self._get_all_parties())

    ### Address

    def get_company_address(self, company, address, address_type=None):
        if found := self.get_address(company, address, address_type, "Company"):
            return found

        return self._get_default_company_address()

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

    def _get_default_company_address(self):
        return frappe.db.get_value("Address", filters={"is_your_company_address": 1})

    def get_party_address(self, party, address, address_type=None):
        return self.get_address(party, address, address_type, self.PARTY_DOCTYPE)

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

    ### Document

    def get_document_number(self):
        return self.data.document_details.number

    def get_document_date(self):
        return self.data.document_details.date

    def get_currency(self):
        return self.data.document_details.currency
