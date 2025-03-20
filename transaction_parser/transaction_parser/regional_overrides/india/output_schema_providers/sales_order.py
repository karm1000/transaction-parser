from transaction_parser.transaction_parser.document_parser.output_schema_providers.sales_order import (
    SalesOrder,
)
from transaction_parser.transaction_parser.regional_overrides.india.output_schema_providers.transaction import (
    IndiaTransaction,
)


class IndiaSalesOrder(IndiaTransaction, SalesOrder):
    def get_default_document_schema(self):
        return {
            **super().get_default_document_schema(),
            # Add India specific fields here:
        }
