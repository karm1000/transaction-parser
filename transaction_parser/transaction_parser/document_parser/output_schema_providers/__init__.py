from transaction_parser.transaction_parser.document_parser.output_schema_providers.sales_order import (
    SalesOrder,
)
from transaction_parser.transaction_parser.regional_overrides.output_schema_providers import (
    REGIONAL_OUTPUT_SCHEMA_PROVIDERS,
)

DEFAULT_OUTPUT_SCHEMA_PROVIDERS = {
    "Sales Order": SalesOrder,
}


OUTPUT_SCHEMA_PROVIDERS = {
    **REGIONAL_OUTPUT_SCHEMA_PROVIDERS,
    "DEFAULT": DEFAULT_OUTPUT_SCHEMA_PROVIDERS,
}
