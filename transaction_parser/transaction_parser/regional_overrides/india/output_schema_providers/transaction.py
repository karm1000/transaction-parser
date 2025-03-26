from transaction_parser.transaction_parser.document_parser.output_schema_providers.transaction import (
    TransactionSchema,
)


class IndiaTransactionSchema(TransactionSchema):
    def get_default_party_schema(self):
        return {
            **super().get_default_party_schema(),
            "gstin": "string (GST Identification Number)",
            "pan": "string (Permanent Account Number)",
        }
