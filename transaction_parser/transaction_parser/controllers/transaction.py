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
        self.party_schema = None
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
            "payment_terms": [
                {
                    "no_of_days_credit": "int",
                    "credit_from": "string | null",
                    "due_date": "date | null",
                    "percent_of_invoice": "float | null",
                }
            ],
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
            "serial_number": "string | null",
            "party_item_code": "string | null (Dont confuse this with serial number)",
            "description": "string",
            "quantity": "float",
            "unit": "string (e.g., KG, MTR, PC, etc.)",
            "rate": "float",
            "amount": "float",
            "taxes": [self.get_tax_schema()],
            "total_tax_percentage": "float | null",
            "total_tax_amount": "float | null",
            "is_price_inclusive_of_taxes": "boolean",
            "delivery_date": "date | null",
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
        return to_dict(self.settings.party_schema, throw=False)

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

    ### Party

    def get_party(self, party, party_type):
        if found := self.search_party(party, party_type):
            return found

        return self.guess_party(party, party_type)

    def search_party(self, party, party_type):
        return frappe.db.exists(party_type, party.name)

    def guess_party(self, party, party_names):
        return self.guess_value(party.name, party_names)

    def guess_value(self, value, options, score_cutoff=80):
        if result := process.extractOne(value, options, score_cutoff=score_cutoff):
            return result[0]

    ### Address

    def get_address(self, party, party_type, address):
        address_doctype = frappe.qb.DocType("Address")
        link_doctype = frappe.qb.DocType("Dynamic Link")

        addresses = (
            frappe.qb.from_(address_doctype)
            .join(link_doctype)
            .on(address_doctype.name == link_doctype.parent)
            .select("*")
            .where(link_doctype.link_doctype == party_type)
            .where(link_doctype.link_name == party.name)
        ).run(as_dict=True)

        for _address in addresses:
            if found := self.search_address(address, _address):
                return found

        return self.guess_address(party, address, addresses)

    def search_address(self, address, erp_address):
        if erp_address.get("pincode") == address.postal_code:
            return erp_address.get("name")

        if erp_address.get("address_line1") == address.address_line_1:
            return erp_address.get("name")

    def guess_address(self, address, addresses):
        address_line_1_map = {
            addr.get("address_line1"): addr.get("name") for addr in addresses
        }

        if found := self.guess_value(address.address_line_1, address_line_1_map.keys()):
            return address_line_1_map.get(found)

    ### Item

    def get_item(self, item, company, currency):
        item_details = {}

        if item.item_code and company and currency:
            item_details = get_item_details(
                {
                    "item_code": item.item_code,
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
                "rate": item.rate,
            }
        )
