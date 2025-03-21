from transaction_parser.transaction_parser.document_parser.output_schema_providers.sales_order import (
    SalesOrderSchema,
)
from transaction_parser.transaction_parser.regional_overrides.other.output_schema_providers.transaction import (
    OtherTransactionSchema,
)


class OtherSalesOrderSchema(OtherTransactionSchema, SalesOrderSchema):
    def get_default_document_schema(self):
        return {
            **super().get_default_document_schema(),
            # Add Other country specific fields here ...
        }
