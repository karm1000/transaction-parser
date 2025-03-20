from transaction_parser.transaction_parser.document_parser.output_schema_providers.transaction import (
    Transaction,
)


class SalesOrder(Transaction):
    def get_default_document_schema(self):
        return {
            **super().get_default_document_schema(),
            "delivery_date": "date | null",
            "payment_terms": "string (e.g., '30 days from invoice')",
            "project_reference": "string | null",
            "buyer": {
                "shipping": self.get_party_schema(),
                "billing": self.get_party_schema(),
            },
            "vendor": self.get_party_schema(),
        }
