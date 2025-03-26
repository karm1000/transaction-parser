from transaction_parser.transaction_parser.document_generators.sales_order import (
    SalesOrderGenerator,
)
from transaction_parser.transaction_parser.regional_overrides.other.document_generators.transaction import (
    OtherTransactionGenerator,
)


class OtherSalesOrderGenerator(SalesOrderGenerator, OtherTransactionGenerator):
    pass
