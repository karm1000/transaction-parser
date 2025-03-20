from transaction_parser.transaction_parser.document_generators.sales_order import (
    SalesOrder,
)
from transaction_parser.transaction_parser.regional_overrides.india.document_generators.transaction import (
    IndiaTransaction,
)


class IndiaSalesOrder(IndiaTransaction, SalesOrder):
    pass
