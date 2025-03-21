from transaction_parser.transaction_parser.document_parser.output_schema_providers.sales_order import (
    SalesOrderSchema,
)
from transaction_parser.transaction_parser.regional_overrides.output_schema_providers import (
    REGIONAL_OUTPUT_SCHEMA_PROVIDERS,
)

DEFAULT_OUTPUT_SCHEMA_PROVIDERS = {
    "Sales Order": SalesOrderSchema,
}


OUTPUT_SCHEMA_PROVIDERS = {
    **REGIONAL_OUTPUT_SCHEMA_PROVIDERS,
    "DEFAULT": DEFAULT_OUTPUT_SCHEMA_PROVIDERS,
}
