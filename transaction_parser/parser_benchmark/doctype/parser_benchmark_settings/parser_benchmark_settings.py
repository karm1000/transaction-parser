# Copyright (c) 2026, Resilient Tech and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ParserBenchmarkSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from transaction_parser.parser_benchmark.doctype.parser_benchmark_token_cost.parser_benchmark_token_cost import (
            ParserBenchmarkTokenCost,
        )

        enabled: DF.Check
        friday: DF.Check
        monday: DF.Check
        saturday: DF.Check
        sunday: DF.Check
        thursday: DF.Check
        token_costs: DF.Table[ParserBenchmarkTokenCost]
        tuesday: DF.Check
        wednesday: DF.Check
    # end: auto-generated types

    pass
