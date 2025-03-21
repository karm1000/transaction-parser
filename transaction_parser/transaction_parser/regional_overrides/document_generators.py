from transaction_parser.transaction_parser.regional_overrides.india.document_generators import (
    INDIA_DOCUMENT_GENERATORS,
)
from transaction_parser.transaction_parser.regional_overrides.other.document_generators import (
    OTHER_DOCUMENT_GENERATORS,
)

REGIONAL_DOCUMENT_GENERATORS = {
    "India": INDIA_DOCUMENT_GENERATORS,
    "Other": OTHER_DOCUMENT_GENERATORS,
}
