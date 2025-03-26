from transaction_parser.transaction_parser.document_parser.output_schema_providers.transaction import (
    TransactionSchema,
)


class OtherTransactionSchema(TransactionSchema):
    def get_default_party_schema(self):
        return {
            **super().get_default_party_schema(),
            "tax_id": "string (Country Specific Unique Tax Identifier)",
        }
