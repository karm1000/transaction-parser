from transaction_parser.transaction_parser.document_generators.sales_order import (
    SalesOrderGenerator,
)
from transaction_parser.transaction_parser.regional_overrides.india.document_generators.transaction import (
    IndiaTransactionGenerator,
)


class IndiaSalesOrderGenerator(IndiaTransactionGenerator, SalesOrderGenerator):
    pass
