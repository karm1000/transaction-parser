import frappe
from erpnext.stock.get_item_details import get_item_details
from rapidfuzz import process

from transaction_parser.transaction_parser.ai_integration.parser import AIParser
from transaction_parser.transaction_parser.utils import to_dict
from transaction_parser.transaction_parser.utils.file_processor import FileProcessor


class Transaction:
    DOCTYPE = None
    PARTY_DOCTYPE = None

    def __init__(self, settings=None):
        if not self.DOCTYPE:
            raise NotImplementedError("DOCTYPE is not defined")

        if not self.PARTY_DOCTYPE:
            raise NotImplementedError("PARTY_DOCTYPE is not defined")

        self.settings = settings or frappe.get_cached_doc("Transaction Parser Settings")

    def generate(self, file, page_limit=None):
        self.initialize()

        self.file = file
        self.data = self.get_file_content(page_limit)
        self.doc = frappe.get_doc({"doctype": self.DOCTYPE})

        self.set_details()
        self.set_flags()
        self.doc.insert()
        self.attach_file()

        return self.doc

    def initialize(self):
        # file processing
        self.file = None

        # output schema
        self.schema = None
        self.document_schema = None
        self.tax_schema = None
        self.address_schema = None
        self.business_schema = None
        self.item_schema = None

        # data mapping
        self.data = None

        # draft document
        self.doc = None

    #####################################
    ########## File Processing ##########
    #####################################

    # def get_file_content(self, file_url, page_limit=None):
    #     if self.settings.reuse_previously_parsed_data and (
    #         content := self.get_saved_content(file_url)
    #     ):
    #         return content

    #     return self.parse_file_content(file_url, page_limit)

    # def get_saved_content(self, file_url):
    #     duplicate_names = frappe.get_all(
    #         "File", filters={"file_url": file_url}, pluck="name"
    #     )

    #     filters = {
    #         "integration_request_service": SERVICE_NAME,
    #         "status": "Completed",
    #         "reference_doctype": "File",
    #         "reference_docname": ["in", duplicate_names],
    #     }

    #     response = frappe.db.get_value(
    #         "Integration Request", filters=filters, fieldname="output"
    #     )

    #     if not response:
    #         return

    #     response = to_dict(response, throw=False)

    #     return get_content(response)

    def get_file_content(self, page_limit=None):
        processor = FileProcessor()
        content = processor.get_content(self.file, page_limit)

        schema = self.get_schema()

        parser = AIParser(self.settings)
        return parser.parse(
            doctype=self.DOCTYPE,
            schema=schema,
            file_doc_name=self.file.name,
            data=content,
        )

    ###################################
    ########## Output Schema ##########
    ###################################

    def get_schema(self):
        if not self.schema:
            self.schema = self._get_schema()

        return self.schema

    def _get_schema(self):
        return {
            **self.get_default_schema(),
            **self.get_custom_schema(),
        }

    def get_default_schema(self):
        return {
            "document_number": "string (unique identifier)",
            "document_date": "date | null",
            "currency": "ISO currency code (e.g., INR, USD, etc.)",
            "item_list": [self.get_item_schema()],
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

    def get_custom_schema(self):
        return to_dict(self.settings.base_schema, throw=False)

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
        return to_dict(self.settings.item_schema, throw=False)

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
        return to_dict(self.settings.tax_schema, throw=False)

    ### Party

    def get_business_schema(self):
        if not self.business_schema:
            self.business_schema = self._get_business_schema()

        return self.business_schema

    def _get_business_schema(self):
        return {
            **self.get_default_business_schema(),
            **self.get_custom_business_schema(),
        }

    def get_default_business_schema(self):
        return {
            "name": "string",
            "address": self.get_address_schema(),
            "contact": {
                "email": ["string"],
                "phone": ["string"],
            },
        }

    def get_custom_business_schema(self):
        return to_dict(self.settings.business_schema, throw=False)

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
        return to_dict(self.settings.address_schema, throw=False)

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

    def attach_file(self):
        self.file.attached_to_doctype = self.DOCTYPE
        self.file.attached_to_name = self.doc.name
        self.file.save()

    ### Company

    def get_company(self, company):
        if found := self.search_company(company):
            return found

        return self.guess_company(company)

    def search_company(self, company):
        return self.search_business(company, "Company")

    def search_business(self, business, doctype):
        return frappe.db.exists(doctype, business.name)

    def guess_company(self, company):
        return self.guess_business(company, "Company")

    def guess_business(self, business, doctype):
        return self.guess_value(business.name, self._get_all_businesses(doctype))

    def _get_all_businesses(self, doctype):
        return frappe.db.get_all(doctype, pluck="name")

    def guess_value(self, value, options, score_cutoff=80):
        if result := process.extractOne(value, options, score_cutoff=score_cutoff):
            return result[0]

    ### Party

    def get_party(self, party):
        if found := self.search_party(party):
            return found

        return self.guess_party(party)

    def search_party(self, party):
        return self.search_business(party, self.PARTY_DOCTYPE)

    def guess_party(self, party):
        return self.guess_business(party, self.PARTY_DOCTYPE)

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
        address_table = frappe.qb.DocType("Address")
        link_table = frappe.qb.DocType("Dynamic Link")

        query = (
            frappe.qb.from_(address_table)
            .join(link_table)
            .on(address_table.name == link_table.parent)
            .select(address_table.name)
            .limit(1)
            .where(link_table.link_doctype == doctype)
            .where(link_table.link_name == business.name)
            .where(address_table.pincode == address.postal_code)
        )

        if address_type:
            query = query.where(address_table.pincode == address.postal_code)

        if found := query.run():
            return found[0][0]

    # def _get_all_addresses(self, business, linked_doctype):
    #     """
    #     Returns a list addresses for a given business.

    #     Example:
    #     self.addresses = {
    #         "business_1": [ "address_1", "address_2", ... ],
    #         "business_2": [ "address_1", "address_2", ... ],
    #         ...
    #     }
    #     """
    #     # TODO: make key as a combination of business and linked_doctype
    #     _business = business.name

    #     if self.addresses.get(_business) is None:
    #         self.addresses[_business] = set(
    #             frappe.get_all(
    #                 "Dynamic Link",
    #                 filters={
    #                     "parenttype": "Address",
    #                     "link_doctype": linked_doctype,
    #                     "link_name": _business,
    #                 },
    #                 pluck="parent",
    #             )
    #         )

    #     return self.addresses[_business]

    def _get_default_company_address(self):
        return frappe.db.get_value("Address", filters={"is_your_company_address": 1})

    def get_party_address(self, party, address, address_type=None):
        return self.get_address(party, address, address_type, self.PARTY_DOCTYPE)

    ### Item

    def get_item(self, item, company, currency):
        item_details = {}

        if item.item_code and company and currency:
            item_details = get_item_details(
                {
                    "item_code": item.item_code,
                    "qty": item.quantity,
                    "rate": item.rate,
                    "company": company,
                    "currency": currency,
                    "doctype": self.DOCTYPE,
                }
            )

        return frappe._dict(
            {
                **item_details,
                **item,
                "qty": item.quantity,
            }
        )

    ### Document

    def get_document_number(self):
        return self.data.document_number

    def get_document_date(self):
        return self.data.document_date

    def get_currency(self):
        return self.data.currency
