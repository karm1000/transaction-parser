from transaction_parser.transaction_parser.document_parser.output_schema_providers.transaction import (
    Transaction,
)


class IndiaTransaction(Transaction):
    def get_default_party_schema(self):
        return {
            **super().get_default_party_schema(),
            "GSTIN": "string (GST Identification Number)",
            "PAN": "string (Permanent Account Number)",
        }
