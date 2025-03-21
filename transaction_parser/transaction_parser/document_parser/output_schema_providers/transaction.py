import frappe

from transaction_parser.transaction_parser.utils import to_dict


class TransactionSchema:
    def __init__(self, settings=None):
        self.settings = settings or frappe.get_cached_doc("Transaction Parser Settings")

        self.transaction = None
        self.document = None
        self.tax = None
        self.address = None
        self.party = None
        self.item = None

    def get_schema(self):
        return {
            **self.get_transaction_schema(),
            "document_details": self.get_document_schema(),
        }

    ### Transaction
    def get_transaction_schema(self):
        if not self.transaction:
            self.transaction = self._get_transaction_schema()

        return {**self.transaction}

    def _get_transaction_schema(self):
        return {
            **self.get_default_transaction_schema(),
            **self.get_custom_transaction_schema(),
        }

    def get_default_transaction_schema(self):
        return {
            "document_details": None,
            "items": [self.get_item_schema()],
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
        if not self.document:
            self.document = self._get_document_schema()

        return {**self.document}

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

    ### Tax
    def get_tax_schema(self):
        if not self.tax:
            self.tax = self._get_tax_schema()

        return {**self.tax}

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

    ### Address
    def get_address_schema(self):
        if not self.address:
            self.address = self._get_address_schema()

        return {**self.address}

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

    ### Party
    def get_party_schema(self):
        if not self.party:
            self.party = self._get_party_schema()

        return {**self.party}

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

    ### Item
    def get_item_schema(self):
        if not self.item:
            self.item = self._get_item_schema()

        return {**self.item}

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
