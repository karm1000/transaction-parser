from transaction_parser.transaction_parser.document_generators.sales_order import (
    SalesOrder,
)
from transaction_parser.transaction_parser.regional_overrides.document_generators import (
    REGIONAL_DOCUMENT_GENERATORS,
)

DEFAULT_DOCUMENT_GENERATORS = {
    "Sales Order": SalesOrder,
}

DOCUMENT_GENERATORS = {
    **REGIONAL_DOCUMENT_GENERATORS,
    "DEFAULT": DEFAULT_DOCUMENT_GENERATORS,
}
